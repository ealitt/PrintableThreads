# Native feature status — 8 October 2026

0.5.0 is installed and loaded from Fusion's AddIns directory. Its native source checksum matches the repository. The loaded-version record is `installed-loaded-version.json`; installed Create and Apply command records include their exact native source checksum.

## Implemented and tested

Circular / On Center Create and Apply use editable native Coil, Extrude, Offset Faces, Mirror, Move, Pattern, Loft and Combine operations in a named timeline group. The screw remains nominal. The nut has the requested uniform normal clearance on its bore and curved thread surfaces; the default is 0.2 mm. Threads terminate flush. Printing-plane placement uses parametric Move features for knob/floor thickness. Existing operations remain unchanged.

Named PT parameters drive diameter, pitch, section diameter, length, engagement, positive tolerance, starts and phase. Structural choices such as handedness, output, cap presence and knob type are selected at creation. Fusion rejects zero-distance Offset Faces; zero-tolerance creation omits that feature and requires recreation to add one.

Native Coil features come from an original minimal F3D template because the public API cannot create a Coil. Archive import is prohibited in command events, so the command captures its inputs, then builds on a main-thread CustomEvent after destruction. Imported occurrence placement is captured in a timeline snapshot before recomputation. Four stable patterned tool bodies are arranged into 1–4 starts; unused copies coincide, keeping Combine references valid across start-count edits. Pattern elements provide body ordering; `feature.bodies` is unordered.

Current release checks are `native-circular-regression-probe.json`, `native-occurrence-probe.json`, and `installed-*-probe.json`. These pass for native circular construction, physical solid containment about the requested 0.2 mm gap, options, parameter changes, regular external/internal cylinders, assembly occurrences, and mid-timeline insertion. Pure mathematical tests: 31 passed. Installed advanced-profile Create was also checked and retains its original closed solids and timeline grouping.

The editable circular example is open in Fusion and exported at `dist/PrintableThreads-0.5.0-native-example.f3d`. Test handlers were removed and preference saving restored to its actual installed function.

## Incomplete scope

Full native parity for Balanced / Custom rounded trapezoids remains unfinished. Native constrained sections and Coil-guided sweeps can be built, but Fusion rejects some normal offsets with ASM topology errors. Attempts included guided rails, cylindrical guide surfaces, full mating-wall offset, full cutter offset, end-cap offset/restoration, and shell/surface approaches. Failed exploratory probes remain in the repository; they are not passing release checks. The installed commands explicitly keep these options on their original legacy geometry and radial/flank allowances. Do not describe those profiles as fully native, uniformly offset, or associative.

## Research

- [CoilFeatures API](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_CoilFeatures.htm)
- [Archive import and command-event limitation](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/core_ImportManager_importToTarget2.htm)
- [Native Offset Faces](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_OffsetFacesFeatures.htm)
- [Timeline groups](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_TimelineGroups_add.htm)
