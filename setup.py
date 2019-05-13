# ---------------- package metadata ----------------
NAME = 'nsls2ptycho'
VERSION = "1.0.2"
DESCRIPTION = 'NSLS-II Ptychography Software'
AUTHOR = 'Leo Fang, Sungsoo Ha, Zhihua Dong, and Xiaojing Huang'
EMAIL = 'leofang@bnl.gov'
LINK = 'https://github.com/leofang/ptycho_gui/'
LICENSE = 'MIT'
REQUIREMENTS = ['mpi4py', 'pyfftw', 'numpy', 'scipy', 'matplotlib', 'Pillow', 'h5py', 'posix_ipc']
# --------------------------------------------------

import os
import sys
from setuptools import setup #, find_packages
import numpy

# cython is needed for compiling the CPU codes
try:
    from Cython.Build import cythonize
except ImportError:
    print("\n************************************************************************\n"
          "***** Cython is not found. Use the corresponding C source instead. *****\n"
          "************************************************************************\n", file=sys.stderr)
    from distutils.extension import Extension
    from glob import glob
    extensions = []
    # this doesn't work because setuptools doesn't support glob pattern...
    #extensions = [Extension("*", ["nsls2ptycho/core/ptycho/*.c"])]
    for filename in glob("nsls2ptycho/core/ptycho/*.c"):
        mod = os.path.basename(filename)[:-2]
        extensions.append(Extension("nsls2ptycho.core.ptycho."+mod, [filename]))
else:
    extensions = cythonize("nsls2ptycho/core/ptycho/*.pyx")

# see if PyQt5 is already installed --- pip and conda use different names...
try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError:
    REQUIREMENTS.append('PyQt5')

# for generating .cubin files
# TODO: add a flag to do this only if GPU support is needed?
import nsls2ptycho.core.ptycho.build_cuda_source as bcs
cubin_path = bcs.compile()

# skip depending CuPy on OS X as the wheel is not provided
if bcs.PLATFORM_DARWIN:
    #for cubin in cubin_path:
    #    os.remove(cubin)
    cubin_path = []

# if GPU support is needed, check if cupy exists
if len(cubin_path) > 0:
    cuda_ver = str(bcs._cuda_version)
    major = str(int(cuda_ver[:-2])//10)
    minor = str(int(cuda_ver[-2:])//10)
    try:
        import cupy
    except ImportError:
        cupy_ver = 'cupy-cuda'+major+minor
        print("CuPy not found. Will install", cupy_ver+"...", file=sys.stderr)
        REQUIREMENTS.append(cupy_ver+'>=6.0.0b3') # for experimental FFT plan feature

# start building
with open("README.md", "r") as f:
    long_description = f.read()

setup(name=NAME,
      version=VERSION,
      #packages=find_packages(),
      packages=["nsls2ptycho", "nsls2ptycho.core", "nsls2ptycho.ui", "nsls2ptycho.core.ptycho", "nsls2ptycho.core.widgets"],
      entry_points={
          'gui_scripts': ['run-ptycho = nsls2ptycho.ptycho_gui:main'],
          'console_scripts': ['run-ptycho-backend = nsls2ptycho.core.ptycho.recon_ptycho_gui:main']
      },
      install_requires=REQUIREMENTS,
      #extras_require={'GPU': 'cupy'}, # this will build cupy from source, may not be the best practice!
      ext_modules=extensions,
      include_dirs=[numpy.get_include()],
      #dependency_links=['git+https://github.com/leofang/ptycho.git#optimization']
      description=DESCRIPTION,
      long_description=long_description,
      long_description_content_type="text/markdown",
      author=AUTHOR,
      author_email=EMAIL,
      url=LINK,
      license=LICENSE,
      include_package_data=True, # to include all precompiled .cubin files
      )
