import os
os.environ['../EPROVER_HOME'] = './eprover/' # Adjust this based on your installation
from shadowprover.syntax import *
from shadowprover.syntax.reader import r
from shadowprover.experimental.sst_prover import SST_Prover

sst_prover = SST_Prover()

print(sst_prover.prove(givens=["Q"], goal="Q"))

r1 = sst_prover.prove(givens=["(if P Q)", "P"], goal="Q")
print(r1)

r2 = sst_prover.prove(givens=["(if P Q)", "(if Q R)", "P"], goal="R")
print(r2)