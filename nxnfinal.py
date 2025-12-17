import os
import itertools
import time

os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r
from shadowprover.experimental.sst_prover import SST_Prover
from shadowprover.reasoners.planner import run_spectra

start_time = time.perf_counter()

# 1x1
puzzle_input = {(0, 0): 4}
HEIGHT = 1
WIDTH = 1

# 2x1
# puzzle_input = {(0, 0): 1, (0, 1): 4}
# HEIGHT = 1
# WIDTH = 2

# 2x1
# puzzle_input = {(0, 0): 3, (0, 1): 3}
# HEIGHT = 1
# WIDTH = 2

# 1x2
# puzzle_input = {(0, 0): 1, (1, 0): 4}
# HEIGHT = 2
# WIDTH = 1


# 1x2
# puzzle_input = {(0, 0): 3, (1, 0): 3}
# HEIGHT = 2
# WIDTH = 1

# 2x2
# puzzle_input = {(0, 0): 4}
# HEIGHT = 2
# WIDTH = 2

# 2x2
# puzzle_input = {(0, 0): 4, (1, 1): 0}
# HEIGHT = 2
# WIDTH = 2

# 2x2 (times out)
# puzzle_input = {(0, 0): 3, (1, 0): 2, (1, 1): 3}
# HEIGHT = 2
# WIDTH = 2


def h(r, c):
    return f"h{r}{c}"


def v(r, c):
    return f"v{r}{c}"


def make_binary_op(op, items):
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return f"({op} {items[0]} {make_binary_op(op, items[1:])})"


all_edges = []
for r_i in range(HEIGHT + 1):
    for c_i in range(WIDTH):
        all_edges.append(h(r_i, c_i))
for r_i in range(HEIGHT):
    for c_i in range(WIDTH + 1):
        all_edges.append(v(r_i, c_i))

domain = set(map(r, all_edges))

goal_clauses = []

# Logic for each clue
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
        valid_configs.append(make_binary_op("and", parts))

    if valid_configs:
        goal_clauses.append(make_binary_op("or", valid_configs))

# The logic checks for either a degree of 0 or 2 for each vertex in the puzzle to ensure there are no loose ends.
for r_i in range(HEIGHT + 1):
    for c_i in range(WIDTH + 1):
        incident = []
        if c_i > 0:
            incident.append(h(r_i, c_i - 1))
        if c_i < WIDTH:
            incident.append(h(r_i, c_i))
        if r_i > 0:
            incident.append(v(r_i - 1, c_i))
        if r_i < HEIGHT:
            incident.append(v(r_i, c_i))

        valid_vertex = []

        all_off = [f"(not (On {e}))" for e in incident]
        valid_vertex.append(make_binary_op("and", all_off))

        for on_indices in itertools.combinations(range(len(incident)), 2):
            parts = []
            for i in range(len(incident)):
                if i in on_indices:
                    parts.append(f"(On {incident[i]})")
                else:
                    parts.append(f"(not (On {incident[i]}))")
            valid_vertex.append(make_binary_op("and", parts))

        if valid_vertex:
            goal_clauses.append(make_binary_op("or", valid_vertex))

giant_goal_str = make_binary_op("and", goal_clauses)
goal = r(giant_goal_str)

start = set()
for e in all_edges:
    start.add(r(f"(not (On {e}))"))

actions = [
    Action(
        r("(Draw ?e)"),
        precondition=r("(not (On ?e))"),
        additions={r("(On ?e)")},
        deletions={r("(not (On ?e))")},
    )
]

sst = SST_Prover()
background = set()

print("Domain", domain)
print("Background", background)
print("Start", start)
print("Goal", goal)
print("Actions", actions)

results = run_spectra(
    domain,
    background,
    start,
    goal,
    actions,
    sst.get_cached_shadow_prover2(),
    verbose=False,
)
plan = results[0] if results else None

print("Solved")

end_time = time.perf_counter()
elapsed_time = end_time - start_time
print(f"Elapsed time: {elapsed_time:.4f} seconds")


def print_ascii(plan, height, width, puzzle_input):
    on_edges = set()
    if plan:
        for step in plan:
            s = str(step).strip().replace("(", "").replace(")", "")
            parts = s.split()
            if len(parts) >= 2 and parts[0] == "Draw":
                on_edges.add(parts[1])

    print("\nASCII SOLUTION:")

    for r in range(height + 1):
        line_str = ""
        for c in range(width + 1):
            line_str += "●"
            if c < width:
                edge_name = f"h{r}{c}"
                if edge_name in on_edges:
                    line_str += "───"
                else:
                    line_str += "   "
        print(line_str)

        if r < height:
            row_str = ""
            for c in range(width + 1):
                edge_name = f"v{r}{c}"
                if edge_name in on_edges:
                    row_str += "│"
                else:
                    row_str += " "

                if c < width:
                    val = puzzle_input.get((r, c), " ")
                    row_str += f" {val} "
            print(row_str)


if plan:
    for step in plan:
        print(step)
    print_ascii(plan, HEIGHT, WIDTH, puzzle_input)
else:
    print("No plan found.")
