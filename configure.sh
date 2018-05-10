#!/bin/bash

# for V100
nvcc -cubin -arch=sm_70 -o ./ptycho.cubin ./core/ptycho/ptycho.cu
