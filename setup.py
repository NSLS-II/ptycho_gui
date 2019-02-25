NAME = 'nsls2ptycho'
VERSION = "1.0.0"
DESCRIPTION = 'NSLS-II Ptychography Software'
AUTHOR = 'Leo Fang, Sungsoo Ha, Zhihua Dong, and Xiaojing Huang'
EMAIL = 'leofang@bnl.gov'
LINK = 'https://github.com/leofang/ptycho_gui/'
LICENSE = 'MIT'
REQUIREMENTS = ['mpi4py', 'pyfftw', 'numpy', 'scipy', 'matplotlib', 'Pillow', 'h5py', 'posix_ipc']
with open("README.md", "r") as f:
    long_description = f.read()

import sys
from setuptools import setup #, find_packages

# cython is needed for compiling the CPU codes
# TODO: add the generated .c file in the source tree to avoid depending on cython
try:
    from Cython.Build import cythonize
except ImportError:
    print("\n*************************************************************************\n"
          "***** Cython is required to build this package.                     *****\n"
          "***** Please do \"pip install cython\" and then install this package. *****\n"
          "*************************************************************************\n", file=sys.stderr)
    raise
else:
    import numpy

# see if PyQt5 is already installed --- pip and conda use different names...
try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError:
    REQUIREMENTS.append('PyQt5')

setup(name=NAME,
      version=VERSION,
      #packages=find_packages(),
      packages=["nsls2ptycho", "nsls2ptycho.core", "nsls2ptycho.ui", "nsls2ptycho.core.ptycho", "nsls2ptycho.core.widgets"],
      entry_points={
          'gui_scripts': ['run-ptycho = nsls2ptycho.ptycho_gui:main'],
          'console_scripts': ['run-ptycho-backend = nsls2ptycho.core.ptycho.recon_ptycho_gui:main']
      },
      install_requires=REQUIREMENTS,
      extras_require={'GPU': 'cupy'}, # this will build cupy from source, may not be the best practice!
      ext_modules=cythonize("nsls2ptycho/core/ptycho/*.pyx"),
      include_dirs=[numpy.get_include()],
      #dependency_links=['git+https://github.com/leofang/ptycho.git#optimization']
      description=DESCRIPTION,
      long_description=long_description,
      long_description_content_type="text/markdown",
      author=AUTHOR,
      author_email=EMAIL,
      url=LINK,
      license=LICENSE,
      )
