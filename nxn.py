import os
import itertools
from functools import cache

# 1. Visualization Backend
try:
    import matplotlib

    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
except:
    pass

# 2. Configure EProver
os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r
from shadowprover.experimental.sst_prover import SST_Prover
from shadowprover.reasoners.planner import run_spectra
from shadowprover.fol.fol_prover import fol_prove

# ==========================================
# 3. Puzzle Setup (1x1 with '4')
# ==========================================
puzzle_input = {(0, 0): 4}
grid_size = 1


def normalize_clue_token(val) -> str:
    val = str(val).strip().lower()
    if val in {"zero", "one", "two", "three", "four"}:
        return val
    if val == "0":
        return "zero"
    if val == "1":
        return "one"
    if val == "2":
        return "two"
    if val == "3":
        return "three"
    if val == "4":
        return "four"
    raise ValueError(f"Bad clue token: {val}")


def h(r, c):
    return f"h{r}{c}"


def v(r, c):
    return f"v{r}{c}"


# ==========================================
# 4. Logic Generation (Monolithic Strategy)
# ==========================================
# Generate Domain
all_edges = []
for r_i in range(grid_size + 1):
    for c_i in range(grid_size):
        all_edges.append(h(r_i, c_i))
for r_i in range(grid_size):
    for c_i in range(grid_size + 1):
        all_edges.append(v(r_i, c_i))

domain = set(map(r, all_edges))

# --- Construct Giant Goal Formula ---
goal_clauses = []

# Cell Constraints
for (r_i, c_i), count in puzzle_input.items():
    cell_edges = [h(r_i, c_i), h(r_i + 1, c_i), v(r_i, c_i), v(r_i, c_i + 1)]
    valid_configs = []

    for on_indices in itertools.combinations(range(4), count):
        parts = []
        for i in range(4):
            if i in on_indices:
                parts.append(f"(On {cell_edges[i]})")
            else:
                parts.append(f"(not (On {cell_edges[i]}))")
        valid_configs.append(f"(and {' '.join(parts)})")

    if valid_configs:
        goal_clauses.append(f"(or {' '.join(valid_configs)})")

# Vertex Constraints
for r_i in range(grid_size + 1):
    for c_i in range(grid_size + 1):
        incident = []
        if c_i > 0:
            incident.append(h(r_i, c_i - 1))
        if c_i < grid_size:
            incident.append(h(r_i, c_i))
        if r_i > 0:
            incident.append(v(r_i - 1, c_i))
        if r_i < grid_size:
            incident.append(v(r_i, c_i))

        valid_vertex = []

        # Degree 0
        all_off = [f"(not (On {e}))" for e in incident]
        valid_vertex.append(f"(and {' '.join(all_off)})")

        # Degree 2
        for on_indices in itertools.combinations(range(len(incident)), 2):
            parts = []
            for i in range(len(incident)):
                if i in on_indices:
                    parts.append(f"(On {incident[i]})")
                else:
                    parts.append(f"(not (On {incident[i]}))")
            valid_vertex.append(f"(and {' '.join(parts)})")

        if valid_vertex:
            goal_clauses.append(f"(or {' '.join(valid_vertex)})")

# Final Goal
# We construct the string carefully to ensure valid syntax
giant_goal_str = f"(and {' '.join(goal_clauses)})"
goal = r(giant_goal_str)

# ==========================================
# 5. Planner Configuration
# ==========================================
# Explicit Start State: Everything is OFF
start = set()
for e in all_edges:
    start.add(r(f"(not (On {e}))"))

# Lifted Action: Draw ?e
actions = [
    Action(
        r("(Draw ?e)"),
        precondition=r("(not (On ?e))"),
        additions={r("(On ?e)")},
        deletions={r("(not (On ?e))")},
    )
]


# Manual Caching Wrapper (Exactly as in 1x2.py)
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


print("Running Spectra (Monolithic + Manual Prover)...")

sst = SST_Prover()
# Completions=[] because we handle negations manually in Start State
result = run_spectra(
    domain,
    set(),
    start,
    goal,
    actions,
    sst.get_cached_shadow_prover2(),
    completions=[],
    verbose=False,
)
plan = result

if plan:
    print(f"\nPLAN FOUND! ({len(plan)} steps)")
    for step in plan:
        print(step)

    # Visualization
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.invert_yaxis()

    # Draw Grid
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

    # Draw Lines
    for action in plan:
        act_str = str(action)
        # Parse: (Draw h00)
        clean = act_str.replace("(", "").replace(")", "").split()
        edge_name = clean[1]
        kind = edge_name[0]
        r_i = int(edge_name[1])
        c_i = int(edge_name[2])

        if kind == "h":
            ax.plot([c_i, c_i + 1], [r_i, r_i], "b-", linewidth=4)
        elif kind == "v":
            ax.plot([c_i, c_i], [r_i, r_i + 1], "b-", linewidth=4)

    if matplotlib.get_backend() == "Agg":
        plt.savefig("slitherlink_solution.png")
        print("Visualization saved to slitherlink_solution.png")
    else:
        plt.show()
else:
    print("\nNo plan found.")
