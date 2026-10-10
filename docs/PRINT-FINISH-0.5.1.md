# Printable Threads 0.5.1

Circular Create and Apply add a native Chamfer feature to the cylindrical thread-land boundaries, including the helical edges highlighted in the supplied example. The chamfer is inside the operation's existing timeline group. Existing features remain unchanged.

The nominal distance is `min(0.2 mm, section size / 10, (pitch - section size) / 4)`. Smaller sections and narrower lands receive smaller finishes. Failed operations are retried at half, quarter, and eighth distance; an unsolvable finish is skipped. The editable `PT…_edge_chamfer` parameter controls subsequent changes. This follows Autodesk's [equal-distance chamfer API](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/EqualDistanceChamferFeature_Sample.htm), with explicit BRep edges: face selection through the API returned an empty feature in this Fusion build.

Starts is a main input for every command. Last-used starts and dimensions still use the original preference store.

New Create parts use +Y as their root-coordinate thread axis, away from the ZX plane. Flat print bases lie at Y=0 before user placement offsets. Preview and final creation use the same placement matrix. Apply retains the selected cylinder's axis and position. Construction inside each component remains on local Z.

## Verification

[Physical Fusion MCP results](print-finish-probe.json): all 11 cases pass. Tests include normal and small sections, the user's 15 / 5 / 4 mm dimensions, swapped operations, left-handed multi-start threads, lobed head and blind cap, and Apply on external/internal cylinders at mid-timeline in root and rotated components. The normal chamfer is 0.2 mm; the tested 0.8 mm section uses 0.08 mm. Actual chamfer faces exist, all parts remain single solids, parameter edits recompute without warnings, and print bases remain on ZX. Matched-pair solid intersections contain zero regions for standard, swapped, and left-handed multi-start cases. Fusion boolean success alone does not imply an intersection exists: empty intersection bodies also report success.

The real installed command lifecycle passed for [Create](installed-create-False-False-probe.json) and [Apply on a rotated bore](installed-apply-True-True-probe.json). Reports confirm version 0.5.1, main-input Starts, real chamfer faces, healthy grouped timelines, and matching source hashes. The [loaded version](installed-loaded-version.json) report confirms normal preference saving was restored after tests.

31 pure Python tests pass, and the changed sources compile successfully.

## Limits

The fast mesh preview omits the small chamfer; the completed solid includes it. Automatic native chamfers currently apply to Circular Create/Apply. Balanced/Custom retain their previous legacy geometry. Extreme later parameter edits may require reducing the chamfer parameter or suppressing its feature, as with manually created Fusion chamfers.
