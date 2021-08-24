#!/bin/bash

# Download ELAN: https://www.mpi.nl/tools/elan/ELAN_6-1_linux.tar.gz

[ $# -ne 1 ] && { echo "Usage: $0 <ELAN_DIR>/lib/app/extensions/"; exit 1; }
elan_extensions_dir=$(readlink -ve $1) || exit 1
script_dir=$(dirname $(readlink -f $0))

# copy the code to ELAN extensions dir
echo cp -a $script_dir $elan_extensions_dir

# setup allosaurus
cd $script_dir
conda create --yes --name allosaurus-elan-simple python=3.7
source activate allosaurus-elan-simple
pip install -r requirements.txt
