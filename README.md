# slitherlink


## Installation 

Install Conda: https://anaconda.org/anaconda/conda

### Python dependencies 
```
conda init 
conda env create -f environment.yml
conda activate slitherlink_env
```

### Install EProver

```
git clone https://github.com/eprover/eprover
cd eprover
./configure --enable-ho
make rebuild
```