import os
import itertools

os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r
from shadowprover.experimental.sst_prover import SST_Prover
from shadowprover.reasoners.planner import run_spectra


def normalize_clue_token(tok) -> str:
    tok = str(tok).strip().lower()
    if tok in {"zero", "one", "two", "three", "four"}:
        return tok
    if tok == "0": return "zero"
    if tok == "1": return "one"
    if tok == "2": return "two"
    if tok == "3": return "three"
    if tok == "4": return "four"
    raise ValueError(f"Bad clue token: {tok}")


def cell_name(rr, cc): return f"c{rr}{cc}"
def h_name(rr, cc): return f"h{rr}{cc}"
def v_name(rr, cc): return f"v{rr}{cc}"


def parse_clues(clue_triples):
    clues = {}
    for rr, cc, val in clue_triples:
        clues[cell_name(rr, cc)] = normalize_clue_token(val)
    return clues



def build_grid(H, W):
    cells = [cell_name(r, c) for r in range(H) for c in range(W)]

    # Horizontal edges: r in [0..H], c in [0..W-1]
    hedges = [h_name(r, c) for r in range(H + 1) for c in range(W)]
    # Vertical edges: r in [0..H-1], c in [0..W]
    vedges = [v_name(r, c) for r in range(H) for c in range(W + 1)]
    edges = hedges + vedges

    # For each cell, list its 4 boundary edges (top,bottom,left,right)
    incident = {}
    for r in range(H):
        for c in range(W):
            incident[cell_name(r, c)] = [
                h_name(r, c),         # top
                h_name(r + 1, c),     # bottom
                v_name(r, c),         # left
                v_name(r, c + 1),     # right
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
            # horizontal edges touching this vertex
            if c > 0:
                inc.append(h_name(r, c - 1))
            if c < W:
                inc.append(h_name(r, c))

            # vertical edges touching this vertex
            if r > 0:
                inc.append(v_name(r - 1, c))
            if r < H:
                inc.append(v_name(r, c))

            incident_vtx[p] = inc

    return vertices, incident_vtx


def exactly_k_of_4(edges4, k: int) -> str:
    """CNF-ish encoding for exactly k edges On among these 4."""
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
            clauses.append(f"(or {x[i]} {x[j]} {x[l]})")    # not all 3 false
        return "(and " + " ".join(clauses) + ")"

    raise ValueError("k must be 0..4")


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


def print_1x1_ascii(on_edges, clue=None):
    dot, h, v, space = "●", "───", "│", "   "
    top = dot + (h if "h00" in on_edges else space) + dot
    midc = f" {clue} " if clue is not None else space
    mid = (v if "v00" in on_edges else " ") + midc + (v if "v01" in on_edges else " ")
    bot = dot + (h if "h01" in on_edges else space) + dot
    print(top)
    print(mid)
    print(bot)

if __name__ == "__main__":
    H, W = 1, 1

    clue_input = [(0, 0, 4)]

    cells, edges, incident = build_grid(H, W)
    vertices, vtx_incident = build_vertices(H, W)
    clues = parse_clues(clue_input)

    domain = set(map(r, edges))

    background = set()

    start = set(map(r, [f"(not (On {e}))" for e in edges]))

    actions = [
        Action(
            r("(Draw ?e)"),
            precondition=r("(not (On ?e))"),
            additions={r("(On ?e)")},
            deletions={r("(not (On ?e))")},
        )
    ]

    clue_goals = []
    if clues:
        k_map = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4}
        for cell, clue_tok in clues.items():
            clue_goals.append(exactly_k_of_4(incident[cell], k_map[clue_tok]))

    clue_goal_str = "(and)" if not clue_goals else (clue_goals[0] if len(clue_goals) == 1 else "(and " + " ".join(clue_goals) + ")")

    vertex_goals = [degree_0_or_2(vtx_incident[v]) for v in vertices]

    # Force a non-empty loop
    nonempty_goal = "(or " + " ".join(f"(On {e})" for e in edges) + ")"

    goal_str = "(and " + " ".join([clue_goal_str] + vertex_goals + [nonempty_goal]) + ")"
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

    print("CLUES:", clue_input)
    print("GOAL:", goal_str)
    print("PLAN:")
    if not plan:
        print("  No plan found")
    else:
        for i, step in enumerate(plan, 1):
            print(i, step)

        on_edges = edges_on_from_plan(plan)
        clue_char = None
        if clues:
            # only 1 cell in 1x1
            clue_tok = clues["c00"]
            clue_char = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4"}[clue_tok]

        print("\nASCII SOLUTION:")
        print_1x1_ascii(on_edges, clue=clue_char)
