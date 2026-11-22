# Proposed contributor replies • drafts only

## Issue 113 — edge lines, load sharing and skew

I reran 25 m, three- and four-girder plate bridges. The physical result keys now agree across the design data and analysis output. The edge lines still receive main-girder steel stiffness. On the straight three-girder model each edge carries 87.84 kN·m from girder self-weight, while the physical girders carry 87.14–87.51 kN·m each. An isolated simply supported girder gives 146.45 kN·m. The total support reaction balances the input, so it would be misleading to close the stiffness issue based on counts or equilibrium alone. Is there a documented deck-edge stiffness and staging convention we can use for a reference comparison?

At ±5°, the SciPy warnings originated in load coordinate interpolation. A direct inversion removes the warnings on these meshes. The assembled girder self-weight remains short by 2.09 kN (+5°, three girders) and 2.79 kN (−5°, four girders). I would keep those skew demands provisional.

## Issue 20 — density propagation

With the section held fixed at 0.02388012 m², 85 kN/m³ reaches the frozen material object as 85,000 N/m³ and produces 2.029810 kN/m per girder. In a straight three-girder, 25 m case the total applied self-weight and reaction magnitude both equal 152.235765 kN. Chapter 3 reports 85.0 kN/m³. This confirms the density path for the tested fixture. Girder load sharing remains under investigation separately.

## Issue 91 — zero overhang

With zero overhang, the outer longitudinal lines are structural girders. The original self-weight loop skipped both. In a three-girder control this gave 46.865 kN instead of 140.594 kN. Using the model's physical girder list restores the full reaction and gives 145.946 kN·m per girder against a continuous simply supported reference of 146.452 kN·m.
