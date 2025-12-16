import os
import itertools

os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax.reader import r
from shadowprover.reasoners.planner import Action, run_spectra
from shadowprover.experimental.sst_prover import SST_Prover


# -----------------------------
# 1x2 Slitherlink instance
# Cells: c00 c01
# Horiz edges: h00 h01 (top), h10 h11 (bottom)
# Vert edges:  v00 (left), v01 (middle), v02 (right)
# -----------------------------

# Example: set clues for both cells
clue_input = "c00 3 c01 2"


def normalize_clue_token(tok: str) -> str:
    tok = tok.strip().lower()
    if tok in {"zero", "one", "two", "three", "four"}:
        return tok
    if tok == "0":
        return "zero"
    if tok == "1":
        return "one"
    if tok == "2":
        return "two"
    if tok == "3":
        return "three"
    if tok == "4":
        return "four"
    raise ValueError(f"Bad clue token: {tok}")


def parse_clues(clue_input_str: str) -> dict[str, str]:
    toks = clue_input_str.split()
    if len(toks) % 2 != 0:
        raise ValueError("clue_input must be pairs like: c00 3 c01 2 ...")
    out: dict[str, str] = {}
    for i in range(0, len(toks), 2):
        cell = toks[i]
        clue_tok = normalize_clue_token(toks[i + 1])
        out[cell] = clue_tok
    return out


# 1x2 cells + edges
cells = ["c00", "c01"]
edges = ["h00", "h01", "h10", "h11", "v00", "v01", "v02"]

# Python-side incidence used to expand goals
incident = {
    "c00": ["h00", "h10", "v00", "v01"],  # left cell
    "c01": ["h01", "h11", "v01", "v02"],  # right cell
}

clues = parse_clues(clue_input)

# Validate clue cells
for c in clues:
    if c not in incident:
        raise ValueError(f"Unknown cell {c}. Valid cells: {list(incident.keys())}")

# Domain: objects we mention (cells, edges, clue symbols)
domain = set(map(r, cells + edges + ["zero", "one", "two", "three", "four"]))

# Background: just types + clue declarations + edge declarations
background_items = []
for c in cells:
    background_items.append(f"(Cell {c})")
for e in edges:
    background_items.append(f"(Edge {e})")
for c, clue in clues.items():
    background_items.append(f"(Clue {c} {clue})")
background = set(map(r, background_items))

# Action: draw an undrawn edge
actions = [
    Action(
        r("(Draw ?e)"),
        precondition=r("(and (Edge ?e) (Undrawn ?e))"),
        additions={r("(On ?e)")},
        deletions={r("(Undrawn ?e)"), r("(not (On ?e))")},
    )
]

# Start: all edges undrawn and not on
start_items = []
for e in edges:
    start_items.append(f"(Undrawn {e})")
    start_items.append(f"(not (On {e}))")
start = set(map(r, start_items))


def goal_from_clue(cell: str) -> str:
    clue = clues[cell]
    es = incident[cell]

    def exact_k(k: int) -> str:
        cases = []
        for on_set in itertools.combinations(es, k):
            on_set = set(on_set)
            parts = []
            for e in es:
                parts.append(f"(On {e})" if e in on_set else f"(not (On {e}))")
            cases.append("(and " + " ".join(parts) + ")")
        return "(or " + " ".join(cases) + ")"

    if clue == "zero":
        return "(and " + " ".join(f"(not (On {e}))" for e in es) + ")"
    if clue == "one":
        return exact_k(1)
    if clue == "two":
        return exact_k(2)
    if clue == "three":
        return exact_k(3)
    if clue == "four":
        return "(and " + " ".join(f"(On {e})" for e in es) + ")"
    raise ValueError(f"Unsupported clue: {clue}")


# Goal: satisfy all clue cells
goal_str = "(and " + " ".join(goal_from_clue(c) for c in clues.keys()) + ")"
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


def edges_on_from_plan(plan_steps) -> set[str]:
    on = set()
    for step in plan_steps:
        s = str(step).strip()
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1]
        parts = s.split()
        if len(parts) == 2 and parts[0] == "Draw":
            on.add(parts[1])
    return on


def print_1x2_slitherlink(on_edges: set[str], clue_left=None, clue_right=None):
    dot = "●"
    h = "───"
    v = "│"
    space = "   "

    top = (
        dot + (h if "h00" in on_edges else space) +
        dot + (h if "h01" in on_edges else space) +
        dot
    )

    cL = f" {clue_left} " if clue_left is not None else space
    cR = f" {clue_right} " if clue_right is not None else space

    mid = (
        (v if "v00" in on_edges else " ") + cL +
        (v if "v01" in on_edges else " ") + cR +
        (v if "v02" in on_edges else " ")
    )

    bot = (
        dot + (h if "h10" in on_edges else space) +
        dot + (h if "h11" in on_edges else space) +
        dot
    )

    print(top)
    print(mid)
    print(bot)


if plan:
    on_edges = edges_on_from_plan(plan)
    clue_char = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4"}
    left = clue_char[clues["c00"]] if "c00" in clues else None
    right = clue_char[clues["c01"]] if "c01" in clues else None

    print("\nASCII SOLUTION:")
    print_1x2_slitherlink(on_edges, clue_left=left, clue_right=right)
