import os
import matplotlib
import itertools
from functools import cache

# 1. Visualization Backend Setup
# Use TkAgg if available (windowed), else Agg (save to file)
try:
    matplotlib.use("TkAgg")
except:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt

# 2. Configure EProver Path
os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r
from shadowprover.experimental.sst_prover import SST_Prover
from shadowprover.reasoners.planner import run_spectra
from shadowprover.fol.fol_prover import fol_prove

# ==========================================
# 3. Puzzle Definition
# ==========================================
# Two 3s next to each other horizontally
puzzle_input = {(0, 0): 3, (0, 1): 3}
grid_size = 2


def c(idx):
    """Convert integer index to symbol (e.g., 0 -> c0)"""
    return f"c{idx}"


# ==========================================
# 4. Logic & Axioms
# ==========================================
domain = set(map(r, [c(i) for i in range(grid_size + 1)]))
background_axioms = []

# --- A. Cell Count Constraints ---
for (r_idx, c_idx), count in puzzle_input.items():
    # Edges: Top, Bottom, Left, Right
    edges = [
        f"(HLine {c(r_idx)} {c(c_idx)})",
        f"(HLine {c(r_idx + 1)} {c(c_idx)})",
        f"(VLine {c(r_idx)} {c(c_idx)})",
        f"(VLine {c(r_idx)} {c(c_idx + 1)})",
    ]

    # Valid Permutations: Exactly 'count' edges are Lines
    valid_configs = []
    for on_indices in itertools.combinations(range(4), count):
        clauses = []
        for i in range(4):
            if i in on_indices:
                clauses.append(edges[i])
            else:
                # We assert (not (Line...)) for edges that should be empty
                clauses.append(f"(not {edges[i]})")
        valid_configs.append(f"(and {' '.join(clauses)})")

    axiom = (
        f"(iff (CellSatisfied {c(r_idx)} {c(c_idx)}) (or {' '.join(valid_configs)}))"
    )
    background_axioms.append(axiom)

# --- B. Vertex Degree Constraints ---
rows = list(range(grid_size + 1))
cols = list(range(grid_size + 1))

for r_idx in rows:
    for c_idx in cols:
        incident_edges = []
        # Find all edges connecting to this vertex
        if c_idx > 0:
            incident_edges.append(f"(HLine {c(r_idx)} {c(c_idx - 1)})")
        if c_idx < grid_size:
            incident_edges.append(f"(HLine {c(r_idx)} {c(c_idx)})")
        if r_idx > 0:
            incident_edges.append(f"(VLine {c(r_idx - 1)} {c(c_idx)})")
        if r_idx < grid_size:
            incident_edges.append(f"(VLine {c(r_idx)} {c(c_idx)})")

        valid_vertex_configs = []

        # Degree 0: All NOT Lines
        all_not = [f"(not {e})" for e in incident_edges]
        valid_vertex_configs.append(f"(and {' '.join(all_not)})")

        # Degree 2: Exactly 2 ON, rest NOT
        for on_indices in itertools.combinations(range(len(incident_edges)), 2):
            clauses = []
            for i in range(len(incident_edges)):
                if i in on_indices:
                    clauses.append(incident_edges[i])
                else:
                    clauses.append(f"(not {incident_edges[i]})")
            valid_vertex_configs.append(f"(and {' '.join(clauses)})")

        axiom = f"(iff (VertexSatisfied {c(r_idx)} {c(c_idx)}) (or {' '.join(valid_vertex_configs)}))"
        background_axioms.append(axiom)

# --- C. Final Goal ---
all_cells = [f"(CellSatisfied {c(r)} {c(col)})" for r, col in puzzle_input.keys()]
all_vertices = [f"(VertexSatisfied {c(r)} {c(col)})" for r in rows for col in cols]

final_goal_axiom = (
    f"(iff (PuzzleSolved) (and {' '.join(all_cells)} {' '.join(all_vertices)}))"
)
background_axioms.append(final_goal_axiom)
background = set(map(r, background_axioms))

# ==========================================
# 5. Planner Actions
# ==========================================
# Constructive Approach: We assume all lines are OFF by default.
# The planner only needs to decide which lines to turn ON.
actions = [
    Action(
        r("(MarkHLine ?r ?c)"),
        precondition=r("(not (HLine ?r ?c))"),
        additions={r("(HLine ?r ?c)")},
        deletions=set(),
    ),
    Action(
        r("(MarkVLine ?r ?c)"),
        precondition=r("(not (VLine ?r ?c))"),
        additions={r("(VLine ?r ?c)")},
        deletions=set(),
    ),
]


# ==========================================
# 6. Execution
# ==========================================
# Caching wrapper to speed up repeated logic checks
def get_cached_prover(find_answer=True, max_answers=5):
    @cache
    def cached_prover(inputs, output, find_answer=find_answer, max_answers=max_answers):
        return fol_prove(
            inputs, output, find_answer=find_answer, max_answers=max_answers
        )

    def _prover_(inputs, output, find_answer=find_answer, max_answers=max_answers):
        return cached_prover(
            frozenset(inputs), output, find_answer, max_answers=max_answers
        )

    return _prover_


start = set()
goal = r("(PuzzleSolved)")

# 'completions' forces the Closed World Assumption on these predicates.
# This means if HLine/VLine are not explicitly added, they are considered False.
completions = ["HLine", "VLine"]

print("Generating plan for 3-3 Slitherlink...")

result = run_spectra(
    domain,
    background,
    start,
    goal,
    actions,
    get_cached_prover(),
    completions=completions,
    verbose=False,
)

plan = result[0] if result else None

if plan is None:
    print("No valid plan found! (Logic mismatch or timeout)")
else:
    print(f"Plan Found! Length: {len(plan)}")

    # ==========================================
    # 7. Visualization
    # ==========================================
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.set_aspect("equal")
    ax.axis("off")

    # Invert Y so (0,0) is top-left
    ax.invert_yaxis()

    # Draw Grid Dots
    for r_i in range(grid_size + 1):
        for c_i in range(grid_size + 1):
            ax.plot(c_i, r_i, "ko", markersize=5)

    # Draw Numbers
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

    # Draw Solution Lines
    for action in plan:
        act_str = str(action)
        parts = act_str.replace("(", "").replace(")", "").split()
        op = parts[0]

        # Parse c0 -> 0
        r_idx = int(parts[1].replace("c", ""))
        c_idx = int(parts[2].replace("c", ""))

        # Plotting logic
        y = r_idx
        x = c_idx

        if op == "MarkHLine":
            # Horizontal line at y, from x to x+1
            ax.plot([x, x + 1], [y, y], "b-", linewidth=4)
        elif op == "MarkVLine":
            # Vertical line at x, from y to y+1
            ax.plot([x, x], [y, y + 1], "b-", linewidth=4)

    plt.title("Spectra Solution: 3-3 Pair")

    if matplotlib.get_backend() == "Agg":
        plt.savefig("slitherlink_solution.png")
        print("Visualization saved to 'slitherlink_solution.png'")
    else:
        plt.show()
