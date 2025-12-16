import os

os.environ["EPROVER_HOME"] = "./eprover/"
from shadowprover.syntax import *
from shadowprover.syntax.reader import r
from shadowprover.fol.fol_prover import fol_prove
from shadowprover.reasoners.planner import Action

# ==========================================
# 1. Logic Setup (Same as before)
# ==========================================
grid_size = 1


def c(i):
    return f"c{i}"


domain = set(map(r, [c(i) for i in range(grid_size + 1)]))

# Simplified Axiom for Testing: (HLine c0 c0) -> Goal
# We strip away the complex slitherlink logic to test the MECHANISM first.
background = [r("(if (HLine c0 c0) (Solved c0))")]

# Action: Mark Line
action = Action(
    r("(MarkHLine ?r ?c)"),
    precondition=r("(not (HLine ?r ?c))"),
    additions={r("(HLine ?r ?c)")},
    deletions={r("(not (HLine ?r ?c))")},
)

# Start State: Explicit Negation
start_state = [r("(not (HLine c0 c0))")]

# ==========================================
# TEST 1: Precondition Check
# ==========================================
print("\n--- TEST 1: Action Applicability ---")
# Manually verify if Start State implies Precondition
precond = r("(not (HLine c0 c0))")
kb = frozenset(start_state + background)
result = fol_prove(kb, precond)

print(f"State: {start_state}")
print(f"Query: Does State imply {precond}?")
print(f"Result: {result}")

if result[0]:
    print("✅ SUCCESS: Planner CAN apply the action.")
else:
    print("❌ FAIL: Planner thinks action is invalid.")
    print("   Hypothesis: Prover cannot derive negative facts from this state.")

# ==========================================
# TEST 2: Action Execution (Simulation)
# ==========================================
print("\n--- TEST 2: Action Execution ---")
# Simulate applying (MarkHLine c0 c0)
# New State = (Old - Deletions) + Additions
current_state_set = set(start_state)
additions = {r("(HLine c0 c0)")}
deletions = {r("(not (HLine c0 c0))")}

next_state = (current_state_set - deletions).union(additions)
print(f"Next State: {next_state}")

if r("(HLine c0 c0)") in next_state and r("(not (HLine c0 c0))") not in next_state:
    print("✅ SUCCESS: State updated correctly.")
else:
    print("❌ FAIL: State update failed.")

# ==========================================
# TEST 3: Goal Verification
# ==========================================
print("\n--- TEST 3: Goal Check ---")
goal = r("(Solved c0)")
kb_next = frozenset(list(next_state) + background)
result_goal = fol_prove(kb_next, goal)

print(f"Query: Does Next State imply {goal}?")
print(f"Result: {result_goal}")

if result_goal[0]:
    print("✅ SUCCESS: Goal detected.")
else:
    print("❌ FAIL: Goal NOT detected.")
