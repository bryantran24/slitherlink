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

## Progress

We implemented a planning-based Slitherlink solver using Spectra and successfully solved all **1×1 and 1×2** grid configurations, with clues.

When extending the model to **2×2** grids, performance became a major issue. Even though the model is correct, the number of possible edge combinations grows quickly, causing the planner to run too slowly.

We tried several optimizations, such as simplifying predicates and action preconditions, but these were not enough to make 2×2 practical.

This project shows that Slitherlink can be modeled as a planning problem, but that the approach does not scale well without optimizations.

We also have a solution for Slitherlink without Spectra with an end to end grid.