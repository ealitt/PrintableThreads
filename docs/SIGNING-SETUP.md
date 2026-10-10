# One-time setup for trusted installer signing

Signing cannot begin until the publisher has signing identities. This development Mac
has no valid signing identity, and this repository has no signing secrets or variables.
Existing 0.5.2 release assets remain **unsigned**. No paid accounts have been created.

## macOS: Apple Developer ID and notarization

1. Enroll in the [Apple Developer Program](https://developer.apple.com/programs/).
   Complete Apple's account/identity checks and agreements yourself.
2. Create a **Developer ID Installer** certificate. Export that certificate **with its
   private key** as a password-protected `.p12` from Keychain Access. An application
   certificate or a self-signed certificate cannot replace the Installer certificate.
3. Create an App Store Connect team API key eligible for notarization. Keep its `.p8`
   private key, key ID and issuer ID. See [Apple's notarization instructions](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).
4. In GitHub **PrintableThreads → Settings → Environments**, create **signing**.
   Add these **environment secrets** using GitHub's interface or `gh secret set` from
   local files. Do not paste private keys or passwords into chat or commit them:

| Secret | Value |
|---|---|
| `APPLE_INSTALLER_P12_BASE64` | Base64 of the exported certificate/private-key `.p12`, without line breaks |
| `APPLE_INSTALLER_P12_PASSWORD` | Password protecting that `.p12` |
| `APPLE_INSTALLER_IDENTITY` | Exact Keychain identity, `Developer ID Installer: Your Name (TEAMID)` |
| `APPLE_NOTARY_KEY_BASE64` | Base64 of the `.p8` team API private key, without line breaks |
| `APPLE_NOTARY_KEY_ID` | API key ID |
| `APPLE_NOTARY_ISSUER_ID` | Team API issuer ID |

The automation imports the certificate into an isolated temporary keychain, signs the
PKG, waits for Apple's acceptance, staples the notarization ticket and checks the
publisher signature and Gatekeeper assessment. It removes the temporary keychain and
key files afterward. A rejected/unfinished notarization cannot publish signed downloads.

## Windows: Azure Artifact Signing

The automated route uses Azure's managed signing identity, so a Windows private key
does not need to be exported to GitHub. It requires an Azure subscription and a
**Public Trust** signing profile with completed publisher identity validation.
See [Microsoft's setup requirements](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart).

1. Create the Artifact Signing account, validate your publisher identity and create
   a **Public Trust** certificate profile. Availability depends on Microsoft's current
   eligibility rules. You must complete enrollment/identity validation and authorize costs.
2. Create an Entra application/service principal for GitHub OIDC. Add a federated
   credential with issuer `https://token.actions.githubusercontent.com`, audience
   `api://AzureADTokenExchange`, and subject
   `repo:ealitt/PrintableThreads:environment:signing`.
3. Give that identity **Artifact Signing Certificate Profile Signer** at the certificate
   profile scope. Do not grant subscription-wide signing administration.
4. Add these **environment variables** in the GitHub **signing** environment:

| Variable | Value |
|---|---|
| `AZURE_CLIENT_ID` | Entra application/client ID |
| `AZURE_TENANT_ID` | Tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Subscription ID |
| `AZURE_SIGNING_ENDPOINT` | Signing service endpoint for the account's region |
| `AZURE_SIGNING_ACCOUNT` | Artifact Signing account name |
| `AZURE_SIGNING_PROFILE` | Public Trust certificate profile name |

GitHub uses short-lived OIDC authentication to Azure. Inno Setup calls the signing
helper for **both the installer and embedded uninstaller**. SHA-256 timestamps and
trusted signatures are required. The installed uninstaller is verified again during
the install/upgrade/uninstall check. See [Microsoft signing integration details](https://learn.microsoft.com/en-us/azure/artifact-signing/how-to-signing-integrations)
and [Inno Setup's signed uninstaller](https://jrsoftware.org/ishelp/topic_setup_signeduninstaller.htm).

If you already use an HSM-backed certificate or another signing service, the Windows
signer needs adaptation to that provider. This workflow currently supports Azure.

## Run the automated signing release

After configuring **both platforms**:

1. In GitHub **Actions**, select **Sign and notarize an existing release**.
2. Click **Run workflow**, choose `main`, and enter **v0.5.2**.
3. Wait for both platform jobs and the publish job to succeed.
4. The existing release gains **PrintableThreads-0.5.2-macOS.pkg**,
   **PrintableThreads-0.5.2-Windows.exe**, and **SHA256SUMS-SIGNED.txt**.
   The release description identifies them as the preferred signed downloads.

The workflow checks that the current add-in files exactly match the requested version
tag. Packaging/signing helpers can be updated independently without changing thread
geometry. Both platforms must pass before any signed assets are published. Existing
unsigned files remain available and keep their original labels and hashes. The ZIP
is a source/manual-install fallback, not a signed installer.

Signing functionality is prepared but **not yet validated against real signing services**,
because credentials are not configured. Local checks cover credential rejection and
notarization failure handling; they cannot replace a real Apple/Azure signing run.

You may restrict the GitHub signing environment to `main` and add required reviewers
if your GitHub plan supports it. Future workflow runs would then require that configured
approval. Signing does not make a private repository public and does not guarantee
that a brand-new Windows download immediately has SmartScreen reputation.
