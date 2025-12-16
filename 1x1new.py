import os

os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r

from shadowprover.experimental.sst_prover import SST_Prover
from shadowprover.reasoners.planner import run_spectra


# constants only
domain = {r("eT"), r("eR"), r("eB"), r("eL"), r("c00"), r("four")}

background = set(
    map(
        r,
        [
            # edges
            "(Edge eT)",
            "(Edge eR)",
            "(Edge eB)",
            "(Edge eL)",
            "(not (= eT eR))",
            "(not (= eT eB))",
            "(not (= eT eL))",
            "(not (= eR eB))",
            "(not (= eR eL))",
            "(not (= eB eL))",
            # cell + clue as symbol (no numerals)
            "(Cell c00)",
            "(Clue c00 four)",
            # incidence: edges around the cell
            "(Incident eT c00)",
            "(Incident eR c00)",
            "(Incident eB c00)",
            "(Incident eL c00)",
            # Optional: finite closure so QA stays finite
            "(forall [?x] (if (Edge ?x) (or (= ?x eT) (= ?x eR) (= ?x eB) (= ?x eL))))",
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
            "(Undrawn eT)",
            "(Undrawn eR)",
            "(Undrawn eB)",
            "(Undrawn eL)",
        ],
    )
)

# GOAL: satisfy the clue (for 1x1, clue=four means all incident edges On)
goal = r("""
(forall [?e]
    (if (Incident ?e c00) (On ?e)))
""")

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

print(result)
