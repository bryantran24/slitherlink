import os
import itertools

os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r

from shadowprover.experimental.sst_prover import SST_Prover
from shadowprover.reasoners.planner import run_spectra

import time

start_time = time.perf_counter()


H, W = 1, 2

clue_input = [("c00", 3), ("c01", 3)]
# clue_input = [("c00", 4), ("c01", 1), ("c10", 1), ("c11", 4)]
# clue_input = [("c00", 4)]


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


def parse_clues(clue_pairs):
    clues = {}
    for cell, val in clue_pairs:
        clues[cell] = normalize_clue_token(val)
    return clues


def cell_name(r, c):
    return f"c{r}{c}"


def h_name(r, c):
    return f"h{r}{c}"


def v_name(r, c):
    return f"v{r}{c}"


def build_grid(H, W):
    # cells
    cells = [cell_name(r, c) for r in range(H) for c in range(W)]

    # edges
    # horizontal: r in [0..H], c in [0..W-1]
    hedges = [h_name(r, c) for r in range(H + 1) for c in range(W)]
    # vertical:   r in [0..H-1], c in [0..W]
    vedges = [v_name(r, c) for r in range(H) for c in range(W + 1)]
    edges = hedges + vedges

    # cell -> its 4 incident edges
    incident = {}
    for r in range(H):
        for c in range(W):
            incident[cell_name(r, c)] = [
                h_name(r, c),  # top
                h_name(r + 1, c),  # bottom
                v_name(r, c),  # left
                v_name(r, c + 1),  # right
            ]
    return cells, edges, incident


def build_vertices(H, W):
    vertices = []
    incident_vtx = {}

    for r in range(H + 1):
        for c in range(W + 1):
            p = f"p{r}{c}"
            vertices.append(p)

            inc = []
            # horizontals at this vertex
            if c > 0:
                inc.append(h_name(r, c - 1))
            if c < W:
                inc.append(h_name(r, c))

            # verticals at this vertex
            if r > 0:
                inc.append(v_name(r - 1, c))
            if r < H:
                inc.append(v_name(r, c))

            incident_vtx[p] = inc

    return vertices, incident_vtx

def edges_on_from_plan(plan_steps):
    """
    CHANGED: recognizes Draw_i actions (from ordered Draw/Skip)
    """
    on = set()
    for step in plan_steps:
        s = str(step).strip()
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1]
        name, edge = s.split()
        if name.startswith("Draw_"):  # CHANGED
            on.add(edge)
    return on


def print_slitherlink_ascii(H, W, on_edges, clues):
    dot, HBAR, VBAR, SPACE = "●", "───", "│", "   "
    clue_char = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4"}

    for r in range(H):
        # top boundary of row r
        line = dot
        for c in range(W):
            line += (HBAR if h_name(r, c) in on_edges else SPACE) + dot
        print(line)

        # cell row r
        line = ""
        for c in range(W):
            line += VBAR if v_name(r, c) in on_edges else " "
            cell = cell_name(r, c)
            line += f" {clue_char[clues[cell]]} " if cell in clues else SPACE
        line += VBAR if v_name(r, W) in on_edges else " "
        print(line)

    # bottom boundary
    line = dot
    for c in range(W):
        line += (HBAR if h_name(H, c) in on_edges else SPACE) + dot
    print(line)


def exactly_k_of_4(edges4, k: int) -> str:
    x = [f"(On {e})" for e in edges4]
    nx = [f"(not (On {e}))" for e in edges4]

    if k == 0:
        return "(and " + " ".join(nx) + ")"
    if k == 4:
        return "(and " + " ".join(x) + ")"

    if k == 3:
        clauses = []
        clauses.append("(or " + " ".join(nx) + ")")  # at least one false
        for i in range(4):
            for j in range(i + 1, 4):
                clauses.append(f"(or {x[i]} {x[j]})")  # at most one false
        return "(and " + " ".join(clauses) + ")"

    if k == 1:
        clauses = []
        clauses.append("(or " + " ".join(x) + ")")  # at least one true
        for i in range(4):
            for j in range(i + 1, 4):
                clauses.append(f"(or {nx[i]} {nx[j]})")  # at most one true
        return "(and " + " ".join(clauses) + ")"

    if k == 2:
        clauses = []
        triples = [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]
        for i, j, l in triples:
            clauses.append(f"(or {nx[i]} {nx[j]} {nx[l]})")  # not all 3 true
        for i, j, l in triples:
            clauses.append(f"(or {x[i]} {x[j]} {x[l]})")  # not all 3 false
        return "(and " + " ".join(clauses) + ")"

    raise ValueError("k must be 0..4")


def degree_0_or_2(edges_at_vertex):
    # allow degree 0 or 2 at each vertex
    if len(edges_at_vertex) == 0:
        return "(and)"
    if len(edges_at_vertex) == 1:
        return f"(not (On {edges_at_vertex[0]}))"

    nx = [f"(not (On {e}))" for e in edges_at_vertex]
    all_off = "(and " + " ".join(nx) + ")"

    pairs = []
    m = len(edges_at_vertex)
    for i in range(m):
        for j in range(i + 1, m):
            parts = []
            for k in range(m):
                e = edges_at_vertex[k]
                parts.append(f"(On {e})" if (k == i or k == j) else f"(not (On {e}))")
            pairs.append("(and " + " ".join(parts) + ")")

    # avoid (or X)
    exactly_2 = pairs[0] if len(pairs) == 1 else "(or " + " ".join(pairs) + ")"
    return "(or " + all_off + " " + exactly_2 + ")"


cells, edges, incident = build_grid(H, W)
vertices, vtx_incident = build_vertices(H, W)
clues = parse_clues(clue_input)

for c in clues:
    if c not in incident:
        raise ValueError(f"Unknown cell {c}. Valid cells: {list(incident.keys())}")
    
# -------------------------
# CHANGED: ordered Draw/Skip requires step constants s0..sE in the domain
# -------------------------
edge_order = sorted(edges)               # CHANGED (fixed decision order)
E = len(edge_order)                      # CHANGED
def step_name(i): return f"s{i}"         # CHANGED

domain = set(map(r, edges + [step_name(i) for i in range(E + 1)]))  # CHANGED


background = set(map(r, [f"(Edge {e})" for e in edges] + [f"(Step {step_name(i)})" for i in range(E + 1)]))  # CHANGED

start = set(map(r, [f"(not (On {e}))" for e in edges]))
start.add(r(f"(Ready {step_name(0)})"))  # CHANGED

print("Domain", domain)
print("Background", background)

actions = []
for i, e in enumerate(edge_order):
    s_i = step_name(i)
    s_n = step_name(i + 1)

    # Decide "On" for this edge
    actions.append(
        Action(
            r(f"(Draw_{i} {e})"),
            precondition=r(f"(and (Ready {s_i}) (Edge {e}) (not (On {e})))"),
            additions={r(f"(On {e})"), r(f"(Ready {s_n})")},
            deletions={r(f"(Ready {s_i})"), r(f"(not (On {e}))")},
        )
    )

    # Decide "Off" (skip) for this edge
    actions.append(
        Action(
            r(f"(Skip_{i} {e})"),
            precondition=r(f"(and (Ready {s_i}) (Edge {e}) (not (On {e})))"),
            additions={r(f"(Ready {s_n})")},
            deletions={r(f"(Ready {s_i})")},
        )
    )


def goal_from_clue(cell):
    es = incident[cell]
    clue = clues[cell]
    k_map = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4}
    return exactly_k_of_4(es, k_map[clue])


# clue goals
clue_goals = [goal_from_clue(c) for c in clues.keys()]
if len(clue_goals) == 0:
    raise ValueError("Need at least one clue to form a goal.")
elif len(clue_goals) == 1:
    clue_goal_str = clue_goals[0]
else:
    clue_goal_str = "(and " + " ".join(clue_goals) + ")"

# vertex goals
vertex_goals = [degree_0_or_2(vtx_incident[v]) for v in vertices]

# non-empty loop so at least one edge must be drawn.
nonempty_goal = "(or " + " ".join(f"(On {e})" for e in edges) + ")"

# -------------------------
# CHANGED: require reaching final step so every edge is decided (Draw or Skip)
# -------------------------
processed_goal = f"(Ready {step_name(E)})"  # CHANGED

# final goal
all_goals = [clue_goal_str] + vertex_goals + [nonempty_goal, processed_goal]  # CHANGED
goal_str = all_goals[0] if len(all_goals) == 1 else "(and " + " ".join(all_goals) + ")"
goal = r(goal_str)

sst = SST_Prover()

plan = run_spectra(
    domain,
    background,
    start,
    goal,
    actions,
    sst.get_cached_shadow_prover2(),
    verbose=False,
)[0]

print("GRID:", f"{H}x{W}")
print("CLUES:", clue_input)
print("GOAL:", goal_str)
print("PLAN:")
if not plan:
    print("  No plan found")
else:
    for i, step in enumerate(plan, 1):
        print(i, step)

    print("\nASCII SOLUTION:")
    print_slitherlink_ascii(H, W, edges_on_from_plan(plan), clues)

end_time = time.perf_counter()
elapsed_time = end_time - start_time

print(f"Elapsed time: {elapsed_time:.4f} seconds")
