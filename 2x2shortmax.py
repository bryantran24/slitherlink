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
clue_input = []  # no clues


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
    cells = [cell_name(r, c) for r in range(H) for c in range(W)]

    hedges = [h_name(r, c) for r in range(H + 1) for c in range(W)]
    vedges = [v_name(r, c) for r in range(H) for c in range(W + 1)]
    edges = hedges + vedges

    incident = {}
    for r in range(H):
        for c in range(W):
            incident[cell_name(r, c)] = [
                h_name(r, c),        # top
                h_name(r + 1, c),    # bottom
                v_name(r, c),        # left
                v_name(r, c + 1),    # right
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
            if c > 0:
                inc.append(h_name(r, c - 1))
            if c < W:
                inc.append(h_name(r, c))
            if r > 0:
                inc.append(v_name(r - 1, c))
            if r < H:
                inc.append(v_name(r, c))

            incident_vtx[p] = inc

    return vertices, incident_vtx


def edges_on_from_plan(plan_steps):
    on = set()
    for step in plan_steps:
        s = str(step).strip()
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1]
        name, edge = s.split()
        if name == "Draw":
            on.add(edge)
    return on


def print_slitherlink_ascii(H, W, on_edges, clues):
    dot, HBAR, VBAR, SPACE = "●", "───", "│", "   "
    clue_char = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4"}

    for r in range(H):
        line = dot
        for c in range(W):
            line += (HBAR if h_name(r, c) in on_edges else SPACE) + dot
        print(line)

        line = ""
        for c in range(W):
            line += VBAR if v_name(r, c) in on_edges else " "
            cell = cell_name(r, c)
            line += f" {clue_char[clues[cell]]} " if cell in clues else SPACE
        line += VBAR if v_name(r, W) in on_edges else " "
        print(line)

    line = dot
    for c in range(W):
        line += (HBAR if h_name(H, c) in on_edges else SPACE) + dot
    print(line)


def degree_0_or_2(edges_at_vertex):
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

    exactly_2 = pairs[0] if len(pairs) == 1 else "(or " + " ".join(pairs) + ")"
    return "(or " + all_off + " " + exactly_2 + ")"


# CHANGED: helper for connectivity constraints
def all_off_at_vertex(edges_at_vertex):  # CHANGED
    if len(edges_at_vertex) == 0:
        return "(and)"
    return "(and " + " ".join(f"(not (On {e}))" for e in edges_at_vertex) + ")"


cells, edges, incident = build_grid(H, W)
vertices, vtx_incident = build_vertices(H, W)
clues = parse_clues(clue_input)

# CHANGED: domain includes vertices too (we use Reach(v))
domain = set(map(r, edges + vertices))  # CHANGED

# CHANGED: minimal background needed for Propagate
background = set(map(r, [f"(Edge {e})" for e in edges]))  # CHANGED
background |= set(map(r, [f"(Vtx {v})" for v in vertices]))  # CHANGED
background |= set(map(r, [f"(Inc {v} {e})" for v in vertices for e in vtx_incident[v]]))  # CHANGED

print("Domain", domain)
print("Background", background)

# CHANGED: Draw should keep Edge check (usually helps grounding)
actions = [
    Action(
        r("(Draw ?e)"),
        precondition=r("(and (Edge ?e) (not (On ?e)))"),  # CHANGED
        additions={r("(On ?e)")},
        deletions={r("(not (On ?e))")},
    )
]

# CHANGED: reachability propagation along ON edges
actions.append(  # CHANGED
    Action(
        r("(Propagate ?u ?v ?e)"),
        precondition=r(
            "(and "
            "(On ?e) "
            "(Inc ?u ?e) (Inc ?v ?e) "
            "(Reach ?u) (not (Reach ?v))"
            ")"
        ),
        additions={r("(Reach ?v)")},
        deletions={r("(not (Reach ?v))")},
    )
)

start = set(map(r, [f"(not (On {e}))" for e in edges]))

# CHANGED: initialize Reach at a fixed root
root = "p00"  # CHANGED (top-left)
start.add(r(f"(Reach {root})"))  # CHANGED
for v in vertices:  # CHANGED
    if v != root:
        start.add(r(f"(not (Reach {v}))"))

# --- GOALS ---

# no clue constraints
clue_goal_str = "(and)"  # CHANGED: explicit empty constraint ok in your encoding

# degree constraints everywhere
vertex_goals = [degree_0_or_2(vtx_incident[v]) for v in vertices]

# at least one edge on
nonempty_goal = "(or " + " ".join(f"(On {e})" for e in edges) + ")"

# CHANGED: FORCE root to be on the loop (huge speedup)
root_touch_goal = "(or " + " ".join(f"(On {e})" for e in vtx_incident[root]) + ")"  # CHANGED

# CHANGED: connectivity: every vertex that has any ON edge must be reachable from root
conn_goals = []  # CHANGED
for v in vertices:  # CHANGED
    all_off = all_off_at_vertex(vtx_incident[v])
    conn_goals.append(f"(or {all_off} (Reach {v}))")

all_goals = [clue_goal_str] + vertex_goals + conn_goals + [nonempty_goal, root_touch_goal]  # CHANGED
goal_str = "(and " + " ".join(all_goals) + ")"
goal = r(goal_str)

print("Goal", goal)

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
