import os
import itertools

os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r
from shadowprover.experimental.sst_prover import SST_Prover
from shadowprover.reasoners.planner import run_spectra


# -----------------------------
# single clue input
# -----------------------------
clue_input = "c00 3"

def normalize_clue_token(tok: str) -> str:
    tok = tok.strip().lower()
    if tok in {"zero", "one", "two", "three", "four"}:
        return tok
    if tok == "0": return "zero"
    if tok == "1": return "one"
    if tok == "2": return "two"
    if tok == "3": return "three"
    if tok == "4": return "four"
    raise ValueError(f"Bad clue token: {tok}")

cell_name, clue_tok = clue_input.split()
clue_tok = normalize_clue_token(clue_tok)


# -----------------------------
# 2x2 geometry
# -----------------------------
cells = [f"c{x}{y}" for x in range(2) for y in range(2)]
verts = [f"p{x}{y}" for x in range(3) for y in range(3)]

h_edges = [f"h{x}{y}" for x in range(2) for y in range(3)]
v_edges = [f"v{x}{y}" for x in range(3) for y in range(2)]
edges = h_edges + v_edges

incident_cell = {}
for x in range(2):
    for y in range(2):
        c = f"c{x}{y}"
        incident_cell[c] = [
            f"h{x}{y}",       # top
            f"h{x}{y+1}",     # bottom
            f"v{x}{y}",       # left
            f"v{x+1}{y}",     # right
        ]

touch_vertex = {p: [] for p in verts}

def add_touch(e, p1, p2):
    touch_vertex[p1].append(e)
    touch_vertex[p2].append(e)

for x in range(2):
    for y in range(3):
        add_touch(f"h{x}{y}", f"p{x}{y}", f"p{x+1}{y}")

for x in range(3):
    for y in range(2):
        add_touch(f"v{x}{y}", f"p{x}{y}", f"p{x}{y+1}")


# -----------------------------
# clues: ONLY one clue
# -----------------------------
clues = {cell_name: clue_tok}


# -----------------------------
# domain + background
# -----------------------------
clue_symbols = ["zero", "one", "two", "three", "four"]
domain = set(map(r, cells + verts + edges + clue_symbols))

bg = []
for c in cells:
    bg.append(f"(Cell {c})")
    if c in clues:
        bg.append(f"(Clue {c} {clues[c]})")

for e in edges:
    bg.append(f"(Edge {e})")

for p in verts:
    bg.append(f"(Vertex {p})")

for c, es in incident_cell.items():
    for e in es:
        bg.append(f"(Incident {e} {c})")

for p, es in touch_vertex.items():
    for e in es:
        bg.append(f"(Touches {e} {p})")

background = set(map(r, bg))


# -----------------------------
# actions + start
# -----------------------------
actions = [
    Action(
        r("(Draw ?e)"),
        precondition=r("(and (Edge ?e) (Undrawn ?e))"),
        additions={r("(On ?e)")},
        deletions={r("(Undrawn ?e)"), r("(not (On ?e))")},
    )
]

start = set(map(r,
    [f"(Undrawn {e})" for e in edges] +
    [f"(not (On {e}))" for e in edges]
))


# -----------------------------
# goal compilation (FIXED)
# -----------------------------
def contradiction():
    # safe always-false using an existing constant
    return "(and (On h00) (not (On h00)))"

def exact_k_on(es, k):
    # exact-k over es using explicit negations
    n = len(es)
    if k < 0 or k > n:
        return contradiction()

    if k == 0:
        return "(and " + " ".join(f"(not (On {e}))" for e in es) + ")"
    if k == n:
        return "(and " + " ".join(f"(On {e})" for e in es) + ")"

    cases = []
    for on_tuple in itertools.combinations(es, k):
        on_set = set(on_tuple)
        parts = [(f"(On {e})" if e in on_set else f"(not (On {e}))") for e in es]
        cases.append("(and " + " ".join(parts) + ")")

    if not cases:
        return contradiction()

    return "(or " + " ".join(cases) + ")"

def clue_goal_for_cell(c):
    tok = clues[c]
    k_map = {"zero":0,"one":1,"two":2,"three":3,"four":4}
    return exact_k_on(incident_cell[c], k_map[tok])

def loop_degree_goal():
    # degree at every vertex is 0 or 2 (NO extra nested (or (...)) wrappers)
    parts = []

    # sanity check
    for p in verts:
        if len(touch_vertex[p]) < 2:
            raise RuntimeError(f"BUG: vertex {p} has {len(touch_vertex[p])} touching edges: {touch_vertex[p]}")

    for p in verts:
        es = touch_vertex[p]
        deg0 = "(and " + " ".join(f"(not (On {e}))" for e in es) + ")"
        deg2 = exact_k_on(es, 2)
        parts.append(f"(or {deg0} {deg2})")   # <-- IMPORTANT: no extra "(or (...))"

    # non-empty
    parts.append("(or " + " ".join(f"(On {e})" for e in edges) + ")")

    return "(and " + " ".join(parts) + ")"


goal_str = "(and " + " ".join([
    clue_goal_for_cell(cell_name),   # only c00
    loop_degree_goal(),
]) + ")"

# print("GOAL_STR_PREVIEW:\n", goal_str)

goal = r(goal_str)


# -----------------------------
# run
# -----------------------------
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

print("\nCLUE INPUT:", clue_input)
print("PLAN:")
if not plan:
    print("  No plan found (could be unsat with loop constraints)")
else:
    for i, step in enumerate(plan, 1):
        print(i, step)
