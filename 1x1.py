import os
os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r

from shadowprover.experimental.sst_prover import SST_Prover
from shadowprover.reasoners.planner import run_spectra


domain = {
    r("c00"),
    r("h00"), r("h01"),
    r("v00"), r("v01"),
}


background = set(
    map(
        r,
        [
            # cell
            "(Cell c00)",

            # edges
            "(Edge h00)", "(Edge h01)",
            "(Edge v00)", "(Edge v01)",

            # incidence (exactly 4 edges around the cell)
            "(Incident h00 c00)",   # top
            "(Incident h01 c00)",   # bottom
            "(Incident v00 c00)",   # left
            "(Incident v01 c00)",   # right
        ],
    )
)

actions = [
    Action(
        r("(Draw ?e)"),
        precondition=r("(and (Edge ?e) (Undrawn ?e))"),
        additions={r("(On ?e)")},
        deletions={r("(Undrawn ?e)")},
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
        ],
    )
)

incident = {
    "c00": ["h00", "h01", "v00", "v01"]
}

goal_str = "(and " + " ".join(f"(On {e})" for e in incident["c00"]) + ")"
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
for i, step in enumerate(result, 1):
    print(i, step)
