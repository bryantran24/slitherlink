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
# start
# -----------------------------
start = set(map(r,
    [f"(Undrawn {e})" for e in edges] +
    [f"(not (On {e}))" for e in edges]
))

# -----------------------------
# helpers to build constraints
# -----------------------------
def exact_k_on(es, k):
    n = len(es)
    if k < 0 or k > n:
        return "(and (On h00) (not (On h00)))"  # false

    if k == 0:
        return "(and " + " ".join(f"(not (On {e}))" for e in es) + ")"
    if k == n:
        return "(and " + " ".join(f"(On {e})" for e in es) + ")"

    cases = []
    for on_tuple in itertools.combinations(es, k):
        on_set = set(on_tuple)
        parts = [(f"(On {e})" if e in on_set else f"(not (On {e}))") for e in es]
        cases.append("(and " + " ".join(parts) + ")")
    return "(or " + " ".join(cases) + ")"

def degree_leq_2_formula(es):
    """
    Fast invariant: forbid degree 3 or 4.
    For a vertex with edges es, degree>2 means: there exist 3 distinct edges all On.
    We compile: NOT( OR over all triples (and On e1 On e2 On e3) )
    """
    triples = list(itertools.combinations(es, 3))
    if not triples:
        return "(or (On h00) (not (On h00)))"  # true

    bad = []
    for (a,b,c) in triples:
        bad.append(f"(and (On {a}) (On {b}) (On {c}))")
    return "(not (or " + " ".join(bad) + "))"

# -----------------------------
# Build postconditions (invariants) for Draw
# -----------------------------
vertex_invariants = []
for p in verts:
    es = touch_vertex[p]
    vertex_invariants.append(degree_leq_2_formula(es))

# OPTIONAL (stronger but can prune too hard early):
# forbid degree 1 at end only, not during search.
# We'll keep ONLY <=2 as invariant.

postconds = { r(f) for f in vertex_invariants }

actions = [
    Action(
        r("(Draw ?e)"),
        precondition=r("(and (Edge ?e) (Undrawn ?e))"),
        additions={r("(On ?e)")},
        deletions={r("(Undrawn ?e)"), r("(not (On ?e))")},
        postconditions=postconds,  # <-- huge speedup vs putting it in the goal
    )
]

# -----------------------------
# Goal: ONLY the clue constraint (small)
# -----------------------------
k_map = {"zero":0,"one":1,"two":2,"three":3,"four":4}
goal_str = exact_k_on(incident_cell[cell_name], k_map[clue_tok])
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

print("CLUE INPUT:", clue_input)
print("GOAL:", goal_str)
print("PLAN:")
if not plan:
    print("  No plan found")
else:
    for i, step in enumerate(plan, 1):
        print(i, step)
