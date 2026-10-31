; Vyoma Handless - Windows installer (Inno Setup 6)
; Built by scripts/build_release.py, which passes /DAppVersion and /DSourceDir.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\VyomaHandless"
#endif

#define AppName "Vyoma Handless"
#define AppExe "VyomaHandless.exe"
#define AppPublisher "Vyoma Group"
#define AppURL "https://handless.vyomagroup.online/"

[Setup]
AppId={{8C2F4E61-3B7A-4D9E-9A51-6F0B2C7D8E14}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL=https://github.com/vyomagroupofficial-lab/handless/issues
AppUpdatesURL={#AppURL}
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} Setup

; Per-user install: no administrator prompt. Users can still pick "all users" in the dialog.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UsePreviousAppDir=yes

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763

WizardStyle=modern
WizardSizePercent=110
WizardImageFile=wizard-large.bmp
WizardSmallImageFile=wizard-small.bmp
SetupIconFile=handless.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
InfoBeforeFile=before-install.txt

; Close a running copy before replacing its files
CloseApplications=yes
RestartApplications=no

Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes
OutputDir=..\dist
OutputBaseFilename=VyomaHandless-Setup-{#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nSpeak naturally and Handless opens apps, types for you and handles the busywork.%n%nIt takes about a minute, and no administrator rights are needed.
InfoBeforeLabel=Here is what Handless will ask Windows for, and why.
FinishedHeadingLabel=Handless is ready
FinishedLabel=When Handless opens, a short setup will check your microphone, connect your AI keys and show the shortcuts that matter.

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startup"; Description: "&Start Handless when I sign in to Windows"; GroupDescription: "Startup:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Comment: "Voice control for your PC"
Name: "{autoprograms}\{#AppName} Setup"; Filename: "{app}\{#AppExe}"; Parameters: "--setup"; Comment: "Run the Handless setup again"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; Same value the in-app setup toggles, so both stay in sync
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "VyomaHandless"; ValueData: """{app}\{#AppExe}"" --background"; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName} now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#AppExe}"; Flags: runhidden; RunOnceId: "StopHandless"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    RegDeleteValue(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Run', 'VyomaHandless');
end;
