import os

os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r

from shadowprover.experimental.sst_prover import SST_Prover
from shadowprover.reasoners.planner import run_spectra

import time


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


def parse_clues(clue_triples):
    clues = {}
    for rr, cc, val in clue_triples:
        cell = f"c{rr}{cc}"
        clues[cell] = normalize_clue_token(val)
    return clues


def cell_name(rr, cc):
    return f"c{rr}{cc}"


def h_name(rr, cc):
    return f"h{rr}{cc}"


def v_name(rr, cc):
    return f"v{rr}{cc}"


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
    on = set()
    for step in plan_steps:
        s = str(step).strip()
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1]
        name, edge = s.split()
        if name == "Draw":
            on.add(edge)
    return on


def print_ascii(H, W, on_edges, clues):
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

    exactly_2 = pairs[0] if len(pairs) == 1 else "(or " + " ".join(pairs) + ")"
    return "(or " + all_off + " " + exactly_2 + ")"


def goal_from_clue(cell):
    es = incident[cell]
    clue = clues[cell]
    k_map = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4}
    return exactly_k_of_4(es, k_map[clue])


if __name__ == "__main__":
    start_time = time.perf_counter()

    H, W = 1, 2

    # Format: (row, col, clue)
    clue_input = [(0, 0, 3), (0, 1, 3)]

    cells, edges, incident = build_grid(H, W)
    vertices, vtx_incident = build_vertices(H, W)
    clues = parse_clues(clue_input)

    for c in clues:
        if c not in incident:
            raise ValueError(f"Unknown cell {c}. Valid cells: {list(incident.keys())}")

    domain = set(map(r, edges))

    background = set(
        # map(
        #     r,
        #     (
        #         # [f"(Cell {c})" for c in cells] +
        #         [f"(Edge {e})" for e in edges]
        #         # + [f"(Clue {c} {clue})" for c, clue in clues.items()]
        #     ),
        # )
    )
    print("Domain", domain)
    print("Background", background)

    actions = [
        Action(
            r("(Draw ?e)"),
            precondition=r("(not (On ?e))"),
            additions={r("(On ?e)")},
            deletions={r("(not (On ?e))")},
        )
    ]

    start = set(
        map(
            r,
            [f"(not (On {e}))" for e in edges],
        )
    )

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

    # final goal
    all_goals = [clue_goal_str] + vertex_goals + [nonempty_goal]
    goal_str = (
        all_goals[0] if len(all_goals) == 1 else "(and " + " ".join(all_goals) + ")"
    )
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
        print_ascii(H, W, edges_on_from_plan(plan), clues)

    end_time = time.perf_counter()
    elapsed_time = end_time - start_time

    print(f"Elapsed time: {elapsed_time:.4f} seconds")

