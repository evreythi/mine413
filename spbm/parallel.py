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


def run_cases(fn, cases: list, shared: dict | None = None, on_done=None) -> list:
    """fn(case) for every case, using the data in `shared` (via state()).
    fn must be a module-level function. on_done(k, n) is called as cases finish."""
    shared = shared or {}
    n = n_workers(len(cases))
    if n == 1:
        _init(shared)
        out = []
        for k, c in enumerate(cases):
            out.append(fn(c))
            if on_done:
                on_done(k + 1, len(cases))
        return out
    # one maths thread per worker, so the workers do not compete for the same cores
    saved = {v: os.environ.get(v) for v in _THREAD_VARS}
    os.environ.update({v: "1" for v in _THREAD_VARS})
    try:
        with ProcessPoolExecutor(max_workers=n, initializer=_init, initargs=(shared,)) as ex:
            futs = {ex.submit(fn, c): k for k, c in enumerate(cases)}
            out = [None] * len(cases)
            for done, f in enumerate(as_completed(futs), 1):
                out[futs[f]] = f.result()
                if on_done:
                    on_done(done, len(cases))
            return out
    finally:
        for v, old in saved.items():
            if old is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = old
