# BNL NSLS-II in-house ptychography software
## Introduction

## Installation
While one can `pip install` this pacakge directly, most likely the non-Python dependencies will not be available. For the time being, therefore, we recommend using Conda. The last two steps are needed for using GPU. 
### On NSLS-II beamline machines
The instruction below is for sys admins who have root priviledge to install the software at the system level so that *all* users logging in the machine can run the software directly without any setup.
1. Create a new conda environment named `ptycho_production`: `sudo conda create -n ptycho_production python=3.6 cython pyfftw pyqt=5 numpy scipy matplotlib pillow h5py posix_ipc databroker openmpi mpi4py` (If you need beamline-specific packages, such as `hxntools` for HXN, append the package names in the `conda install` command. This helps resolve possible conflict/downgrade issues.) 
The conda environment `ptycho_production` is activated under the hood using the `run-ptycho` script to be installed in Step 8.
2. Make sure you are able to log in NSLS-II internal GitLab (https://gitlab.nsls2.bnl.gov/) **via LDAP using your control network account**. Currently the backend is host there. Do **NOT** register a new account there!
3. Create a temporary workspace: `mkdir /tmp/build_ptycho; cd /tmp/build_ptycho`
4. Clone the mirror of this repo: `git clone --recursive https://gitlab.nsls2.bnl.gov/leofang/ptycho_gui.git`. (During the process `git` may prompt you to enther your control id and password up to *twice* for cloning the frontend and the backend.)
5. Move this repo to `/usr/local/`: `sudo mv ./ptycho_gui /usr/local/; cd /usr/local/ptycho_gui; rmdir /tmp/build_ptycho`
6. `sudo /opt/conda_envs/ptycho_production/bin/pip install .`
7. `sudo /opt/conda_envs/ptycho_production/bin/pip install 'cupy-cudaXX>=6.0.0b3'`, where `XX` is your CUDA toolkit version, available from `nvcc --version`
8. Copy the script `run-ptycho` to `/usr/local/bin/`: `sudo cp ./run-ptycho /usr/local/bin/`

In the near future, users in the BNL campus network will be able to do simply `conda install nsls2ptycho` to replace Steps 1-6. 

### On personal machines (TO BE UPDATED)
1. Make sure you are granted access to the backend, currently hosted in [this private GitHub repo](https://github.com/leofang/ptycho)
2. `git clone --recursive https://github.com/leofang/ptycho_gui.git` (during the process `git` will prompt you to enther your GitHub id and password for cloning the backend)
3. Either use the current Conda environment, or create a new one, and then do 
`conda install python=3.6 cython pyfftw pyqt=5 numpy scipy matplotlib pillow h5py posix_ipc databroker`
4. If you need beamline-specific packages, install it now. Ex: `conda install hxntools`
5. `conda install -c conda-forge mpi4py openmpi` (the `conda-forge` channel is needed until we build `mpi4py` in `nsls2-tag`)
4. Enter the cloned directory: `cd ./ptycho_gui`
5. `pip install .`
6. `pip install 'cupy-cudaXX>=6.0.0b3'`, where `XX` is your CUDA toolkit version, available from `nvcc --version`
7. Run the script `configure.sh` in the project directory: `bash ./configure.sh`

## Execution
1. Start the GUI: `run-ptycho`
2. Spawn two MPI processes without GUI: `mpirun -n 2 run-ptycho-backend input_file`

## Conventions
1. The GUI writes a config file and a few compiled `.cubin` files to `~/.ptycho_gui/`
2. Once the working directory is specified in the GUI, it assumes that all HDF5 files are stored there, and the outputs are written to `working_dir/recon_results/SXXXXX/`, where `XXXXX` is the scan-number string.  

## References
- *High-Performance Multi-Mode Ptychography Reconstruction on Distributed GPUs*, Z. Dong, Y.-L. L. Fang *et al.*, 2018 NYSDS, DOI:[10.1109/NYSDS.2018.8538964](https://doi.org/10.1109/NYSDS.2018.8538964)

## License
MIT (subject to change)

Users are encouraged to cite the references above.

## Maintainer
- Leo Fang ([@leofang](https://github.com/leofang))
