param([Parameter(Mandatory=$true)][string]$File)
$ErrorActionPreference = 'Stop'
foreach ($name in @('SIGNTOOL_PATH', 'AZURE_SIGNING_DLIB', 'AZURE_SIGNING_METADATA')) {
    if (-not [Environment]::GetEnvironmentVariable($name)) { throw "Missing signing configuration: $name" }
}
& $env:SIGNTOOL_PATH sign /fd SHA256 /tr 'http://timestamp.acs.microsoft.com' /td SHA256 /dlib $env:AZURE_SIGNING_DLIB /dmdf $env:AZURE_SIGNING_METADATA $File
if ($LASTEXITCODE -ne 0) { throw 'Azure signing failed. Release stopped.' }
& $env:SIGNTOOL_PATH verify /pa /all /v $File
if ($LASTEXITCODE -ne 0) { throw 'Signature verification failed. Release stopped.' }
$signature = Get-AuthenticodeSignature $File
if ($signature.Status -ne 'Valid' -or -not $signature.TimeStamperCertificate) {
    throw 'A trusted, timestamped signature is required. Release stopped.'
}
