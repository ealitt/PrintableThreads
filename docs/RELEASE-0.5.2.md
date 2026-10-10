Printable Threads 0.5.2 engineering preview for Autodesk Fusion.

## Downloads and installation

- **macOS:** download `PrintableThreads-0.5.2-macOS-unsigned.pkg` and double-click it.
- **Windows:** download `PrintableThreads-0.5.2-Windows-unsigned.exe` and double-click it.
- **Manual fallback:** download `PrintableThreads-0.5.2.zip` and copy the inner add-in folder.

Close Fusion before installing, then reopen it. Open **Solid → Create → Printable Threads**.
If missing, press **Shift+S → Add-Ins → PrintableThreads → Run**, and enable **Run on Startup**.
Native installers include the add-in and require no separate Python. Upgrades preserve
settings and back up the previous install. The Mac package requests administrator
authorization; Windows installs per user without elevation.

**Both native installers are unsigned; the Mac package is not notarized.** OS security
warnings or blocks are possible. See the [installation guide](https://github.com/ealitt/PrintableThreads/blob/v0.5.2/docs/INSTALLATION.md)
for activation, security prompts, uninstalling and marketplace/signing options.
`SHA256SUMS.txt` provides download integrity hashes, not publisher authentication.

## Changes

- Compresses the default native screw/nut pair from 73 to 34 timeline entries;
  12-lobe pairs fall from 97 to 34, with zero measured solid difference in regression cases.
- Native circular Create/Apply retain grouped, editable Fusion features, full nut mating
  clearance, print edge chamfers, starts, remembered settings and timeline insertion.
- Includes PKG/EXE installers, startup defaults, update backups and automated packaging checks.

This is a prerelease. Balanced/Custom profiles, Fit Test and legacy Edit retain their
existing construction and are not fully native associative features. Geometry validation
is documented in the repository; physical printed fit is not yet certified. Windows
packaging checks verify installation, not Windows Fusion modeling execution.
