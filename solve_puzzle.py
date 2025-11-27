import os
os.environ['EPROVER_HOME'] = './eprover/' # Adjust this based on your installation
from shadowprover.syntax import *
from shadowprover.syntax.reader import r
from shadowprover.experimental.sst_prover import SST_Prover

sst_prover = SST_Prover()

x = sst_prover.prove(givens=["(if P Q)", "P"], goal="Q")

print(x)