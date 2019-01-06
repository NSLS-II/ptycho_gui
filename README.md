# BNL NSLS-II in-house ptychography software
## Installation
While one can `pip install` this pacakge, most likely the non-Python dependencies will not be avaialable. For the time being, therefore, we recommend using Conda. Here's the steps (6 & 7 are additional steps for using GPUs):
1. Make sure you are granted access to the backend, currently hosted in [this private GitHub repo](https://github.com/leofang/ptycho)
2. `git clone --recursive https://github.com/leofang/ptycho_gui.git` (during the process `git` will prompt you to enther your GitHub id and password for cloning the backend)
3. Either use the current Conda environment, or create a new one, and then do 
`conda install python=3.6 pyfftw mpi4py pyqt=5 numpy scipy matplotlib pillow h5py posix_ipc`
4. Enter the cloned directory: `cd ./ptycho_gui`
5. `pip install .`
6. `pip install cupy-cudaXX` \[`XX` is the version of your CUDA toolkit (ex: `cupy-cuda91` for toolkit v9.1)\]
7. Run the script `configure.sh` in the project directory: `bash ./configure.sh`

In the near future, users in the NSLS-II control network will be able to do `conda install nsls2ptycho` to complete the installation.

## Execution
1. Start the GUI: `run-ptycho`
2. Spawn two MPI processes without GUI: `mpirun -n 2 run-ptycho-backend input_file`

## Conventions:
1. The GUI writes a config file and a few compiled `.cubin` files to `~/.ptycho_gui/`
2. Once the working directory is specified in the GUI, it assumes that all HDF5 files are stored there, and the outputs are written to `working_dir/recon_results/SXXXXX/`, where `XXXXX` is the scan-number string.  
