#!/bin/bash

# for V100
nvcc -cubin -arch=sm_70 -o ./ptycho_sm70.cubin ./core/ptycho/ptycho.cu

# for P100
nvcc -cubin -arch=sm_60 -o ./ptycho_sm60.cubin ./core/ptycho/ptycho.cu
