import json
import os

os.environ["EPROVER_HOME"] = "./eprover/"

from shadowprover.syntax import *
from shadowprover.syntax.reader import r

with open("puzzles/1.json") as f:
    data = json.load(f)

width  = data["width"]
height = data["height"]
clues  = data["puzzle"]


# ============================================================================
# 1. Naming helpers for dots / edges / cells
#
# Slitherlink uses a grid of *dots*, and lines are drawn on *edges* between dots.
# Each puzzle "cell" (the squares that hold numbers) is surrounded by four edges.
#
# This logical model uses three kinds of objects:
#
#   DOTS   → the intersection points of the grid
#   EDGES  → the horizontal or vertical line segments between dots
#   CELLS  → the puzzle squares (the areas that may contain numbers)
#
# DOT COORDINATES:
#   A grid with H×W cells always has (H+1)×(W+1) dots.
#   Dot coordinates therefore range from:
#       row = 0 to height
#       col = 0 to width
#
#   Example:
#       For a 2×2 puzzle, height = 2 and width = 2.
#       The dot grid is 3×3:
#           d-0-0   d-0-1   d-0-2
#           d-1-0   d-1-1   d-1-2
#           d-2-0   d-2-1   d-2-2
#
# CELL COORDINATES:
#   Cells lie *between* dots.
#   Cell coordinates therefore start at 1:
#       row = 1 to height
#       col = 1 to width
#
#   For the 2×2 example:
#       c-1-1   c-1-2
#       c-2-1   c-2-2
#
# EDGE NAMING:
#   Edges are pieces of lines between dots. They are named using the coordinates
#   of their starting dot.
#
#   Horizontal edge:
#       eh-r-c  connects dot(r, c) to dot(r, c+1)
#
#   Vertical edge:
#       ev-r-c  connects dot(r, c) to dot(r+1, c)
#
#   For example:
#       eh-1-0 connects d-1-0 to d-1-1
#       ev-0-2 connects d-0-2 to d-1-2
#
# These helper functions below construct the names used in ShadowProver.
# ============================================================================

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

# ============================================================================
# 3. Build DOT / EDGE / CELL objects
#
# These are the constants allowed in ShadowProver reasoning.
# ============================================================================

object_names = set()

# -------------------------
# Dots: (height+1) × (width+1)
# 
# These represent intersections of the imaginary grid.
# So basically every cell has 4 dots at its corners.
# -------------------------
for dot_row in range(height + 1):
    for dot_col in range(width + 1):
        object_names.add(dname(dot_row, dot_col))

# -------------------------
# Horizontal edges:
#
# So basically every cell has a top and bottom horizontal edge 
# that could have a loop line.
# -------------------------
h_edges = []
for dot_row in range(height + 1):
    for dot_col in range(width):
        edge_name = hename(dot_row, dot_col)
        h_edges.append(
            (edge_name, (dot_row, dot_col), (dot_row, dot_col + 1))
        )
        object_names.add(edge_name)

# -------------------------
# Vertical edges:
#
# So basically every cell has a left and right vertical edge 
# that could have a loop line.
# -------------------------
v_edges = []
for dot_row in range(height):
    for dot_col in range(width + 1):
        edge_name = vename(dot_row, dot_col)
        v_edges.append(
            (edge_name, (dot_row, dot_col), (dot_row + 1, dot_col))
        )
        object_names.add(edge_name)

# -------------------------
# Cells:
#
# Exactly height × width
#
# Each “cell” is the unit square between:
#
#   top-left     dot (row-1, col-1)
#   top-right    dot (row-1, col)
#   bottom-left  dot (row,   col-1)
#   bottom-right dot (row,   col)
#
# and touching 4 edges:
#   top, bottom, left, right
#
# This is where clues (0 - 3) live.
# -------------------------
cell_names = []
for cell_row in range(1, height + 1):
    for cell_col in range(1, width + 1):
        cell_name = cname(cell_row, cell_col)
        cell_names.append(cell_name)
        object_names.add(cell_name)
        

# ShadowProver domain = every object constant
domain = {r(name) for name in object_names}

print("Domain objects:")
for obj in sorted(object_names):
    print(" ", obj)
print()

# ============================================================================
# 4. Background: types, incidence, cell-edge, clues
#
# (dot X)                     says X is a dot
# (edge E)                    says E is an edge
# (cell C)                    says C is a puzzle square
# (incident E D)              says edge E touches dot D
# (cell-edge C E)             says edge E borders cell C
# (clueN C)                   says cell C has clue N
#
# ============================================================================

background = set()

# ---- Type declarations ----
for dot_row in range(height + 1):
    for dot_col in range(width + 1):
        background.add(r(f"(dot {dname(dot_row, dot_col)})"))

for edge_name, _, _ in h_edges + v_edges:
    background.add(r(f"(edge {edge_name})"))

for cell_name in cell_names:
    background.add(r(f"(cell {cell_name})"))

# ---- INCIDENT RELATION ----
#
# (incident E D)
#
# Means: “Edge E touches dot D.”
#
# Every edge has two endpoints → therefore two INCIDENT facts.
#
# Example:
#   (incident eh-1-0 d-1-0)
#   (incident eh-1-0 d-1-1)
#
# This is essential for loop reasoning:
#
#   • A dot must have degree 0 or 2 in a valid slitherlink loop.
#   • Degree is computed by counting ON edges incident to each dot.
# ---------------------------------------------------------------------------

for edge_name, (dot_row1, dot_col1), (dot_row2, dot_col2) in h_edges:
    background.add(r(f"(incident {edge_name} {dname(dot_row1, dot_col1)})"))
    background.add(r(f"(incident {edge_name} {dname(dot_row2, dot_col2)})"))

for edge_name, (dot_row1, dot_col1), (dot_row2, dot_col2) in v_edges:
    background.add(r(f"(incident {edge_name} {dname(dot_row1, dot_col1)})"))
    background.add(r(f"(incident {edge_name} {dname(dot_row2, dot_col2)})"))

# ---- CELL-EDGE RELATION ----
#
# (cell-edge C E)
#
# Means: “Edge E is one of the 4 edges bordering cell C.”
#
# Used to apply the clue rule:
#    clue k → exactly k edges must be ON around the cell.
#
# ---------------------------------------------------------------------------

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
            
            
# clue0: all 4 bordering edges must be OFF
background.add(r("""
  (forall [?c ?e]
    (if (and (clue0 ?c) (cell-edge ?c ?e))
        (off ?e)))
"""))

# clue4: all 4 bordering edges must be ON
# background.add(r("""
#   (forall [?c ?e]
#     (if (and (clue4 ?c) (cell-edge ?c ?e))
#         (on ?e)))
# """))

print("Some background facts (first 20):")
for fact in list(background):
    print(" ", fact)
print(f"... total background facts: {len(background)}\n")

from shadowprover.reasoners.planner import Action

# ============================================================================
# Actions
#
# Two parameterized actions are defined:
#
# draw-edge ?e —
#     Turns an edge ?e ON.
#     Preconditions:
#         (edge ?e) and (off ?e)
#     Effects:
#         Adds  (on ?e)              — edge is now part of the loop
#         Adds  (not (off ?e))       — record that it is not off
#         Deletes (off ?e)           — remove old “off” fact
#         Deletes (not (on ?e))      — remove old negation
#
# erase-edge ?e —
#     Turns an edge ?e OFF.
#     Preconditions:
#         (edge ?e) and (on ?e)
#     Effects:
#         Adds  (off ?e)             — edge is now not in the loop
#         Adds  (not (on ?e))        — record that it is not on
#         Deletes (on ?e)            — remove old “on” fact
#         Deletes (not (off ?e))     — remove old negation
#
# ============================================================================

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

# Start: all edges off
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




