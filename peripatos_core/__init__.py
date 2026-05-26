"""Peripatos Core — convert academic papers to Socratic-dialogue podcasts."""
# Set OpenMP env vars BEFORE any sub-imports that might pull in torch/faiss.
# On macOS, PyTorch (via docling) and faiss-cpu each bundle their own
# libomp.dylib. Loading both in the same process aborts with:
#   OMP: Error #15: Initializing libomp.dylib, but found libomp.dylib already initialized.
# KMP_DUPLICATE_LIB_OK is the Apple/Anaconda-blessed workaround.
# OMP_NUM_THREADS=1 prevents over-subscription from two OpenMP runtimes.
import os as _os
_os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
_os.environ.setdefault("OMP_NUM_THREADS", "1")
del _os

__version__ = "0.1.0"
