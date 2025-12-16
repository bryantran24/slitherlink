import os

os.environ["EPROVER_HOME"] = "./../eprover/"
from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r


from shadowprover.experimental.sst_prover import SST_Prover
from shadowprover.reasoners.planner import run_spectra

domain = {r("a"), r("b"), r("c")}

background = set(
    list(
        map(
            r,
            [
                "(agent a)",
                "(agent b)",
                "(agent c)",
                "(room p1)",
                "(room p2)",
                "(not (= a b))",
                "(not (= a c))",
                "(not (= b c))",
            ],
        )
    )
)

actions = [
    Action(
        r("(left ?a)"),
        precondition=r("(and (agent ?a) (at ?a p2))"),
        additions={r("(at ?a p1)"), r("(not (at ?a p2))")},
        deletions={r("(at ?a p2)"), r("(not (at ?a p1))")},
    ),
    Action(
        r("(right ?a)"),
        precondition=r("(and (agent ?a) (at ?a p1))"),
        additions={r("(at ?a p2)"), r("(not (at ?a p1))")},
        deletions={r("(at  ?a p1)"), r("(not (at ?a p2))")},
    ),
    Action(
        r("(shareboth ?a1 ?a2 ?a3 ?r)"),
        precondition=r(
            """(and 
                    (agent ?a1)
                    (agent ?a2)
                    (agent ?a3)
                    (room ?r)
                    ; Precondition
                    (at ?a1 ?r)
                    (at ?a2 ?r)
                    (at ?a3 ?r)
                    (not (= ?a1 ?a2))
                    (not (= ?a1 ?a3))
                    (not (= ?a2 ?a3))
            )"""
        ),
        additions={
            r("(Believes! ?a2 (the ?a1))"),
            r("(Believes! ?a3 (the ?a1))"),
            r("(Believes! ?a1 (Believes! ?a2 (the ?a1)))"),
            r("(Believes! ?a1 (Believes! ?a3 (the ?a1)))"),
        },
        deletions={
            r("(not (Believes! ?a2 (the ?a1)))"),
            r("(not (Believes! ?a3 (the ?a1)))"),
            r("(not (Believes! ?a1 (Believes! ?a2 (the ?a1))))"),
            r("(not (Believes! ?a1 (Believes! ?a3 (the ?a1))))"),
        },
    ),
    Action(
        r("(sharesingle ?a1 ?a2 ?a3 ?r)"),
        precondition=r(
            """(and 
                    (agent ?a1)
                    (agent ?a2)
                    (agent ?a3)
                    (room ?r)
                    ; Precondition
                    (at ?a1 ?r)
                    (at ?a2 ?r)
                    (not (at ?a3 ?r))
                    (not (= ?a1 ?a2))
                    (not (= ?a1 ?a3))
                    (not (= ?a2 ?a3))
            )"""
        ),
        additions={
            r("(Believes! ?a2 (the ?a1))"),
            r("(Believes! ?a1 (Believes! ?a2 (the ?a1)))"),
        },
        deletions={
            r("(not (Believes! ?a2 (the ?a1)))"),
            r("(not (Believes! ?a1 (Believes! ?a2 (the ?a1))))"),
        },
    ),
]

start = set(
    map(
        r,
        [
            "(at a p1)",
            "(not (at a p2))",
            "(at b p1)",
            "(not (at b p2))",
            "(at c p1)",
            "(not (at c p2))",
            "(Believes! a (the a))",
            "(Believes! b (the b))",
            "(Believes! c (the c))",
            "(not (Believes! a (the b)))",
            "(not (Believes! a (the c)))",
            "(not (Believes! b (the a)))",
            "(not (Believes! b (the c)))",
            "(not (Believes! c (the a)))",
            "(not (Believes! c (the b)))",
        ],
    )
)

goal = r(
    """(and 
                (Believes! b (the a)) 
                (Believes! a (Believes! b (the a)))
                 (not (Believes! c (the a)))
                )"""
)

sst = SST_Prover()


goal = r(
    """(and 
                (Believes! b (the a)) 
                (Believes! a (Believes! b (the a)))
                 (not (Believes! c (the a)))
                )"""
)
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