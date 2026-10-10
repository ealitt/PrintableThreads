# Install Printable Threads 0.5.2

Download from the [version 0.5.2 release](https://github.com/ealitt/PrintableThreads/releases/tag/v0.5.2).
The repository is currently private: sign into GitHub with an account that has access.

## macOS

1. Close Fusion.
2. Download **PrintableThreads-0.5.2-macOS-unsigned.pkg** and double-click it.
3. Follow the installer. It may ask for an administrator password. It installs for the
   account currently signed into the Mac, even when a different administrator authorizes it.
4. Reopen Fusion, open a design and choose **Solid → Create → Printable Threads**.

This preview package is **unsigned and not notarized**. macOS may block it. If you trust
this release, Apple's supported exception is **System Settings → Privacy & Security →
Open Anyway**, after attempting to open the package. Do not disable Gatekeeper globally.
See [Apple's instructions](https://support.apple.com/en-us/102445).
Corporate security policies can prevent exceptions; use an approved deployment method instead.

## Windows

1. Close Fusion.
2. Download **PrintableThreads-0.5.2-Windows-unsigned.exe** and double-click it.
3. Follow the installer. It installs for your account without administrator privileges.
4. Reopen Fusion and choose **Solid → Create → Printable Threads**.

This preview installer is **unsigned**. Windows may show an unknown-publisher or
SmartScreen warning, and Smart App Control or organizational policies may block it.
Only proceed if you trust the release; do not turn off system protections.

## If the menu does not appear

Press **Shift+S**, select the **Add-Ins** tab, choose **PrintableThreads**, click **Run**,
and check **Run on Startup**. The default startup setting is enabled for fresh installs;
Fusion may retain your prior preference after an upgrade. Check **0.5.2** at the top of
the tool dialog. Run activation once after manual installation if needed.

## ZIP fallback: no separate Python required

Download **PrintableThreads-0.5.2.zip** and extract it. Copy its inner **PrintableThreads**
folder to one of these locations, creating the directories if necessary:

- macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/`
- Windows: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\`

Restart Fusion and follow activation above. Alternatively, use **Shift+S → + → Script or
add-in from device** and select the extracted inner folder in a permanent location.
The optional `.command`, `.cmd` and `install.py` helpers require Python; native installers
and the copy-folder method do not.

These installers deliberately use the established **Autodesk Fusion 360** path,
which [Fusion still searches](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/WritingDebugging_UM.htm)
alongside its newer **Autodesk Fusion** path. If you previously installed a second
PrintableThreads copy in another location, stop and remove that duplicate first.

## Updating and uninstalling

Close Fusion, install the newer version, and reopen Fusion. Native installers move the
previous add-in into `API/PrintableThreads-backups/<timestamp>`. They preserve tool
settings outside the add-in folder. Backups are retained until you remove them manually.

Windows: use **Settings → Apps → Installed apps → Printable Threads for Autodesk Fusion → Uninstall**.
macOS: close Fusion and move `API/AddIns/PrintableThreads` to Trash. The package contains
only add-in files; it does not install a background service or external Python runtime.
Saved settings and backups remain on both platforms.

For manual ZIP upgrades, rename your old folder outside `AddIns` before copying the new one.
Do not merge folders: stale source files can remain from an older release.

## Distribution options

| Route | What is available / what remains |
|---|---|
| GitHub native installers | Included with this release: PKG, EXE, ZIP, checksums. No marketplace requirement. Private repository access is required until the owner changes visibility. |
| Signed direct downloads | Requires an Apple Developer ID Installer certificate and notarization for the PKG, plus Windows code-signing credentials. There are no usable signing identities on this development Mac. Signing is not a guarantee of immediate SmartScreen reputation. |
| Autodesk App Store | Optional publisher submission, listing assets, current-version compatibility checks, review and publisher agreement. Autodesk recommends its generated Windows/Mac installers. The publisher must submit and accept the agreement; this release is not store-approved. |

Autodesk also permits non-store add-ins in its `ApplicationPlugins` bundle loader,
provided they have a valid `.bundle` and `PackageContents.xml`. This release uses the
existing AddIns layout to preserve installed behavior and avoid duplicate registrations.
A marketplace submission should supply that bundle layout and complete Autodesk's
startup-performance review; current engineering validation is not store certification.

Sources: [Autodesk API loading paths](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/WritingDebugging_UM.htm),
[Fusion publisher requirements](https://aps.autodesk.com/marketplace/publisher-center/fusion-publisher-guidelines),
[Apple signing and notarization](https://developer.apple.com/developer-id/),
[Windows SmartScreen and signing](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation),
[Inno Setup per-user installation](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm).
