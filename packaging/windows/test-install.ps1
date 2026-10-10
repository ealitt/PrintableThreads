$ErrorActionPreference = 'Stop'
$version = (Get-Content -Raw 'PrintableThreads/PrintableThreads.manifest' | ConvertFrom-Json -AsHashtable).version
$signedInstaller = "dist/PrintableThreads-$version-Windows.exe"
$signedBuild = Test-Path $signedInstaller
$installer = if ($signedBuild) { (Resolve-Path $signedInstaller).Path } else { (Resolve-Path "dist/PrintableThreads-$version-Windows-unsigned.exe").Path }
if ($signedBuild -and (Get-AuthenticodeSignature $installer).Status -ne 'Valid') { throw 'Installer signature is not trusted' }
$root = Join-Path $env:RUNNER_TEMP 'Printable Threads installer test'
$target = Join-Path $root 'API/AddIns/PrintableThreads'
New-Item -ItemType Directory -Force $root | Out-Null
function Install-Preview {
    $process = Start-Process -FilePath $installer -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR=`"$target`" /LOG=`"$root/install.log`"" -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        Get-Content (Join-Path $root 'install.log') -Tail 60
        throw "Installer failed: $($process.ExitCode)"
    }
}
Install-Preview
foreach ($source in Get-ChildItem PrintableThreads -File -Recurse) {
    if ($source.FullName -match '__pycache__|\.pyc$|\.DS_Store$') { continue }
    $relative = [IO.Path]::GetRelativePath((Resolve-Path PrintableThreads), $source.FullName)
    $installed = Join-Path $target $relative
    if ((Get-FileHash $source.FullName).Hash -ne (Get-FileHash $installed).Hash) { throw "Payload mismatch: $relative" }
}
Set-Content (Join-Path $target 'old-version.txt') 'keep backup'
Install-Preview
$backupRoot = Join-Path $root 'API/PrintableThreads-backups'
if (-not (Get-ChildItem $backupRoot -Recurse -Filter old-version.txt)) { throw 'Old install was not preserved' }
$uninstaller = Join-Path $target 'unins000.exe'
if ($signedBuild -and (Get-AuthenticodeSignature $uninstaller).Status -ne 'Valid') { throw 'Embedded uninstaller signature is not trusted' }
$process = Start-Process $uninstaller -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' -Wait -PassThru
if ($process.ExitCode -ne 0) { throw 'Uninstaller failed' }
if (Test-Path (Join-Path $target 'PrintableThreads.manifest')) { throw 'Add-in remains after uninstall' }
if (-not (Test-Path $backupRoot)) { throw 'Uninstall removed backups' }
Write-Output 'Fresh install, upgrade, payload hashes, backup and uninstall verified.'
