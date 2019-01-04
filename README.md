# BNL NSLS-II in-house ptychography software
## Installation
While one can `pip install` this pacakge, most likely the non-Python dependencies will not be avaialable. For the time being, therefore, we recommend using Conda. Here's the steps:
1. Make sure you are granted access to the backend, currently hosted in a private repo
2. `git clone --recursive https://github.com/leofang/ptycho_gui.git`, during which `git` will prompt you to enther your GitHub id and password for cloning the backend
3. Either use the current Conda environment, or create a new one, and then do `conda install python=3.6 pyfftw mpi4py pyqt >=5 numpy scipy matplotlib pillow h5py posix_ipc`
4. Enter the cloned directory: `cd ./ptycho_gui`
5. `pip install .`

## Execution
1. With GUI: `run-ptycho`
2. Spawn two MPI processes without GUI: `mpirun -n 2 run-ptycho-backend input_file`
