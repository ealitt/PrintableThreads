# Printable Threads 0.5.3

Short threads now validate section size against the pitch and cylinder axis rather than an arbitrary quarter-diameter limit. Error messages distinguish section reach, spacing, draft, and axial length; invalid values clear stale derived dimensions.

Apply accepts multiple faces on one coaxial cylinder or circular drafted surface, including mold slots and oblique ends. Joined ribs retain the part's cut boundaries, and every disconnected intersection fragment and resulting body is preserved. Draft uses a straight reference thread at the outside/bore envelope diameter. Excessive draft relative to section reach is rejected.

Select the faces, then enable Solid Preview for an opaque shaded part with visible edges and no blue selection overlay. Turn it off to change faces. Kernel sweep/boolean preview geometry excludes final native normal-clearance finishing and optional chamfers. Preview cleanup restores visibility and removes construction, including in Part documents without changing design intent.

Validation: 33 Python tests; 20 disposable Fusion geometry cases spanning 3.65 mm threads, partial cylinders, two-face mold slots, draft and oblique ends, with both thread directions and bore/outside targets. Preview/commit and Cancel cleanup were exercised through the actual command in a disposable Part document. See the committed diagnostic reports.

The installed add-in can be reloaded from source without restarting Fusion after closing its command dialog. Existing installations are backed up by the installer.
