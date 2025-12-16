import os
import itertools

os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r
from shadowprover.experimental.sst_prover import SST_Prover
from shadowprover.reasoners.planner import run_spectra


# ------------------------------------------------------------
# INPUT CLUES (example)
# use cell coords: c00 c10 / c01 c11
# each string: "cell value" where value is 0..4 or zero..four
# ------------------------------------------------------------
clue_inputs = [
    "c00 3",
    "c10 3",
    "c01 3",
    "c11 3",
]

def normalize_clue_token(tok: str) -> str:
    tok = tok.strip().lower()
    if tok in {"zero","one","two","three","four"}: return tok
    if tok == "0": return "zero"
    if tok == "1": return "one"
    if tok == "2": return "two"
    if tok == "3": return "three"
    if tok == "4": return "four"
    raise ValueError(f"Bad clue token: {tok}")


# ------------------------------------------------------------
# 2x2 geometry (vertices 3x3, edges 12)
# Vertex pXY where X,Y in {0,1,2}
# Horizontal edge hXY connects pXY -- p(X+1)Y for X in {0,1}, Y in {0,1,2}
# Vertical edge   vXY connects pXY -- pX(Y+1) for X in {0,1,2}, Y in {0,1}
# Cell cXY where X,Y in {0,1} uses:
#   top    hX,Y
#   bottom hX,Y+1
#   left   vX,Y
#   right  vX+1,Y
# ------------------------------------------------------------
cells = [f"c{x}{y}" for x in range(2) for y in range(2)]

verts = [f"p{x}{y}" for x in range(3) for y in range(3)]

h_edges = [f"h{x}{y}" for x in range(2) for y in range(3)]
v_edges = [f"v{x}{y}" for x in range(3) for y in range(2)]
edges = h_edges + v_edges

# incident edges per cell
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

# edges touching each vertex (for degree constraints)
touch_vertex = {p: [] for p in verts}
def add_touch(e, p1, p2):
    touch_vertex[p1].append(e)
    touch_vertex[p2].append(e)

# horizontal touches
for x in range(2):
    for y in range(3):
        e = f"h{x}{y}"
        p1 = f"p{x}{y}"
        p2 = f"p{x+1}{y}"
        add_touch(e, p1, p2)

# vertical touches
for x in range(3):
    for y in range(2):
        e = f"v{x}{y}"
        p1 = f"p{x}{y}"
        p2 = f"p{x}{y+1}"
        add_touch(e, p1, p2)


# ------------------------------------------------------------
# Parse clues
# ------------------------------------------------------------
clues = {}
for s in clue_inputs:
    c, tok = s.split()
    clues[c] = normalize_clue_token(tok)


# ------------------------------------------------------------
# DOMAIN (constants only)
# include clue symbols that appear
# ------------------------------------------------------------
clue_symbols = {clues[c] for c in clues}
domain = set(map(r, cells + verts + edges + list(clue_symbols)))


# ------------------------------------------------------------
# BACKGROUND facts (Cell/Edge/Vertex + Clue + Incident + Touches)
# ------------------------------------------------------------
bg_facts = []

for c in cells:
    bg_facts.append(f"(Cell {c})")
    if c in clues:
        bg_facts.append(f"(Clue {c} {clues[c]})")

for e in edges:
    bg_facts.append(f"(Edge {e})")

for p in verts:
    bg_facts.append(f"(Vertex {p})")

# Incident(edge, cell)
for c, es in incident_cell.items():
    for e in es:
        bg_facts.append(f"(Incident {e} {c})")

# Touches(edge, vertex)
for p, es in touch_vertex.items():
    for e in es:
        bg_facts.append(f"(Touches {e} {p})")

background = set(map(r, bg_facts))


actions = [
    Action(
        r("(Draw ?e)"),
        precondition=r("(and (Edge ?e) (Undrawn ?e))"),
        additions={r("(On ?e)")},
        deletions={r("(Undrawn ?e)"), r("(not (On ?e))")},
    )
]

start_facts = []
for e in edges:
    start_facts.append(f"(Undrawn {e})")
    start_facts.append(f"(not (On {e}))")

start = set(map(r, start_facts))

def exact_k_on(edges_list, k: int) -> str:
    cases = []
    for on_tuple in itertools.combinations(edges_list, k):
        on_set = set(on_tuple)
        parts = [(f"(On {e})" if e in on_set else f"(not (On {e}))") for e in edges_list]
        cases.append("(and " + " ".join(parts) + ")")
    return "(or " + " ".join(cases) + ")"

def clue_goal_for_cell(c: str) -> str:
    tok = clues[c]  # zero..four
    k_map = {"zero":0,"one":1,"two":2,"three":3,"four":4}
    k = k_map[tok]
    return exact_k_on(incident_cell[c], k)

def degree_0_or_2_goal_for_vertex(p: str) -> str:
    es = touch_vertex[p]  # size 2,3,or4 depending on boundary/interior
    # degree 0: all off
    deg0 = "(and " + " ".join(f"(not (On {e}))" for e in es) + ")"
    # degree 2: choose any 2 on, rest off
    deg2 = exact_k_on(es, 2)
    return "(or " + deg0 + " " + deg2 + ")"

goal_parts = []

for c in cells:
    if c in clues:
        goal_parts.append(clue_goal_for_cell(c))

for p in verts:
    goal_parts.append(degree_0_or_2_goal_for_vertex(p))

goal_parts.append("(or " + " ".join(f"(On {e})" for e in edges) + ")")

goal_str = "(and " + " ".join(goal_parts) + ")"
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

print("CLUES:", clue_inputs)
print("PLAN:")
if not plan:
    print("No plan found")
else:
    for i, step in enumerate(plan, 1):
        print(i, step)
