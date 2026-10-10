# Printable Threads for Autodesk Fusion

A dependency-free Python add-in for modeled FDM threads: circular On Center and rounded trapezoidal profiles, 1–4 starts, left/right hand, knob screws, matching nuts/blind caps, cylindrical-face application, and fit coupons. Dimensions are entered with Fusion's native unit-aware controls.

## Index

- [Download and install](#download-and-install)
- [Mac installer blocked: quarantine command and Open Anyway](#mac-installer-blocked)
- [Windows installer blocked: Unblock and SmartScreen](#windows-installer-blocked)
- [Windows Defender quarantine or malware detection](#windows-defender-quarantine-or-malware-detection)
- [Tool commands and parameters](#commands)
- [Printing and dimensions](#printing-and-dimensions)
- [Release scope](#release-scope)
- [Development](#development)
- [Native validation](#native-validation)
- [Signing setup](docs/SIGNING-SETUP.md)

## Download and install

Download the [0.5.2 release](https://github.com/ealitt/PrintableThreads/releases/tag/v0.5.2):

- **[macOS installer (.pkg)](https://github.com/ealitt/PrintableThreads/releases/download/v0.5.2/PrintableThreads-0.5.2-macOS-unsigned.pkg)**
- **[Windows installer (.exe)](https://github.com/ealitt/PrintableThreads/releases/download/v0.5.2/PrintableThreads-0.5.2-Windows-unsigned.exe)**
- **[ZIP fallback](https://github.com/ealitt/PrintableThreads/releases/download/v0.5.2/PrintableThreads-0.5.2.zip)**

Close Fusion, double-click your installer, then reopen Fusion. Open **Design → Solid → Create → Printable Threads** at the bottom of Create. If missing, press **Shift+S → Add-Ins → PrintableThreads → Run**, then enable **Run on Startup**. Fresh installs default to startup enabled; upgrades can retain Fusion's prior preference.

**No separate Python is needed for the native installers.** Upgrades back up the previous installation and preserve saved settings. The Mac package requests administrator authorization; Windows installs for your user without elevation.

These engineering-preview installers are **unsigned**, and the Mac package is **not notarized**. OS security prompts or blocks are possible. The repository is currently private and requires GitHub access. See the [installation guide](docs/INSTALLATION.md) for security prompts, the manual ZIP method, uninstalling, signing and Autodesk App Store options.

An automated signing workflow is now available, but publisher accounts and credentials
are not configured yet. See [one-time signing setup](docs/SIGNING-SETUP.md). Current
release files keep their unsigned labels until real platform verification succeeds.

### Mac installer blocked

For the unsigned **0.5.2** package downloaded into your **Downloads** folder, open
**Terminal** and remove only its quarantine attribute:

```sh
xattr -d com.apple.quarantine ~/Downloads/PrintableThreads-0.5.2-macOS-unsigned.pkg
```

Then open the installer:

```sh
open ~/Downloads/PrintableThreads-0.5.2-macOS-unsigned.pkg
```

Optionally check the remaining attributes:

```sh
xattr -l ~/Downloads/PrintableThreads-0.5.2-macOS-unsigned.pkg
```

If `com.apple.quarantine` is absent, it has been removed. An error saying that the
attribute does not exist means it was already absent. Change the path if you saved
the package elsewhere or downloaded another version. Use `xattr -d` instead of
`xattr -c`: `-d` removes just the named attribute; `-c` clears all extended attributes.
No `sudo` or recursive removal is needed for this downloaded package.

This removes the downloaded-file quarantine marker; it does **not** sign, notarize
or scan the installer. Use it only for a release you trust. Other security checks or
managed-device policies can still block installation.

**Without Terminal:** double-click the package, dismiss the warning, then open
**System Settings → Privacy & Security → Security → Open Anyway**. Authenticate and
confirm, then follow the installer. This is [Apple's supported per-file exception](https://support.apple.com/en-us/102445).

### Windows installer blocked

Windows can attach a **Mark of the Web** (`Zone.Identifier`) to downloaded files.
Its closest equivalent to the Mac command is **Unblock-File**. After checking that
you trust the download, open **PowerShell** and run:

```powershell
Unblock-File -LiteralPath "$env:USERPROFILE\Downloads\PrintableThreads-0.5.2-Windows-unsigned.exe"
```

Then double-click the installer in Downloads. If you saved it elsewhere, change the
path. No administrator PowerShell session is normally needed for your own download.

**Without PowerShell:** right-click the `.exe` in File Explorer → **Properties →
General**, select **Unblock** if shown, then **Apply → OK**. Microsoft's
[Unblock-File reference](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/unblock-file)
confirms that this removes the download marker and performs the same action as that checkbox.

For an **unrecognized-app** SmartScreen warning such as **Windows protected your PC**,
**More info → Run anyway** may be available for a download you trust. See
[Microsoft's installer guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/publish-first-app).
Unblocking does not add a signature or override Defender antivirus, Smart App Control,
or organizational policy; some blocks offer no per-file exception.

### Windows Defender quarantine or malware detection

A Defender antivirus detection is different from an unsigned/unknown-publisher
warning. If the installer disappears or Defender reports a threat, open **Windows
Security → Virus & threat protection → Protection history** and expand the matching
entry to see the detected threat, affected file and action taken.

`Unblock-File` does not restore a quarantined file. Do not assume a detection is a
false positive merely because this installer is unsigned. If it appears incorrect,
record the detection name and file hash and report it to the publisher for review.
Microsoft's [Protection History guide](https://support.microsoft.com/en-us/windows/security/windows-security/protection-history-in-the-windows-security-app)
explains quarantine and restore actions; restoration can cause the file to be detected
again. Avoid disabling antivirus or adding broad folder exclusions to install the add-in.

## Commands

**Create Printable Thread** generates a screw, female member, or matched pair as separate components. The main dialog follows Fusion's Coil workflow and starts with five main values:

- **Diameter** — the Coil diameter: the circular section center follows this diameter. The base shaft also uses this diameter.
- **Pitch** — axial spacing between neighboring thread ridges.
- **Section size** — full diameter of the circular section, matching Fusion Coil’s **Circular / On Center** setting. The section is centered on the shaft surface. In the default cut-screw mode, the screw outside diameter stays at Diameter and the groove reaches half a section size inward. With the swapped joined-screw mode, outside diameter = Diameter + Section size.
- **Starts** — number of intertwined helices, from 1 to 4. Lead is pitch × starts.
- **Thread length** — axial length to cover. Revolutions are calculated as `length ÷ (pitch × starts)`.
- **3D print tolerance** — initially **0.2 mm**. Circular Create and Apply use a uniform offset normal to every nut mating surface, including the straight bore and curved thread. The bore grows by 0.4 mm in diameter; the screw remains nominal.

Outside diameter, lead, revolutions, and fit are shown as derived values. The Output dropdown chooses the part to create. **More Options** is collapsed until needed and contains handedness, fit, custom cross-section, knob, female-part, and placement controls. Female and knob diameters follow the main diameter and section size until you edit them directly. Every input includes a short tooltip and a longer plain-language explanation.

**More Options → Cross-section** defaults to **Circular / On Center**. The diameter and section-size conventions follow [Autodesk’s Coil reference](https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-REF-COIL.htm). For example, diameter 12 mm and section size 2 mm make a cut screw with outside diameter 12 mm and groove-bottom diameter 10 mm; the swapped joined screw has outside diameter 14 mm. Use one start to match Coil pitch directly; with multiple starts the helix lead is Pitch × Starts. Thread length is trimmed to the requested axial interval, and knobs/entries are additional thread-tool features. Circular nut construction offsets the mating geometry by the requested normal clearance.

**Balanced and Custom retain the original legacy construction**, trapezoidal profiles, radial-height sizing, and separate radial/flank allowances. Their native surface-offset rewrite is unfinished: Fusion rejects some rounded-profile offsets. These options remain usable, but they are not part of the native parametric conversion. Existing body recipes preserve their original shape when loaded by Edit. Last-used settings from older versions migrate to a circular section with twice the previous radial height, preserving the outside diameter.

**More Options → Swap cut / join** is off by default: the screw has a cut groove and the nut has a joined inward rib. Turn it on for a joined screw rib and a cut nut groove. The setting is remembered. Existing body recipes retain their original behavior when edited. For circular profiles, the default nut rib is offset inward normally and the entire straight bore is enlarged consistently. Swap uses an outward normal offset of the nut cutting tool.

Nut threads extend full-depth to both planar end faces and are trimmed flush. Entry taper affects the screw only.

Circular Create and Apply finish the cylindrical thread lands with a native **Print edge chamfer**, inside the same timeline group. Its distance is `min(0.2 mm, section size / 10, (pitch − section size) / 4)`: normal sections get 0.2 mm, while small or closely spaced sections get less. Fusion tries smaller distances if the first size fails; an unsolvable finish is skipped rather than failing the thread. Edit `PT…_edge_chamfer` in Change Parameters to adjust it. The fast mesh preview shows placement and thread dimensions; the small chamfer appears in the completed solid. Existing operations and legacy Balanced/Custom geometry are unchanged.

New standalone parts are placed for printing on the **ZX plane (Y=0)**, with their thread axes pointing along **+Y**. Screws rest on their flat knob/head face or, without a head, their end. Nuts rest on their flat face, and blind caps on their outside floor. Position Y offsets this print plane. Top/Bottom views look along the thread axes when Fusion uses its default Y-up orientation. Apply preserves the selected cylinder’s axis and placement.

The construction component’s local Z remains its screw axis; positions use the root component's coordinates. Phase is measured from +X toward +Y. The default is a 12 mm Coil diameter, 3 mm pitch, 18 mm thread, 2 mm circular section and six-lobe knob; the default cut screw has a 12 mm outside diameter. Female engagement is independent of shaft length. Caps have a floor below Z=0; the floor is a designed stop, not guaranteed tip clearance for every insertion depth.

Fusion's current New Document command creates an empty Part design, which cannot contain the separate components used by this add-in. Printable Threads promotes a completely empty Part document to Hybrid design intent when you click OK. Opening and cancelling the dialog leaves the document unchanged. Create and Apply can also promote populated Part documents on OK. Fit Test requires Hybrid or Assembly intent for populated Part documents.

**Apply Printable Thread** accepts a full cylindrical face bounded by two circular end edges. Partial and interrupted cylinders are not supported. By default, external faces receive cut grooves and internal faces receive joined ribs; **Swap cut / join** reverses those operations. The selected cylinder supplies diameter, axis, and available length. Reverse axis changes which end starts the interval. Only the selected body participates in the native Combine. Apply can promote Part design intent to Hybrid on OK and retains its selected target through this transition. No contour masks or Thicken features are created. Knobs and entry taper are disabled for Apply. Repeated occurrences share the native body, so applying to one updates all occurrences of that component.

Create, Apply, and Fit Test can insert features at the current timeline marker, including in the middle of the history. Apply uses the selected cylinder as it exists at that point; later features recompute through Fusion. Opening or cancelling the dialog does not move the marker.

**Edit Printable Thread** loads the recipe from one selected owned body. It generates and validates the replacement before updating its base feature. This command is deliberately limited to the latest creation operation, with no additional component features or assembly joints. This command preserves editing of legacy owned bodies. New circular threads are edited through **Modify → Change Parameters**, using their `PT1_…`, `PT2_…` parameter sets, or through the individual native features inside their timeline group. Applied circular threads use these same native controls. Moving the timeline marker back is not an edit workaround.

**Printable Thread Fit Test** makes a short screw and four female coupons with physical dot marks on the top rim. Their clearances follow the main tolerance input; at the default 0.2 mm they are:

| Dots | Radial clearance per side | Diameter increase |
|---|---:|---:|
| 1 | 0.10 mm | 0.20 mm |
| 2 | 0.20 mm | 0.40 mm |
| 3 | 0.30 mm | 0.60 mm |
| 4 | 0.45 mm | 0.90 mm |

Axial clearance is independently applied to each flank. This regenerates a wider/larger cutter with unchanged lead; it is not a uniform scale or a surface-normal offset. Coupon component names include their clearance. Coupon sets are not individually editable through Edit.

**Live Preview** is available and enabled in every tool. It uses display-only Custom Graphics meshes, so changes to diameter, pitch, thread size, length, handedness, starts, output, and fit appear immediately without creating timeline features. The preview is deliberately approximate and translucent; **OK** creates the exact native Coil construction for circular Create/Apply, or the original guided-sweep solid for legacy commands. Turn Live Preview off for exceptionally large assemblies. Cancel or closing the dialog removes the preview.

Each tool remembers its last valid settings, including changes made before Cancel, across reopening and Fusion restarts. Updates and reinstalls preserve them. Saved dimensions are numeric values; references to document-specific user parameters are not carried into other documents. Edit loads the selected body’s saved recipe.

Settings are stored in `~/Library/Application Support/PrintableThreads/settings.json` on macOS and `%APPDATA%\PrintableThreads\settings.json` on Windows.

## Printing and dimensions

Pitch means adjacent-ridge spacing. Lead = starts × pitch. For example, three starts at 2 mm pitch gives 6 mm/revolution. A 12 mm working interval contains two revolutions of each start.

Print with the thread axis vertical as an initial calibration choice. Rounded profiles do not guarantee support-free printing. Check underside slopes and the blind cap orientation in your slicer. Record material, nozzle, layer height and slicer compensation using [the calibration sheet](docs/PRINT-CALIBRATION.md). No physical fit result is claimed yet.

Circular Create and Apply generate native **Coil, Extrude, Offset Faces, Move, Mirror, Circular Pattern, Loft, and Combine** features, grouped as one operation. Edit `PT1_pitch`, `PT1_section`, `PT1_length`, `PT1_engagement`, `PT1_tolerance`, `PT1_starts`, or `PT1_phase` in **Modify → Change Parameters** to recompute the corresponding geometry. Each subsequent operation gets its own numbered parameter set. Knob thickness and blind floor use a parametric Move to keep their flat base on the print plane. Output, handedness, knob type, cap presence, and whether an entry taper exists are structural choices selected at creation; changing those choices requires a new operation or manual feature edits.

Fusion rejects zero-distance Offset Faces. A thread created with zero tolerance has no offset feature; recreate it to add a positive tolerance. Keep a positive offset when editing an existing tolerance feature.

Existing operations remain unchanged. Balanced/Custom, Fit Test, and legacy Edit retain static base geometry with stored recipes and regeneration; they are not fully associative native thread features.

## Release scope

This is a **0.5.2 engineering preview**, not a standardized fastener or commercial bottle-thread library. Implemented: circular On Center, rounded trapezoid (radius zero gives sharp trapezoid), axial/radial fit controls, end trimming, standalone entry easing, lobed/cylindrical knobs, independent engagement, caps, multistart, handedness, responsive Custom Graphics preview, basic owned regeneration and cylindrical application.

Deferred from the outline: triangle profile families, separate crest/root radius controls, native conversion of the advanced trapezoidal profiles, shoulder relief/runout, knob edge fillets, hex blanks, standalone face/center placement, manipulators, turns-driven UI, advanced external cut-groove mode, associative legacy regeneration, an add-in dialog for editing native thread groups and custom timeline features. Unsupported selections fail with an explanation. See [validation evidence and outstanding checks](docs/TEST-RESULTS.md).

## Development

Run `python3 -m unittest discover -s tests -v` for pure mathematical tests. Run `diagnostics/ThreadGeometryProbe` through Fusion's Scripts dialog for geometry and integration tests. It opens a new document, writes `docs/probe-result.json`, and on success exports an F3D and PNG. It never uses the current user document for test geometry.

The legacy backend uses two exact `TemporaryBRepManager.createHelixWire` rails and a native guided sweep, then kernel boolean clipping and joining. It constructs tangent sketch arcs before sweeping; it does not fillet long helical edges or use a faceted mesh approximation. API details and observed failures are in [API notes](docs/API-NOTES.md).

## Native validation

The installed 0.5.2 Create and Apply dialogs were exercised in Fusion, including regular external/internal cylinders and timeline insertion before a later feature. Circular clearance checks use actual solid containment on both straight and curved mating faces. Native parameter recomputation, option combinations, and rotated component placement are checked through the user-enabled [local Fusion MCP](http://127.0.0.1:27182/mcp). See [native circular results](docs/native-circular-regression-probe.json) and [installed command evidence](docs/installed-create-False-False-probe.json).

A minimal original F3D template supplies the native editable Coil because [Fusion’s CoilFeatures API](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_CoilFeatures.htm) has no creation method. [Archive import](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/core_ImportManager_importToTarget2.htm) cannot run inside command events, so OK captures inputs and queues construction on the main thread after the dialog closes. Imported placements are captured in native timeline snapshots before Coil recomputation.

0.5.1 adds native circular thread-land chamfers, main-input Starts, and +Y placement from ZX. See [print-finish validation](docs/PRINT-FINISH-0.5.1.md).

0.5.2 consolidates the lobed knob into one sketch and one joining extrusion, simplifies nut blanks and the entry taper, and removes redundant cutting-tool trims. The default native pair falls from 73 to 34 timeline entries; 12-lobe pairs fall from 97 to 34. See [optimization evidence](docs/OPTIMIZATION-0.5.2.md).
