"""SPBM - Stockpile reconstruction & Block Model platform (MIN E 413 term project).

Pipeline: ingest -> QA/QC -> surfaces/growth -> material movement -> block model
-> validation -> uncertainty -> audit.  Run `python -m spbm --help`.
"""
import os as _os

# One maths-library thread per process: the speed-up comes from running cases
# on several worker processes (spbm.parallel), and extra threads inside each
# worker would only compete for the same cores. Set before numpy is imported.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")

__version__ = "2.1.0"
