import os

os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r

from shadowprover.experimental.sst_prover import SST_Prover
from shadowprover.reasoners.planner import run_spectra


domain = {
    r("c00"),
    r("three"),
    r("h00"),
    r("h01"),
    r("v00"),
    r("v01"),
}


background = set(
    map(
        r,
        [
            # cell
            "(Cell c00)",
            "(Clue c00 three)",
            # edges
            "(Edge h00)",
            "(Edge h01)",
            "(Edge v00)",
            "(Edge v01)",
            # incidence (exactly 4 edges around the cell)
            "(Incident h00 c00)",  # top
            "(Incident h01 c00)",  # bottom
            "(Incident v00 c00)",  # left
            "(Incident v01 c00)",  # right
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
            "(Undrawn h00)",
            "(Undrawn h01)",
            "(Undrawn v00)",
            "(Undrawn v01)",
            "(not (On h00))",
            "(not (On h01))",
            "(not (On v00))",
            "(not (On v01))",
        ],
    )
)

incident = {"c00": ["h00", "h01", "v00", "v01"]}

clues = {"c00": "three"}


def goal_from_clue(cell):
    clue = clues[cell]
    edges = incident[cell]

    if clue == "four":
        return "(and " + " ".join(f"(On {e})" for e in edges) + ")"

    if clue == "three":
        # exactly 3 On == choose 1 edge to be NOT On, the other 3 are On
        cases = []
        for off in edges:
            on_edges = [e for e in edges if e != off]
            case = (
                "(and "
                + " ".join([f"(On {e})" for e in on_edges] + [f"(not (On {off}))"])
                + ")"
            )
            cases.append(case)
        return "(or " + " ".join(cases) + ")"
    raise ValueError("Unsupported clue")


goal_str = goal_from_clue("c00")
goal = r(goal_str)

sst = SST_Prover()

result = run_spectra(
    domain,
    background,
    start,
    goal,
    actions,
    sst.get_cached_shadow_prover2(),
    verbose=False,
)[0]

print("GOAL:", goal_str)
print("PLAN:")

if not result:
    print(" No plan found")
else:
    for i, step in enumerate(result, 1):
        print(i, step)


result = ["Draw h00", "Draw v00", "Draw h01", "Draw v01"]  # for testing drawing


def edges_on_from_plan(plan):
    on = set()
    for step in plan:
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

    # top row
    top = dot
    top += h if "h00" in on_edges else space
    top += dot

    # middle row (put clue in center if present)
    center = f" {clue} " if clue is not None else space
    mid = (v if "v00" in on_edges else " ") + center + (v if "v01" in on_edges else " ")

    # bottom row
    bot = dot
    bot += h if "h01" in on_edges else space
    bot += dot

    print(top)
    print(mid)
    print(bot)


on_edges = edges_on_from_plan(result)
print_1x1_slitherlink(on_edges, clue="4")

