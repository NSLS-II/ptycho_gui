from setuptools import setup, find_packages

NAME = 'nsls2ptycho'
VERSION = "1.0.0"

setup(name=NAME,
      version=VERSION,
      #packages=find_packages(),
      packages=["nsls2ptycho", "nsls2ptycho.core", "nsls2ptycho.ui", "nsls2ptycho.core.ptycho", "nsls2ptycho.core.widgets"],
      entry_points={
          'gui_scripts': ['nsls2ptycho = nsls2ptycho.ptycho_gui:main']
      },
      dependency_links=['git+https://github.com/leofang/ptycho.git#optimization']
      )
