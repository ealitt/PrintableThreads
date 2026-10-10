# Native feature consolidation in 0.5.2

The open Untitled example uses its grip circles in one sketch and extrudes the profiles together. Inspection was read-only; all modeling tests used disposable documents.

The circular native backend now builds the existing lobed knob outline in one sketch, defers sketch computation while adding its circles and dimensions, then joins every closed profile in one extrusion. It retains the original circle sizes, spacing, lobe count and print-base placement. Axial offsets use native Extrude start offsets instead of additional construction planes.

Through nuts use one annular sketch and extrusion. Blind nuts use a blank extrusion and direct bore cut. The screw entry uses one annular sketch and a parameter-driven drafted cut in place of multiple envelope, loft and Combine features. Standalone cutting tools rely on the blank to clip their ends; joined ribs and blind nut tools still receive explicit flush trimming. Apply retains bounded trimming to protect geometry outside the chosen thread interval, and drops an unused construction axis.

## Measured timeline reductions

| Circular matched pair | 0.5.1 entries | 0.5.2 entries |
| --- | ---: | ---: |
| Default six-lobe knob | 73 | 34 |
| Blind cap | 75 | 37 |
| Cylindrical knob | 49 | 34 |
| Twelve-lobe knob | 97 | 34 |
| Left-handed, three starts, swapped cut/join | 77 | 38 |
| No knob or entry | 35 | 29 |

These counts measure a fresh Hybrid document. Fusion can add a design-intent conversion entry outside the thread group when a command starts in a Part document.

The four stable thread tool identities and phase feature remain, preserving later edits to starts and phase. A simpler pattern candidate failed Fusion's angle limits; it is not shipped. Existing operations and legacy Balanced/Custom construction remain unchanged. Features are still native and editable, inside their timeline groups.

## Evidence

[Optimization comparisons](optimization-probe.json) compare the old and new bodies through differences in both directions for six combinations, before and after parameter edits. [Print and Apply checks](print-finish-probe.json) exercise eleven cases covering chamfers, mating interference, +Y print orientation, external/internal application in root and rotated components, and middle-of-timeline insertion. Reports include actual solid geometry and healthy feature recomputation.

The real installed [Create command](installed-create-False-False-probe.json) tested the new lobed knob and entry; the installed [Apply command](installed-apply-True-True-probe.json) tested a rotated bore before a downstream feature. [Loaded-version evidence](installed-loaded-version.json) confirms 0.5.2 and restored preference saving. 31 Python tests pass.

Feature-count reductions do not imply equal wall-clock reductions: native Coil import, booleans and surface offsets remain. Timings in the comparison report are observed single-run measurements, not a guaranteed speedup.
