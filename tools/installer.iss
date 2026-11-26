; Inno Setup script for AgentTokenlike-Setup.exe. Built by tools/build_exe.py (needs Inno Setup 6, dev only):
;   ISCC /DAppVersion=1.0.2 /DRoot=<repo> tools\installer.iss
; Per-user install (no admin prompt) in %LOCALAPPDATA%\Programs\Agent Tokenlike. Running it again updates in place.
; Progress lives in %USERPROFILE%\.tokenlike and is never touched (not even by the uninstaller).

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6F3C2A1E-4B7D-4E21-9A55-7C0D2B8E5F41}
AppName=Agent Tokenlike
AppVersion={#AppVersion}
AppPublisher=TheVino
AppPublisherURL=https://github.com/TheVino/agent-tokenlike
DefaultDirName={autopf}\Agent Tokenlike
DefaultGroupName=Agent Tokenlike
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#Root}\dist
OutputBaseFilename=AgentTokenlike-Setup
SetupIconFile={#Root}\build\icon.ico
UninstallDisplayIcon={app}\AgentTokenlike.exe
LicenseFile={#Root}\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#Root}\dist\AgentTokenlike\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; old build files from a previous version (the extra heroes in characters\ stay)
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\Agent Tokenlike"; Filename: "{app}\AgentTokenlike.exe"
Name: "{group}\Agent Tokenlike (demo)"; Filename: "{app}\AgentTokenlike.exe"; Parameters: "--demo"
Name: "{autodesktop}\Agent Tokenlike"; Filename: "{app}\AgentTokenlike.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AgentTokenlike.exe"; Description: "{cm:LaunchProgram,Agent Tokenlike}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; the "Start with Windows" shortcut the app writes from its menu
Type: files; Name: "{userstartup}\Agent Tokenlike.cmd"
