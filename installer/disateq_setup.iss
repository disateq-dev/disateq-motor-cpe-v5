; =============================================================================
; disateq_setup.iss -- DisateQ Motor CPE v5.0
; TASK-INS-01 -- DisateQ DEV FLOW v1
; Para cambiar cliente: usar build_installer.ps1 -Cliente nombre_cliente
; =============================================================================

#define MyAppName      "DisateQ Motor CPE"
#define MyAppVersion   "5.0"
#define MyAppPublisher "DisateQ DEV - Fernando Tejada"
#define MyAppURL       "https://github.com/disateq-dev/disateq-motor-cpe-v5"
#define MyAppExeName   "DisateQ-Motor-CPE.exe"
#define ClienteID      "farmacia_central"

[Setup]
AppId={{3A7F2C1E-9B4D-4E8A-BC12-5F6D7E8A9B0C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\DisateQ\Motor CPE
DefaultGroupName=DisateQ Motor CPE
OutputDir=Output
OutputBaseFilename=DisateQ-Motor-CPE-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
MinVersion=10.0

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Opciones adicionales:"

[Files]
; Ejecutable principal
Source: "..\dist\DisateQ-Motor-CPE\DisateQ-Motor-CPE.exe"; DestDir: "{app}"; Flags: ignoreversion
; Dependencias PyInstaller
Source: "..\dist\DisateQ-Motor-CPE\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
; Config del cliente (inyectado por build_installer.ps1)
Source: "..\dist\DisateQ-Motor-CPE\config\clientes\{#ClienteID}.yaml"; DestDir: "{app}\config\clientes"; Flags: ignoreversion
Source: "..\dist\DisateQ-Motor-CPE\config\contratos\{#ClienteID}.yaml"; DestDir: "{app}\config\contratos"; Flags: ignoreversion
; Llave publica RSA -- NUNCA incluir disateq_private.pem
Source: "..\src\licenses\keys\disateq_public.pem"; DestDir: "{app}\licenses"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: dirifempty; Name: "{app}\config\clientes"
Type: dirifempty; Name: "{app}\config\contratos"
Type: dirifempty; Name: "{app}\licenses"
Type: dirifempty; Name: "{app}\_internal"

[Code]
var
  DataDirPage: TInputDirWizardPage;

function CheckWebView2(): Boolean;
var
  Version: String;
begin
  Result := RegQueryStringValue(
    HKLM,
    'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}',
    'pv', Version
  );
  if not Result then
    Result := RegQueryStringValue(
      HKCU,
      'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}',
      'pv', Version
    );
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not CheckWebView2() then
    MsgBox(
      'AVISO: Microsoft WebView2 no detectado.' + #13#10 + #13#10 +
      'DisateQ Motor CPE requiere WebView2 para la interfaz grafica.' + #13#10 +
      'La instalacion continuara, pero debera instalar WebView2 antes' + #13#10 +
      'de ejecutar el motor.' + #13#10 + #13#10 +
      'Descarga gratuita:' + #13#10 +
      'https://developer.microsoft.com/microsoft-edge/webview2/',
      mbInformation, MB_OK
    );
end;

procedure InitializeWizard();
begin
  DataDirPage := CreateInputDirPage(
    wpSelectDir,
    'Directorio de datos operativos',
    'Seleccione la carpeta donde DisateQ almacenara logs, base de datos y comprobantes.',
    'IMPORTANTE: Se recomienda una unidad D: de gran capacidad.' + #13#10 +
    'DisateQ requiere unidad D: para backups y data operativa.' + #13#10 + #13#10 +
    'El directorio del programa (C:) solo contiene el ejecutable y configuracion.',
    False,
    ''
  );
  DataDirPage.Add('Carpeta de datos (recomendado en D:):');
  DataDirPage.Values[0] := 'D:\DisateQ\Data';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  DataDir: String;
  DataPath: String;
  OutputPath: String;
  AppDir: String;
  CfgPath: String;
  CfgContent: String;
begin
  Result := True;

  if CurPageID = DataDirPage.ID then
  begin
    DataDir := DataDirPage.Values[0];
    if Trim(DataDir) = '' then
    begin
      MsgBox('Debe seleccionar un directorio de datos.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;

  if CurPageID = wpReady then
  begin
    DataDir    := DataDirPage.Values[0];
    DataPath   := DataDir + '\data';
    OutputPath := DataDir + '\output';
    AppDir     := WizardDirValue();
    CfgPath    := AppDir + '\disateq_paths.cfg';

    if not DirExists(DataPath) then
      ForceDirectories(DataPath);
    if not DirExists(OutputPath) then
      ForceDirectories(OutputPath);

    CfgContent :=
      '; DisateQ Motor CPE -- rutas operativas' + #13#10 +
      '; Generado por el instalador -- no editar manualmente' + #13#10 +
      '[paths]' + #13#10 +
      'data_dir = '   + DataPath   + #13#10 +
      'output_dir = ' + OutputPath + #13#10;

    if not SaveStringToFile(CfgPath, CfgContent, False) then
    begin
      MsgBox(
        'No se pudo crear disateq_paths.cfg en:' + #13#10 + CfgPath + #13#10 + #13#10 +
        'Verifique permisos de escritura en el directorio de instalacion.',
        mbError, MB_OK
      );
      Result := False;
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    MsgBox(
      'DisateQ Motor CPE ha sido desinstalado.' + #13#10 + #13#10 +
      'Sus datos operativos (logs, base de datos, comprobantes generados)' + #13#10 +
      'en la carpeta D: NO han sido eliminados.' + #13#10 + #13#10 +
      'Puede eliminarlos manualmente si ya no los necesita.',
      mbInformation, MB_OK
    );
end;
