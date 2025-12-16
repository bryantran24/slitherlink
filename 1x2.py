import os
import itertools

os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r

from shadowprover.experimental.sst_prover import SST_Prover
from shadowprover.reasoners.planner import run_spectra

H, W = 1, 2

# clue_input = [("c00", 3), ("c01", 3)]
clue_input = [("c00", 4)]


def normalize_clue_token(val) -> str:
    val = str(val).strip().lower()
    if val in {"zero", "one", "two", "three", "four"}:
        return val
    if val == "0": return "zero"
    if val == "1": return "one"
    if val == "2": return "two"
    if val == "3": return "three"
    if val == "4": return "four"
    raise ValueError(f"Bad clue token: {val}")


def parse_clues(clue_pairs):
    """
    Input: [("c00", 3), ("c01", 2)]
    Output: {"c00": "three", "c01": "two"}
    """
    clues = {}
    for cell, val in clue_pairs:
        clues[cell] = normalize_clue_token(val)
    return clues


def cell_name(r, c): return f"c{r}{c}"
def h_name(r, c): return f"h{r}{c}"
def v_name(r, c): return f"v{r}{c}"


def build_grid(H, W):
    cells = [cell_name(r, c) for r in range(H) for c in range(W)]
    hedges = [h_name(r, c) for r in range(H + 1) for c in range(W)]
    vedges = [v_name(r, c) for r in range(H) for c in range(W + 1)]
    edges = hedges + vedges

    incident = {}
    for r in range(H):
        for c in range(W):
            incident[cell_name(r, c)] = [
                h_name(r, c),
                h_name(r + 1, c),
                v_name(r, c),
                v_name(r, c + 1),
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
            # horizontal edges meeting at (r,c): left and right along row r
            if c > 0:
                inc.append(h_name(r, c - 1))   # h{r}{c-1}
            if c < W:
                inc.append(h_name(r, c))       # h{r}{c}

            # vertical edges meeting at (r,c): up and down along col c
            if r > 0:
                inc.append(v_name(r - 1, c))   # v{r-1}{c}
            if r < H:
                inc.append(v_name(r, c))       # v{r}{c}

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
        # top boundary
        line = dot
        for c in range(W):
            line += (HBAR if h_name(r, c) in on_edges else SPACE) + dot
        print(line)

        # middle
        line = ""
        for c in range(W):
            line += (VBAR if v_name(r, c) in on_edges else " ")
            cell = cell_name(r, c)
            line += f" {clue_char[clues[cell]]} " if cell in clues else SPACE
        line += (VBAR if v_name(r, W) in on_edges else " ")
        print(line)

    # bottom boundary
    line = dot
    for c in range(W):
        line += (HBAR if h_name(H, c) in on_edges else SPACE) + dot
    print(line)


cells, edges, incident = build_grid(H, W)
vertices, vtx_incident = build_vertices(H, W)
clues = parse_clues(clue_input)

for c in clues:
    if c not in incident:
        raise ValueError(f"Unknown cell {c}")

domain = set(map(r, cells + edges + ["zero", "one", "two", "three", "four"]))

background = set(
    map(
        r,
        (
            [f"(Cell {c})" for c in cells]
            + [f"(Edge {e})" for e in edges]
            + [f"(Clue {c} {clue})" for c, clue in clues.items()]
        ),
    )
)

actions = [
    Action(
        r("(Draw ?e)"),
        precondition=r("(and (Edge ?e) (Undrawn ?e))"),
        additions={r("(On ?e)")},
        deletions={r("(Undrawn ?e)"), r("(not (On ?e))")},
    )
]

start = set(
    map(
        r,
        [f"(Undrawn {e})" for e in edges]
        + [f"(not (On {e}))" for e in edges],
    )
)

# =========================
# NEW: compact “exactly k of 4” to avoid giant (or (and ...) ...) goals
# (Keeps your overall structure the same, just changes goal generation.)
# =========================
def exactly_k_of_4(edges4, k: int) -> str:
    x  = [f"(On {e})" for e in edges4]
    nx = [f"(not (On {e}))" for e in edges4]

    if k == 0:
        return "(and " + " ".join(nx) + ")"
    if k == 4:
        return "(and " + " ".join(x) + ")"

    # k==3: exactly one is false
    if k == 3:
        clauses = []
        clauses.append("(or " + " ".join(nx) + ")")  # at least one false
        # at most one false: no pair can both be false -> (or xi xj)
        for i in range(4):
            for j in range(i + 1, 4):
                clauses.append(f"(or {x[i]} {x[j]})")
        return "(and " + " ".join(clauses) + ")"

    # k==1: exactly one is true
    if k == 1:
        clauses = []
        clauses.append("(or " + " ".join(x) + ")")  # at least one true
        # at most one true: no pair can both be true -> (or ¬xi ¬xj)
        for i in range(4):
            for j in range(i + 1, 4):
                clauses.append(f"(or {nx[i]} {nx[j]})")
        return "(and " + " ".join(clauses) + ")"

    # k==2: (at most 2) AND (at least 2)
    if k == 2:
        clauses = []
        triples = [(0,1,2), (0,1,3), (0,2,3), (1,2,3)]
        # at most 2: no triple all true -> (or ¬xi ¬xj ¬xk)
        for (i,j,l) in triples:
            clauses.append(f"(or {nx[i]} {nx[j]} {nx[l]})")
        # at least 2: no triple all false -> (or xi xj xk)
        for (i,j,l) in triples:
            clauses.append(f"(or {x[i]} {x[j]} {x[l]})")
        return "(and " + " ".join(clauses) + ")"

    raise ValueError("k must be 0..4")

# =========================
# UPDATED: goal_from_clue now uses compact encoding
# =========================
def goal_from_clue(cell):
    es = incident[cell]  # always 4 edges for a cell
    clue = clues[cell]
    k_map = {"zero":0, "one":1, "two":2, "three":3, "four":4}
    return exactly_k_of_4(es, k_map[clue])

# =========================
# NEW: degree(0 or 2) at each vertex
# (kept your original “enumerate pairs” style, but fixes unary (or) case)
# =========================
def degree_0_or_2(edges_at_vertex):
    # vertex degree is allowed to be 0 or 2 (no endpoints, no T-junctions)

    # 0 edges incident (shouldn't happen in grids, but safe)
    if len(edges_at_vertex) == 0:
        return "(and)"

    # 1 incident edge: must be off
    if len(edges_at_vertex) == 1:
        return f"(not (On {edges_at_vertex[0]}))"

    nx = [f"(not (On {e}))" for e in edges_at_vertex]
    all_off = "(and " + " ".join(nx) + ")"

    # exactly 2 on (enumerate pairs)
    pairs = []
    m = len(edges_at_vertex)
    for i in range(m):
        for j in range(i + 1, m):
            parts = []
            for k in range(m):
                e = edges_at_vertex[k]
                if k == i or k == j:
                    parts.append(f"(On {e})")
                else:
                    parts.append(f"(not (On {e}))")
            pairs.append("(and " + " ".join(parts) + ")")

    # IMPORTANT: avoid unary (or X) which can crash your version
    if len(pairs) == 1:
        exactly_2 = pairs[0]
    else:
        exactly_2 = "(or " + " ".join(pairs) + ")"

    return "(or " + all_off + " " + exactly_2 + ")"

# =========================
# Build clue goal string (avoids unary (and ...))
# =========================
clue_goals = [goal_from_clue(c) for c in clues.keys()]
if len(clue_goals) == 0:
    raise ValueError("Need at least one clue to form a goal.")
elif len(clue_goals) == 1:
    clue_goal_str = clue_goals[0]
else:
    clue_goal_str = "(and " + " ".join(clue_goals) + ")"

# =========================
# Build vertex degree goals
# =========================
vertex_goals = [degree_0_or_2(vtx_incident[v]) for v in vertices]

# =========================
# NEW: require at least one edge ON (prevents empty solution)
# =========================
nonempty_goal = "(or " + " ".join(f"(On {e})" for e in edges) + ")"

# =========================
# Combine all goals (avoids unary (and ...))
# =========================
all_goals = [clue_goal_str] + vertex_goals + [nonempty_goal]
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
