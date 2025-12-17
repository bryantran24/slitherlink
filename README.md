# Slitherlink Solver

## Installation

Install Conda: <https://anaconda.org/anaconda/conda>

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

## Usage

The puzzle and instructions for the game can be found at <https://www.puzzle-loop.com/>

The inputs can be edited in each file:

```
# Syntax (row number, col number): clue number

# Eg.
puzzle_input={(0, 0): 4, (0, 1): 1}
WIDTH=2
HEIGHT=1

# Output
●───●   ●
│ 4 │ 1 
●───●   ●

```

For Shadow Prover, run `python nxnfinal.py`.
For BFS, run `python nxnfinal.py`.

Our variation of the puzzle accepts multiple separate loops, and a puzzle without any clues has infinite valid solutions.

## Progress

We implemented a planning-based Slitherlink solver using Spectra and successfully solved all **1×1 and 1×2** grid configurations, with clues.

When extending the model to **2×2** grids, performance became a major issue. Even though the model is correct, the number of possible edge combinations grows quickly, causing the planner to run slowly.

This project shows that Slitherlink can be modeled as a planning problem, but that the approach does not scale well without optimizations.

Form the 1×1 and 1×2 solvers, we created a n×n solver that is adjustable to any grid size.

We also have a solution for Slitherlink without Spectra utilizing a BFS algorithm. The algorithm performs faster but is not as generalizable as Spectra.

## Tested Puzzles

```
●───●
│ 4 │
●───●
BFS: 0.1s
Spectra: 2.5s

●   ●───●
  1 │ 4 │
●   ●───●
BFS: 0.6s
Spectra: 45.8s

●───●───●
│ 3   3 │
●───●───●
BFS: 0.8s
Spectra: 69.3s

●   ●
  1  
●───●
│ 4 │
●───●
BFS: 5.1s
Spectra: 37.9s

●───●
│ 3 │
●   ●
│ 3 │
●───●
BFS: 1s
Spectra: 67.3s

●───●   ●
│ 4 │
●───●   ●

●   ●   ●
BFS: 3.6s
Spectra: 752.9s

●───●   ●
│ 4 │
●───●   ●
      0  
●   ●   ●
BFS: 3.4s
Spectra: 399.5

●───●───●
│ 3     │
●───●   ●
  2 │ 3 │
●   ●───●
or
●───●   ●
│ 3 │
●   ●───●
│ 2   3 │
●───●───●
BFS: 105.9s

```
