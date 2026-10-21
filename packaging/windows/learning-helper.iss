#define AppName "Learning Helper"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\..\dist\learning-helper"
#endif

[Setup]
AppId={{C7B4E3D0-2F6A-4B8E-9B7D-6A1C2E3F4A5B}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Learning Helper
DefaultDirName={autopf}\LearningHelper
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist\installer
OutputBaseFilename=LearningHelper-{#AppVersion}-Setup
SetupIconFile=..\icons\learning-helper.ico
UninstallDisplayIcon={app}\learning-helper.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "autostart"; Description: "Iniciar com o Windows (somente este usuário)"; GroupDescription: "Opções:"; Flags: checkedonce
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[InstallDelete]
; Remove o bundle antigo para não misturar arquivos de versões diferentes.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\learning-helper.exe"
Name: "{group}\Configurações do {#AppName}"; Filename: "{app}\learning-helper.exe"; Parameters: "--settings"
Name: "{group}\Estatísticas do {#AppName}"; Filename: "{app}\learning-helper.exe"; Parameters: "--stats"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\learning-helper.exe"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\learning-helper.exe"; Tasks: autostart

[Run]
Filename: "{app}\learning-helper.exe"; Description: "Iniciar o Learning Helper agora"; Flags: nowait postinstall skipifsilent
Filename: "{app}\learning-helper.exe"; Flags: nowait runasoriginaluser; Check: IsUpdateRestart

[UninstallRun]
Filename: "{app}\learning-helper.exe"; Parameters: "--quit"; Flags: runhidden waituntilterminated; RunOnceId: "QuitLearningHelper"
Filename: "{sys}\taskkill.exe"; Parameters: "/IM learning-helper.exe /T /F"; Flags: runhidden waituntilterminated; RunOnceId: "KillLearningHelper"

[Code]
function IsUpdateRestart: Boolean;
begin
  Result := ExpandConstant('{param:UPDATERESTART|0}') = '1';
end;

procedure StopRunningApp;
var
  ResultCode: Integer;
begin
  if not FileExists(ExpandConstant('{app}\learning-helper.exe')) then
    exit;
  Exec(
    ExpandConstant('{app}\learning-helper.exe'),
    '--quit', '', SW_HIDE, ewWaitUntilTerminated, ResultCode
  );
  Sleep(1500);
  Exec(
    ExpandConstant('{sys}\taskkill.exe'),
    '/IM learning-helper.exe /T /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode
  );
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  StopRunningApp;
  Result := '';
end;
