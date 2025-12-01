import json
import os

os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.syntax.reader import r

with open("puzzles/3.json") as f:
    data = json.load(f)

width  = data["width"]
height = data["height"]
clues  = data["puzzle"]

def dname(dot_row: int, dot_col: int) -> str:
    """Return the symbolic name of a DOT at coordinates (dot_row, dot_col)."""
    return f"d-{dot_row}-{dot_col}"

def cname(cell_row: int, cell_col: int) -> str:
    """Return the name of a CELL (puzzle square)."""
    return f"c-{cell_row}-{cell_col}"

def hename(dot_row: int, dot_col: int) -> str:
    """Return the name of a HORIZONTAL EDGE starting at dot (dot_row, dot_col)."""
    return f"eh-{dot_row}-{dot_col}"

def vename(dot_row: int, dot_col: int) -> str:
    """Return the name of a VERTICAL EDGE starting at dot (dot_row, dot_col)."""
    return f"ev-{dot_row}-{dot_col}"

object_names = set()


for dot_row in range(height + 1):
    for dot_col in range(width + 1):
        object_names.add(dname(dot_row, dot_col))


h_edges = []
for dot_row in range(height + 1):
    for dot_col in range(width):
        edge_name = hename(dot_row, dot_col)
        h_edges.append(
            (edge_name, (dot_row, dot_col), (dot_row, dot_col + 1))
        )
        object_names.add(edge_name)
        

v_edges = []
for dot_row in range(height):
    for dot_col in range(width + 1):
        edge_name = vename(dot_row, dot_col)
        v_edges.append(
            (edge_name, (dot_row, dot_col), (dot_row + 1, dot_col))
        )
        object_names.add(edge_name)
        
cell_names = []
for cell_row in range(1, height + 1):
    for cell_col in range(1, width + 1):
        cell_name = cname(cell_row, cell_col)
        cell_names.append(cell_name)
        object_names.add(cell_name)
        
domain = {r(name) for name in object_names}

print("Domain objects:")
for obj in sorted(object_names):
    print(" ", obj)
print()


background = set()

# ---- Type declarations ----
for dot_row in range(height + 1):
    for dot_col in range(width + 1):
        background.add(r(f"(dot {dname(dot_row, dot_col)})"))

for edge_name, _, _ in h_edges + v_edges:
    background.add(r(f"(edge {edge_name})"))

for cell_name in cell_names:
    background.add(r(f"(cell {cell_name})"))
    
    
for edge_name, (dot_row1, dot_col1), (dot_row2, dot_col2) in h_edges:
    background.add(r(f"(incident {edge_name} {dname(dot_row1, dot_col1)})"))
    background.add(r(f"(incident {edge_name} {dname(dot_row2, dot_col2)})"))

for edge_name, (dot_row1, dot_col1), (dot_row2, dot_col2) in v_edges:
    background.add(r(f"(incident {edge_name} {dname(dot_row1, dot_col1)})"))
    background.add(r(f"(incident {edge_name} {dname(dot_row2, dot_col2)})"))
    
for cell_row in range(1, height + 1):
    for cell_col in range(1, width + 1):
        cell_name = cname(cell_row, cell_col)

        # The four edges surrounding a cell:
        top_edge    = hename(cell_row - 1, cell_col - 1)
        bottom_edge = hename(cell_row,     cell_col - 1)
        left_edge   = vename(cell_row - 1, cell_col - 1)
        right_edge  = vename(cell_row - 1, cell_col)

        for edge_name in (top_edge, bottom_edge, left_edge, right_edge):
            background.add(r(f"(cell-edge {cell_name} {edge_name})"))

        # ---- CLUES ----
        #
        # Represented as (clue0 C), (clue1 C), …
        #
        clue_value = clues[cell_row - 1][cell_col - 1]
        if clue_value is not None:
            background.add(r(f"(clue{clue_value} {cell_name})"))
            
background.add(r("""
  (forall [?c ?e]
    (if (and (clue4 ?c) (cell-edge ?c ?e))
        (on ?e)))
"""))

print(f"Total background facts: {len(background)}")
for fact in list(background):
    print(fact)
    
from shadowprover.reasoners.planner import Action

actions = [
    Action(
        r("(draw-line ?e)"),
        precondition=r("(and (edge ?e) (off ?e))"),
        additions={
            r("(on ?e)"),
            r("(not (off ?e))"),
        },
        deletions={
            r("(off ?e)"),
            r("(not (on ?e))"),
        },
    ),

    Action(
        r("(erase-edge ?e)"),
        precondition=r("(and (edge ?e) (on ?e))"),
        additions={
            r("(off ?e)"),
            r("(not (on ?e))"),
        },
        deletions={
            r("(on ?e)"),
            r("(not (off ?e))"),
        },
    ),
]

start = set()
for edge_name, _, _ in h_edges + v_edges:
    start.add(r(f"(off {edge_name})"))
    start.add(r(f"(not (on {edge_name}))"))

from functools import cache
from shadowprover.fol.fol_prover import fol_prove
from shadowprover.reasoners.planner import run_spectra

def get_cached_prover(find_answer=True, max_answers=5):
    @cache
    def cached_prover(inputs, output, find_answer=find_answer, max_answers=max_answers):
        return fol_prove(inputs, output, find_answer=find_answer, max_answers=max_answers)
    def _prover_(inputs, output, find_answer=find_answer, max_answers=max_answers):
        return cached_prover(frozenset(inputs), output, find_answer, max_answers=max_answers)
    return _prover_


some_edge = hename(0, 0)
goal = r(f"(on {some_edge})")

completions = ["on", "off"]

result = run_spectra(
    domain,
    background,
    start,
    goal,
    actions,
    get_cached_prover(),
    completions=completions,
    verbose=True,
)[0]

print("Plan:", result)
