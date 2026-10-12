# Printable Threads 0.5.5

Apply now spans separate bodies and component occurrences with a shared thread axis and phase. Every intended body gets its own consuming Join/Cut Combine. Gaps stay empty, unselected bodies remain unchanged, and detached joined fragments are rejected. A failed native batch rolls back all its targets. Compatible repeated component instances are handled once; instances requiring different local thread geometry must be made independent with Paste New.

- **Solid Preview (Beta)** uses an on-demand cached snapshot. Editing clears the outdated snapshot without running sweeps, booleans or tessellation; click **Refresh Solid Preview** when ready. A shared thread tool serves all targets, numeric meshes are cached, and edges are batched. Two-target snapshot construction measured 2.95 s before and 1.52 s after; five cached redraws took about 38 ms.
- **Thread settings memory:** Create and Apply share the latest valid dimensions, profile, pitch, starts, handedness, phase and fit while retaining separate head settings. Generated native bodies store complete thread/head recipes.
- **Automatic knob sizing:** diameter is the larger of thread outside diameter + 2 mm or 1.6 × outside diameter; thickness is 0.3 × outside diameter, bounded to 2–12 mm. Native parameter expressions keep automatic heads proportional after edits. Choose **Knob sizing → Custom**, or edit either dimension, to preserve an override.
- **Cleaner measurements:** diameter and automatically measured thread length display three significant figures while geometry and native expressions retain exact measured values.

Explicit solid refresh still runs on Fusion’s main thread and can pause on complex models. Native normal-clearance finishing and optional chamfers can differ slightly from the beta preview. Apply supports circular cylinders and circular drafted faces sharing a rotational surface; it creates a straight mating thread rather than a tapered fastener.

Validation: 37 Python tests and 8 package/signing tests passed locally. Separate disposable Fusion documents covered 32 cross-body/translated/rotated/nested cases, 5 gap/shared-instance cases, 8 per-target Combine cases, preview edit/refresh/cancel behavior, and automatic/custom head parameter changes. No thread tools remained after the Combine checks; unselected control bodies were unchanged. Local hot reload confirmed all four commands.

Validation evidence: [Combine targets](https://github.com/ealitt/PrintableThreads/blob/v0.5.5/docs/combine-targets-0.5.5.json), [preview command](https://github.com/ealitt/PrintableThreads/blob/v0.5.5/docs/beta-preview-command-0.5.5.json), [preview benchmark](https://github.com/ealitt/PrintableThreads/blob/v0.5.5/docs/preview-performance-0.5.5.json), [head memory](https://github.com/ealitt/PrintableThreads/blob/v0.5.5/docs/head-memory-0.5.5.json).

Download the macOS .pkg, Windows .exe, or portable .zip below. Installers retain their unsigned labels; checksums are included.
