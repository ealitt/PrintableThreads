$ErrorActionPreference = 'Stop'
foreach ($name in @('AZURE_SIGNING_ENDPOINT', 'AZURE_SIGNING_ACCOUNT', 'AZURE_SIGNING_PROFILE')) {
    if (-not [Environment]::GetEnvironmentVariable($name)) { throw "Missing signing configuration: $name" }
}
$tools = Join-Path $env:RUNNER_TEMP 'signing-tools'
nuget install Microsoft.Windows.SDK.BuildTools -OutputDirectory $tools -NonInteractive
if ($LASTEXITCODE -ne 0) { throw 'Windows SDK signing tools download failed' }
nuget install Microsoft.ArtifactSigning.Client -OutputDirectory $tools -NonInteractive
if ($LASTEXITCODE -ne 0) { throw 'Azure signing client download failed' }
$signTool = (Get-ChildItem $tools -Recurse -Filter signtool.exe | Where-Object FullName -Match '\\x64\\' | Sort-Object FullName -Descending | Select-Object -First 1).FullName
$dlib = (Get-ChildItem $tools -Recurse -Filter Azure.CodeSigning.Dlib.dll | Where-Object FullName -Match '\\x64\\' | Select-Object -First 1).FullName
if (-not $signTool -or -not $dlib) { throw 'Matching x64 signing tools not found' }
$metadata = Join-Path $tools 'metadata.json'
@{
    Endpoint = $env:AZURE_SIGNING_ENDPOINT
    CodeSigningAccountName = $env:AZURE_SIGNING_ACCOUNT
    CertificateProfileName = $env:AZURE_SIGNING_PROFILE
    ExcludeCredentials = @('EnvironmentCredential', 'WorkloadIdentityCredential', 'ManagedIdentityCredential', 'SharedTokenCacheCredential', 'VisualStudioCredential', 'VisualStudioCodeCredential', 'AzurePowerShellCredential', 'AzureDeveloperCliCredential', 'InteractiveBrowserCredential')
} | ConvertTo-Json | Set-Content -Encoding utf8 $metadata
"SIGNTOOL_PATH=$signTool" | Out-File -Append -Encoding utf8 $env:GITHUB_ENV
"AZURE_SIGNING_DLIB=$dlib" | Out-File -Append -Encoding utf8 $env:GITHUB_ENV
"AZURE_SIGNING_METADATA=$metadata" | Out-File -Append -Encoding utf8 $env:GITHUB_ENV
