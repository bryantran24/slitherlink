import os
import itertools

os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r

from shadowprover.experimental.sst_prover import SST_Prover
from shadowprover.reasoners.planner import run_spectra


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

domain = {
    r("c00"),
    r("three"),
    r("h00"),
    r("h01"),
    r("v00"),
    r("v01"),
}

incident = {"c00": ["h00", "h01", "v00", "v01"]}
clues = {cell_name: clue_tok}

background = set(
    map(
        r,
        [
            "(Cell c00)",
            f"(Clue {cell_name} {clue_tok})",

            "(Edge h00)", "(Edge h01)", "(Edge v00)", "(Edge v01)",
            "(Incident h00 c00)",
            "(Incident h01 c00)",
            "(Incident v00 c00)",
            "(Incident v01 c00)",
        ],
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
        [
            "(Undrawn h00)", "(Undrawn h01)", "(Undrawn v00)", "(Undrawn v01)",
            "(not (On h00))", "(not (On h01))", "(not (On v00))", "(not (On v01))",
        ],
    )
)

def goal_from_clue(cell):
    clue = clues[cell]
    edges = incident[cell]

    def exact_k(k):
        cases = []
        for on_set in itertools.combinations(edges, k):
            on_set = set(on_set)
            clause_parts = []
            for e in edges:
                clause_parts.append(f"(On {e})" if e in on_set else f"(not (On {e}))")
            cases.append("(and " + " ".join(clause_parts) + ")")
        return "(or " + " ".join(cases) + ")"

    if clue == "zero":
        return "(and " + " ".join(f"(not (On {e}))" for e in edges) + ")"

    if clue == "one":
        return exact_k(1)

    if clue == "two":
        return exact_k(2)

    if clue == "three":
        return exact_k(3)

    if clue == "four":
        return "(and " + " ".join(f"(On {e})" for e in edges) + ")"

    raise ValueError(f"Unsupported clue: {clue}")

goal_str = goal_from_clue(cell_name)
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


def edges_on_from_plan(plan_steps):
    on = set()
    for step in plan_steps:
        s = str(step).strip()
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1]
        parts = s.split()
        if len(parts) == 2 and parts[0] == "Draw":
            on.add(parts[1])
    return on

def print_1x1_slitherlink(on_edges, clue=None):
    dot = "●"
    h = "───"
    v = "│"
    space = "   "

    top = dot + (h if "h00" in on_edges else space) + dot
    center = f" {clue} " if clue is not None else space
    mid = (v if "v00" in on_edges else " ") + center + (v if "v01" in on_edges else " ")
    bot = dot + (h if "h01" in on_edges else space) + dot

    print(top)
    print(mid)
    print(bot)

if plan:
    on_edges = edges_on_from_plan(plan)
    clue_char = {"zero":"0","one":"1","two":"2","three":"3","four":"4"}[clue_tok]
    print("\nASCII SOLUTION:")
    print_1x1_slitherlink(on_edges, clue=clue_char)
