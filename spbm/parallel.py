"""Run independent cases (Monte Carlo realisations, sensitivity and robustness
variants, forward-model settings) on several CPU cores.

Results are returned in the order of the cases, and every case gets exactly
the inputs it would get in a one-core run, so the numbers do not depend on
the number of workers. Workers: SPBM_WORKERS (set by `--workers` or the web
page: low / medium / high or a number), default high; never more than
machine()["max_workers"]. One worker runs everything in this process.
"""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, as_completed

_STATE: dict = {}                    # per-process data shared by all cases (set by the initializer)
_THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")


GB_PER_WORKER = 0.6                  # measured peak ~0.3 GB per reconstruction, with margin


def total_ram_gb() -> float | None:
    """Installed memory, or None if it cannot be read."""
    try:
        if os.name == "nt":
            import ctypes

            class MEM(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MEM()
            m.dwLength = ctypes.sizeof(MEM)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.ullTotalPhys / 1024 ** 3
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024 ** 3
    except Exception:
        return None


def machine() -> dict:
    """Cores, memory and the worker counts of the speed modes. The maximum
    leaves one core free and stays within ~75% of memory."""
    cores = os.cpu_count() or 1
    ram = total_ram_gb()
    top = cores - 1 if cores > 2 else cores
    if ram:
        top = min(top, int(0.75 * ram / GB_PER_WORKER))
    top = max(1, top)
    return {"cores": cores, "ram_gb": round(ram, 1) if ram else None, "max_workers": top,
            "modes": {"low": 1, "medium": max(1, top // 2), "high": top}}


def resolve_workers(value) -> int:
    """'low' / 'medium' / 'high' / a number -> a worker count within the maximum."""
    m = machine()
    v = str(value).strip().lower() if value is not None else ""
    if v in m["modes"]:
        return m["modes"][v]
    if v.isdigit() and int(v) > 0:
        return min(int(v), m["max_workers"])
    return m["modes"]["high"]


def n_workers(n_cases: int) -> int:
    return max(1, min(resolve_workers(os.environ.get("SPBM_WORKERS")), n_cases))


def state() -> dict:
    return _STATE


def _init(shared: dict):
    _STATE.clear()
    _STATE.update(shared)


_POOL = None                         # shared pool while run_steps runs steps side by side


def run_cases(fn, cases: list, shared: dict | None = None, on_done=None, costs=None) -> list:
    """fn(case) for every case, using the data in `shared` (via state()).
    fn must be a module-level function. on_done(k, n) is called as cases finish.
    `costs` (relative run times) makes the slowest cases start first, so no
    long case is left running alone at the end; results keep the case order.
    Inside run_steps the cases go to the shared pool (whose data replaces `shared`)."""
    shared = shared or {}
    order = sorted(range(len(cases)), key=lambda k: -costs[k]) if costs else list(range(len(cases)))
    if _POOL is not None:
        return _collect(_POOL, fn, cases, order, on_done)
    n = n_workers(len(cases))
    if n == 1:
        _init(shared)
        out = []
        for k, c in enumerate(cases):
            out.append(fn(c))
            if on_done:
                on_done(k + 1, len(cases))
        return out
    with _executor(n, shared) as ex:
        return _collect(ex, fn, cases, order, on_done)


def _collect(ex, fn, cases, order, on_done):
    futs = {ex.submit(fn, cases[k]): k for k in order}
    out = [None] * len(cases)
    for done, f in enumerate(as_completed(futs), 1):
        out[futs[f]] = f.result()
        if on_done:
            on_done(done, len(cases))
    return out


class _executor:
    """Process pool with one maths thread per worker (the environment is set
    while the workers start, then restored)."""

    def __init__(self, n, shared):
        self.n, self.shared = n, shared

    def __enter__(self):
        self.saved = {v: os.environ.get(v) for v in _THREAD_VARS}
        os.environ.update({v: "1" for v in _THREAD_VARS})
        self.ex = ProcessPoolExecutor(max_workers=self.n, initializer=_init, initargs=(self.shared,))
        return self.ex

    def __exit__(self, *exc):
        self.ex.shutdown(wait=True, cancel_futures=exc[0] is not None)
        for v, old in self.saved.items():
            if old is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = old


def run_steps(steps: list, shared: dict, log=print, start_first=()) -> dict:
    """Run independent steps [(key, label, fn)] and return {key: result}.
    With several workers the steps run side by side (one thread each, all
    feeding one shared pool of worker processes, so no core waits for a step
    to end); with one worker they run one after another, in order. `shared`
    must hold the data every step's cases read through state(). Steps named in
    `start_first` (those with the longest single cases) submit their work first,
    so their long cases are not left running alone at the end."""
    global _POOL
    if not steps:
        return {}
    n = n_workers(10 ** 6)
    if n == 1:
        out = {}
        for key, label, fn in steps:
            log(label)
            out[key] = fn()
        return out
    import threading
    import time
    t0 = time.time()
    log("8-9 running side by side: " + "; ".join(label.strip() for _, label, _ in steps))
    out, errors = {}, []

    def work(key, label, fn):
        try:
            out[key] = fn()
            log(f"    finished: {label.strip()} ({time.time() - t0:.0f} s)")
        except BaseException as e:            # reported after all steps stop
            errors.append(e)

    with _executor(n, shared) as ex:
        _POOL = ex
        try:
            rank = {k: i for i, k in enumerate(start_first)}
            ordered = sorted(steps, key=lambda s: rank.get(s[0], len(rank)))
            threads = [threading.Thread(target=work, args=s, daemon=True) for s in ordered]
            for th in threads:
                th.start()
                time.sleep(0.2)               # let it submit its cases before the next step does
            for th in threads:
                th.join()
        finally:
            _POOL = None
    if errors:
        raise errors[0]
    return out
