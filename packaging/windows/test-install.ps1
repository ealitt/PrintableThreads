$ErrorActionPreference = 'Stop'
$version = (Get-Content -Raw 'PrintableThreads/PrintableThreads.manifest' | ConvertFrom-Json -AsHashtable).version
$installer = (Resolve-Path "dist/PrintableThreads-$version-Windows-unsigned.exe").Path
$root = Join-Path $env:RUNNER_TEMP 'Printable Threads installer test'
$target = Join-Path $root 'API/AddIns/PrintableThreads'
New-Item -ItemType Directory -Force $target | Out-Null
Set-Content (Join-Path $target 'old-version.txt') 'keep backup'
function Install-Preview {
    $process = Start-Process -FilePath $installer -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR=`"$target`" /LOG=`"$root/install.log`"" -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Installer failed: $($process.ExitCode)" }
}
Install-Preview
$backupRoot = Join-Path $root 'API/PrintableThreads-backups'
if (-not (Get-ChildItem $backupRoot -Recurse -Filter old-version.txt)) { throw 'Old install was not preserved' }
foreach ($source in Get-ChildItem PrintableThreads -File -Recurse) {
    if ($source.FullName -match '__pycache__|\.pyc$|\.DS_Store$') { continue }
    $relative = [IO.Path]::GetRelativePath((Resolve-Path PrintableThreads), $source.FullName)
    $installed = Join-Path $target $relative
    if ((Get-FileHash $source.FullName).Hash -ne (Get-FileHash $installed).Hash) { throw "Payload mismatch: $relative" }
}
Install-Preview
$uninstaller = Join-Path $target 'unins000.exe'
$process = Start-Process $uninstaller -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' -Wait -PassThru
if ($process.ExitCode -ne 0) { throw 'Uninstaller failed' }
if (Test-Path (Join-Path $target 'PrintableThreads.manifest')) { throw 'Add-in remains after uninstall' }
if (-not (Test-Path $backupRoot)) { throw 'Uninstall removed backups' }
Write-Output 'Fresh install, upgrade, payload hashes, backup and uninstall verified.'
