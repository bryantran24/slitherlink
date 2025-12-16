import os
os.environ['../EPROVER_HOME'] = './eprover/'
from shadowprover.syntax import *
from shadowprover.reasoners.planner import Action
from shadowprover.syntax.reader import r

from functools import cache

from shadowprover.experimental.sst_prover import SST_Prover
from shadowprover.reasoners.planner import run_spectra
from shadowprover.fol.fol_prover import fol_prove

domain = {r("wolf"), r("sheep"), r("cabbage"), r("left"), r("right")}

background = set(
    list(
        map(
            r,
            [
                "(forall [?x ?y] (if (Conflict ?x ?y) (Conflict ?y ?x)))",
                "(Conflict wolf sheep)",
                "(Conflict sheep cabbage)",
                "(not (Conflict wolf cabbage))",
                "(Shore left)",
                "(Shore right)",
                "(Object wolf)",
                "(Object sheep)",
                "(Object cabbage)",
                "(not (= left right))",
                "(forall [?x] (if (Object ?x) (or (= ?x wolf) (= ?x sheep) (= ?x cabbage) )))",
                "(forall [?x ?y ?z] (if (and (On ?x ?y) (On ?x ?z)) (= ?y ?z) ))",
                "(not (= boat left))",
                "(not (= left right))",
                "(forall [?x] (not (Conflict ?x ?x)))",
            ],
        )
    )
)


actions = [
    Action(
        r("(LoadBoat ?obj ?shore)"),
        precondition=r(
            """(and 
                            
                                    (Shore ?shore) 
                                    (Object ?obj)  
                                    (On ?obj ?shore) 
                                    (At boat ?shore))"""
        ),
        additions={
            r("(On ?obj boat)"),
        },
        deletions={r("(On ?obj ?shore)"), r("(not (On ?obj boat))")},
        postconditions={
            r(
                "(or (At boat ?shore) (forall [?c] (if (and (Object ?c) (On ?c boat)) (not (Conflict ?c ?obj)))))"
            ),
            r(
                "(forall [?obj ?y] (if (and (On ?obj boat) (On ?y boat)) (= ?obj ?y) ) )"
            ),
        },
    ),
    Action(
        r("(UnLoadBoat ?obj ?shore)"),
        precondition=r(
            """(and 
                                    (Shore ?shore) 
                                    (Object ?obj) 
                                    (On ?obj boat) 
                                    (At boat ?shore)

                                    )"""
        ),
        additions={r("(On ?obj ?shore)"), r("(not (On ?obj boat))")},
        deletions={
            r("(On ?obj boat)"),
        },
        postconditions={
            r(
                "(or (At boat ?shore) (forall [?c] (if (and (Object ?c) (On ?c ?shore)) (not (Conflict ?c ?obj)))))"
            )
        },
    ),
    Action(
        r("(MoveBoat ?shore1 ?shore2)"),
        precondition=r(
            """(and 
                            (Shore ?shore1) (Shore ?shore2) (not (= ?shore1 ?shore2)) (At boat ?shore1))"""
        ),
        additions={
            r("(At boat ?shore2)"),
        },
        deletions={
            r("(At boat ?shore1)"),
        },
        postconditions={
            r(
                "(forall [?c ?d] (if (and (Object ?c) (Object ?d) (On ?c ?shore1) (On ?d ?shore1)) (not (Conflict ?c ?d))))"
            )
        },
    ),
]
start = set(
    map(
        r,
        [
            "(On wolf left)",
            "(On cabbage left)",
            "(On sheep left)",
            "(At boat left)",
            "(not (On wolf boat))",
            "(not (On sheep boat))",
            "(not (On cabbage boat))",
        ],
    )
)

completions = ["On"]
goal = r(
    """
        (and (On wolf right)  (On sheep right) (On cabbage right))
    """
)
avoid_condition_1 = r(" (if (previous LoadBoat) (not (Next UnLoadBoat)))")
avoid_condition_2 = r(" (if (previous MoveBoat) (not (Next MoveBoat)))")
avoid_condition_3 = r(" (not (first UnLoadBoat))")
avoid_condition_4 = r(" (not (first MoveBoat))")

meta_conditions = {
                avoid_condition_1,
                avoid_condition_2,
                avoid_condition_3,
                avoid_condition_4,
                
                
                }

sst = SST_Prover()
def get_cached_prover(find_answer=True, max_answers=5):
    @cache
    def cached_prover(inputs, output, find_answer=find_answer, max_answers=max_answers):
        return fol_prove(inputs, output, find_answer=find_answer, max_answers=max_answers)
    
    def _prover_(inputs, output, find_answer=find_answer, max_answers=max_answers):
        return cached_prover(frozenset(inputs), output, find_answer, max_answers=max_answers)
    
    return _prover_

result = run_spectra(domain, background, start, goal, actions, get_cached_prover(), completions=completions, meta_conditions=meta_conditions, verbose=False)[0]

print(result)