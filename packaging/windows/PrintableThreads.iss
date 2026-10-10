#ifndef Version
  #define Version "0.5.2"
#endif
[Setup]
AppId={{2FE5661D-F8ED-4BC2-88EE-5B9825D5B8FB}
AppName=Printable Threads for Autodesk Fusion
AppVersion={#Version}
AppPublisher=PrintableThreads
AppPublisherURL=https://github.com/ealitt/PrintableThreads
DefaultDirName={userappdata}\Autodesk\Autodesk Fusion 360\API\AddIns\PrintableThreads
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
UsePreviousAppDir=no
OutputDir=..\..\dist
#ifdef SignedBuild
OutputBaseFilename=PrintableThreads-{#Version}-Windows
SignTool=azure
SignedUninstaller=yes
SignedUninstallerDir=..\..\dist\signed-uninstaller
InfoBeforeFile=..\INSTALL-SIGNED.txt
#else
OutputBaseFilename=PrintableThreads-{#Version}-Windows-unsigned
InfoBeforeFile=..\INSTALL.txt
#endif
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
InfoAfterFile=..\ACTIVATE.txt
UninstallDisplayName=Printable Threads for Autodesk Fusion
CloseApplications=no
RestartApplications=no
[Files]
Source: "..\..\PrintableThreads\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__,*.pyc,.DS_Store"
[Code]
var
  BackupPath: String;
  Completed: Boolean;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Target, BackupRoot: String;
begin
  Result := '';
  { Back up before Inno opens its uninstall log in the target directory. }
  if BackupPath = '' then begin
    Target := ExpandConstant('{app}');
    if DirExists(Target) then begin
      BackupRoot := ExtractFileDir(ExtractFileDir(Target)) + '\PrintableThreads-backups';
      if not ForceDirectories(BackupRoot) then
        begin Result := 'Could not create backup folder. Installation stopped.'; Exit; end;
      BackupPath := BackupRoot + '\' + GetDateTimeString('yyyymmdd-hhnnss-zzz', '-', ':');
      if DirExists(BackupPath) then
        begin Result := 'Backup already exists. Please try again in a moment.'; BackupPath := ''; Exit; end;
      if not RenameFile(Target, BackupPath) then
        begin Result := 'Could not back up the installed version. Close Fusion and try again.'; BackupPath := ''; Exit; end;
      Log('Previous installation saved in ' + BackupPath);
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then Completed := True;
end;

procedure DeinitializeSetup();
begin
  if (not Completed) and (BackupPath <> '') and DirExists(BackupPath) then begin
    if (not DirExists(ExpandConstant('{app}'))) or DelTree(ExpandConstant('{app}'), True, True, True) then
      if not RenameFile(BackupPath, ExpandConstant('{app}')) then
        MsgBox('Installation failed. Restore the backup from: ' + BackupPath, mbError, MB_OK);
  end;
end;
