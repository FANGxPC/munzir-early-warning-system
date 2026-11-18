"""
PRAHARI - Population & Workforce Health Early Warning System
"""

import os

# Guarantee writable scratch/cache directories for Triton, PyTorch, and Matplotlib
os.environ.setdefault("TRITON_CACHE_DIR", "/tmp/triton")
os.environ.setdefault("TORCH_EXTENSIONS_DIR", "/tmp/torch_extensions")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl")
for _p in ("/tmp/triton", "/tmp/torch_extensions", "/tmp/mpl"):
    try:
        os.makedirs(_p, exist_ok=True)
    except OSError:
        pass

__version__ = "0.1.0"

