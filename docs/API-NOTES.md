# API evidence and backend decisions

Checked against installed Fusion Python wrappers and Fusion build 2704.1.53 on macOS, 3 October 2026.

- [Helix wire](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_TemporaryBRepManager_createHelixWire.htm): `pitch` receives **lead**, in cm. The sweep extends by the smallest whole number of leads that covers half the profile width and corner radius. Whole-lead extension preserves phase while avoiding the old fixed four-turn overhead on short threads.
- [BRep persistence](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_BRepBodies_add.htm): history designs use a base feature in edit mode. The design's modeling mode is never changed.
- [Guided sweep](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_SweepFeatureInput.htm): two rails plus `SweepProfileNoScalingOption`; sections are tested by kernel containment. The second rail prevents unwanted section rotation.
- [Python template](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/PythonTemplate_UM.htm): the entry point and retained event-handler lifecycle follow the generated-template architecture. A small original helper in `lib/events.py` provides the same retention pattern, without vendored dependencies.
- [Tokens](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_Design_findEntityByToken.htm): edit resolves the base feature token and rejects missing or ambiguous results.
- [Toolbar controls](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/core_ToolbarControls.htm): one `DropDownControl` groups the four commands in `SolidCreatePanel`. Adding it without a position ID appends it to the panel.
- [Command inputs](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/CommandInputs_UM.htm): a collapsed group holds secondary controls. Every visible input sets both `tooltip` and `tooltipDescription`.
- [Custom Graphics](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/CustomGraphics_UM.htm): live preview uses analytical mesh graphics instead of temporary BRep features. This keeps input changes off the timeline and avoids guided sweeps and booleans until the user clicks OK.

Observed during prototyping: `Path.create` on native wire edges inside a scratch component failed with `InternalValidationError: Utils::getObjectPath`. Creating edge proxies for the scratch occurrence and setting sweep `creationOccurrence` fixed the actual Fusion failure. The initial root-component probe remains in `diagnostics/initial_sweep_probe.py` for reference.

Left-hand geometry reflects the proven right-hand sweep across local XZ using a kernel transform. This avoids relying on undocumented negative helix pitch conventions. The diagnostic checks the opposite phase sign and coordinated rotation/translation.

Booleans operate on transient BReps until final creation. Apply uses a native Combine targeted to one existing body, after first verifying the result on a transient copy. New component geometry is regenerated through `BaseFeature.updateBody`; no user body is deleted to simulate editing.

No CoilFeatures creation API, undocumented text-command geometry, worker-thread API calls, CustomFeatures preview API, or surface-normal offset claims are used. On the default recipe, pure mesh generation averages about 0.32 ms on the development Mac (868 vertices, 1,700 triangles); Fusion display refresh is the remaining interactive cost.
