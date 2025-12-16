import os
import matplotlib
import itertools
from functools import cache
import copy

# 1. Visualization Backend
try:
    matplotlib.use("TkAgg")
except:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 2. Configure EProver
os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r
from shadowprover.fol.fol_prover import fol_prove

# ==========================================
# 3. Puzzle Setup (1x1 Grid with '4')
# ==========================================
puzzle_input = {(0, 0): 3, (1, 0): 3}
grid_size = 2


def c(idx):
    return f"c{idx}"


# ==========================================
# 4. Logic Setup (Positive Predicates)
# ==========================================
# Domain of constants
constants = [c(i) for i in range(grid_size + 1)]
domain = set(map(r, constants))
domain.add(r("board"))

background_axioms = []

# --- A. Cell Constraints ---
for (r_idx, c_idx), count in puzzle_input.items():
    edges = [
        f"(HLine {c(r_idx)} {c(c_idx)})",
        f"(HLine {c(r_idx + 1)} {c(c_idx)})",
        f"(VLine {c(r_idx)} {c(c_idx)})",
        f"(VLine {c(r_idx)} {c(c_idx + 1)})",
    ]
    empties = [
        f"(EmptyH {c(r_idx)} {c(c_idx)})",
        f"(EmptyH {c(r_idx + 1)} {c(c_idx)})",
        f"(EmptyV {c(r_idx)} {c(c_idx)})",
        f"(EmptyV {c(r_idx)} {c(c_idx + 1)})",
    ]

    for on_indices in itertools.combinations(range(4), count):
        clauses = [edges[i] if i in on_indices else empties[i] for i in range(4)]
        axiom = f"(if (and {' '.join(clauses)}) (CellSatisfied {c(r_idx)} {c(c_idx)}))"
        background_axioms.append(axiom)

# --- B. Vertex Constraints ---
for r_idx in range(grid_size + 1):
    for c_idx in range(grid_size + 1):
        lines, empties_list = [], []
        # Add edges carefully
        if c_idx > 0:
            lines.append(f"(HLine {c(r_idx)} {c(c_idx - 1)})")
            empties_list.append(f"(EmptyH {c(r_idx)} {c(c_idx - 1)})")
        if c_idx < grid_size:
            lines.append(f"(HLine {c(r_idx)} {c(c_idx)})")
            empties_list.append(f"(EmptyH {c(r_idx)} {c(c_idx)})")
        if r_idx > 0:
            lines.append(f"(VLine {c(r_idx - 1)} {c(c_idx)})")
            empties_list.append(f"(EmptyV {c(r_idx - 1)} {c(c_idx)})")
        if r_idx < grid_size:
            lines.append(f"(VLine {c(r_idx)} {c(c_idx)})")
            empties_list.append(f"(EmptyV {c(r_idx)} {c(c_idx)})")

        # Degree 0
        background_axioms.append(
            f"(if (and {' '.join(empties_list)}) (VertexSatisfied {c(r_idx)} {c(c_idx)}))"
        )
        # Degree 2
        for on_indices in itertools.combinations(range(len(lines)), 2):
            clauses = [
                lines[i] if i in on_indices else empties_list[i]
                for i in range(len(lines))
            ]
            background_axioms.append(
                f"(if (and {' '.join(clauses)}) (VertexSatisfied {c(r_idx)} {c(c_idx)}))"
            )

# --- C. Goal ---
all_reqs = [f"(CellSatisfied {c(r)} {c(col)})" for r, col in puzzle_input.keys()] + [
    f"(VertexSatisfied {c(r)} {c(col)})"
    for r in range(grid_size + 1)
    for col in range(grid_size + 1)
]
background_axioms.append(f"(if (and {' '.join(all_reqs)}) (Solved board))")

background = set(map(r, background_axioms))

# ==========================================
# 5. Manual Planner Implementation
# ==========================================
# Define explicit Grounded Actions (No variables, just concrete moves)
# This removes any ambiguity about "grounding" variables ?r ?c
grounded_actions = []

# Generate all possible MarkH moves
for r_i in range(grid_size + 1):
    for c_i in range(grid_size):
        grounded_actions.append(
            {
                "name": f"MarkHLine {c(r_i)} {c(c_i)}",
                "precond": r(f"(EmptyH {c(r_i)} {c(c_i)})"),
                "add": r(f"(HLine {c(r_i)} {c(c_i)})"),
                "del": r(f"(EmptyH {c(r_i)} {c(c_i)})"),
            }
        )

# Generate all possible MarkV moves
for r_i in range(grid_size):
    for c_i in range(grid_size + 1):
        grounded_actions.append(
            {
                "name": f"MarkVLine {c(r_i)} {c(c_i)}",
                "precond": r(f"(EmptyV {c(r_i)} {c(c_i)})"),
                "add": r(f"(VLine {c(r_i)} {c(c_i)})"),
                "del": r(f"(EmptyV {c(r_i)} {c(c_i)})"),
            }
        )

# Initial State: All Empty
start_state = set()
for r_i in range(grid_size + 1):
    for c_i in range(grid_size):
        start_state.add(r(f"(EmptyH {c(r_i)} {c(c_i)})"))
for r_i in range(grid_size):
    for c_i in range(grid_size + 1):
        start_state.add(r(f"(EmptyV {c(r_i)} {c(c_i)})"))

goal = r("(Solved board)")


# Caching Prover
@cache
def check_logic(kb_frozen, query):
    return fol_prove(kb_frozen, query)


print(f"Starting Manual BFS Planner...")
print(f"Initial State Size: {len(start_state)}")
print(f"Total Possible Actions: {len(grounded_actions)}")

# Queue for BFS: [(current_state_set, plan_list)]
queue = [(start_state, [])]
visited_states = set()

found_plan = None
max_depth = 10  # Safety break

while queue:
    current_state, plan = queue.pop(0)

    # Signature for visited check (frozenset is hashable)
    state_sig = frozenset(current_state)
    if state_sig in visited_states:
        continue
    visited_states.add(state_sig)

    # 1. Check Goal
    kb = frozenset(list(background) + list(current_state))
    # print(f"Checking state depth {len(plan)}...")

    # Optimization: Only check goal if we have enough lines (at least 4 for this puzzle)
    # This speeds it up significantly by skipping prover calls on early states
    if len(plan) >= 4:
        is_solved = check_logic(kb, goal)
        if is_solved[0]:
            print("\n>>> GOAL REACHED! <<<")
            found_plan = plan
            break

    if len(plan) >= max_depth:
        continue

    # 2. Find Applicable Actions
    for action in grounded_actions:
        # Simple set check is faster than prover for these preconditions
        # Since our preconditions are just "Is this atom in the set?"
        if action["precond"] in current_state:
            # Apply Action
            new_state = set(current_state)
            new_state.remove(action["del"])
            new_state.add(action["add"])

            new_plan = plan + [action["name"]]
            queue.append((new_state, new_plan))

if found_plan:
    print(f"Plan found with {len(found_plan)} steps:")
    for step in found_plan:
        print(f" - {step}")

    # Visualization
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.invert_yaxis()

    for r_i in range(grid_size + 1):
        for c_i in range(grid_size + 1):
            ax.plot(c_i, r_i, "ko", markersize=5)

    for (r_i, c_i), val in puzzle_input.items():
        ax.text(
            c_i + 0.5,
            r_i + 0.5,
            str(val),
            ha="center",
            va="center",
            fontsize=14,
            color="gray",
        )

    for act_str in found_plan:
        parts = act_str.split()
        op = parts[0]
        r_idx = int(parts[1].replace("c", ""))
        c_idx = int(parts[2].replace("c", ""))

        y = r_idx
        x = c_idx
        if op == "MarkHLine":
            ax.plot([x, x + 1], [y, y], "b-", linewidth=4)
        elif op == "MarkVLine":
            ax.plot([x, x], [y, y + 1], "b-", linewidth=4)

    if matplotlib.get_backend() == "Agg":
        plt.savefig("slitherlink_solution.png")
        print("Visualization saved.")
    else:
        plt.show()

else:
    print("Search exhausted. No plan found.")
