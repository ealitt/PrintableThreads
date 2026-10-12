# Printable Threads 0.5.4

Apply can span separate bodies and component occurrences. Selected circular surfaces are measured in assembly coordinates and use one shared axis, axial interval and helix phase. Construction is transformed into each body's owning component coordinates and combines only with selected bodies. Axial gaps remain empty. Failures roll back the entire native batch.

Solid Preview renders every selected target in assembly coordinates and restores all target visibility on cleanup. Diameter and automatically measured thread length display at most three significant figures while geometry and parameter expressions retain the exact measured values.

Repeated occurrences of one component definition still share their native geometry. Compatible local phases are deduplicated; instances that require different local thread geometry must first be made independent with Paste New. This prevents silently adding several phases to every shared instance.

Validation: 33 model tests, 8 installer tests, 32 Fusion cases covering separate bodies and translated/rotated/nested occurrences, plus 5 gap, partial-length and shared-instance cases. The actual command preview, Cancel cleanup, exact measurement retention and two-component commit were exercised in a disposable file. See docs/multi-body-probe.json, docs/multi-body-edge-probe.json and docs/multi-body-command.json.
