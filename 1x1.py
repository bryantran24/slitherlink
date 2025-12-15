import os
os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r

from shadowprover.experimental.sst_prover import SST_Prover
from shadowprover.reasoners.planner import run_spectra

domain = {r("eT"), r("eR"), r("eB"), r("eL")}

background = set(
    list(
        map(
            r,
            [
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
            ],
        )
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

goal = r("(and (On eT) (On eR) (On eB) (On eL))")

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
