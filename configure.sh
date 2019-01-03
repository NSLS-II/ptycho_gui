#!/bin/bash

# test if nvcc exists in $PATH
if ! [ -x "$(command -v nvcc)" ]; then
    echo 'Error: nvcc is not found. No GPU support.' >&2
    exit 1
fi

PTYCHO_HOME=~/.ptycho_gui 
PWD=$(pwd)

mkdir $PTYCHO_HOME

for pre in 1 2
do
    #TODO: find a way to automate the compiling without hard-coding the compute compatibilities
    for sm in sm_35 sm_60 sm_70 # K5200 P100 V100
    do
        if [ $pre == 1 ]
        then
            precision=single
        else
            precision=double
        fi

        echo $precision $sm 
        nvcc -DPTYCHO_PRECISION=$pre -cubin -arch=$sm -o $PTYCHO_HOME/ptycho_${sm}_${precision}.cubin $PWD/nsls2ptycho/core/ptycho/ptycho_precision.cu
    done
done
