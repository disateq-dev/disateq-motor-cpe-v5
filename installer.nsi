; ============================================================
; Motor CPE DisateQ™ v4.0 - Instalador NSIS
; ============================================================

!define PRODUCT_NAME "Motor CPE DisateQ"
!define PRODUCT_VERSION "4.0.0"
!define PRODUCT_PUBLISHER "DisateQ™"
!define PRODUCT_WEB_SITE "https://disateq.com"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\MotorCPE.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

; Configuración
SetCompressor lzma
RequestExecutionLevel admin

; Includes
!include "MUI2.nsh"
!include "FileFunc.nsh"

; Configuración MUI
!define MUI_ABORTWARNING
; !define MUI_ICON "assets\icon.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Páginas
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\bin\MotorCPE.exe"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\docs\README.txt"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Idiomas
!insertmacro MUI_LANGUAGE "Spanish"

; Información del instalador
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "MotorCPE_Installer_v${PRODUCT_VERSION}.exe"
InstallDir "D:\FFEESUNAT\Motor CPE DisateQ"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show

; ============================================================
; SECCIÓN PRINCIPAL
; ============================================================
Section "Motor CPE" SEC01
  SetOutPath "$INSTDIR\bin"
  SetOverwrite ifnewer
  
  ; Ejecutable principal
  File "dist\MotorCPE.exe"
  
  ; Crear estructura de carpetas
  CreateDirectory "$INSTDIR\config"
  CreateDirectory "$INSTDIR\data"
  CreateDirectory "$INSTDIR\output\txt"
  CreateDirectory "$INSTDIR\output\json"
  CreateDirectory "$INSTDIR\output\cdr"
  CreateDirectory "$INSTDIR\logs"
  CreateDirectory "$INSTDIR\backup"
  CreateDirectory "$INSTDIR\licenses"
  CreateDirectory "$INSTDIR\docs"
  
  ; Archivos de configuración
  SetOutPath "$INSTDIR\config"
  File /nonfatal "config\*.yaml"
  
  ; Documentación
  SetOutPath "$INSTDIR\docs"
  File /nonfatal "docs\*.md"
  
  ; Licencias (carpeta vacía, usuario agregará su .lic)
  SetOutPath "$INSTDIR\licenses"
  
  ; Inicializar trial
  FileOpen $0 "$INSTDIR\licenses\trial_timestamp.dat" w
  ${GetTime} "" "L" $1 $2 $3 $4 $5 $6 $7
  FileWrite $0 '{"installed_at": "$1-$2-$3 $4:$5:$6", "expires_at": "", "documents_processed": 0}'
  FileClose $0
  
SectionEnd

; ============================================================
; ACCESOS DIRECTOS
; ============================================================
Section -AdditionalIcons
  SetOutPath "$INSTDIR\bin"
  
  ; Menú Inicio
  CreateDirectory "$SMPROGRAMS\DisateQ"
  CreateShortCut "$SMPROGRAMS\DisateQ\Motor CPE.lnk" "$INSTDIR\bin\MotorCPE.exe"
  CreateShortCut "$SMPROGRAMS\DisateQ\Desinstalar.lnk" "$INSTDIR\uninst.exe"
  
  ; Escritorio
  CreateShortCut "$DESKTOP\Motor CPE DisateQ.lnk" "$INSTDIR\bin\MotorCPE.exe"
SectionEnd

; ============================================================
; REGISTRO DE WINDOWS
; ============================================================
Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  
  ; Registro de aplicación
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\bin\MotorCPE.exe"
  
  ; Desinstalador en Panel de Control
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\bin\MotorCPE.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  
  ; Firewall (permitir MotorCPE.exe)
  ExecWait 'netsh advfirewall firewall add rule name="Motor CPE DisateQ" dir=in action=allow program="$INSTDIR\bin\MotorCPE.exe" enable=yes'
SectionEnd

; ============================================================
; FUNCIONES
; ============================================================
Function .onInit
  ; Verificar si ya está instalado
  ReadRegStr $R0 ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString"
  StrCmp $R0 "" done
  
  MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION \
    "Motor CPE ya está instalado. $\n$\nClick OK para desinstalar la versión anterior y continuar, o Cancelar para salir." \
    IDOK uninst
  Abort
  
uninst:
  ClearErrors
  ExecWait '$R0 _?=$INSTDIR'
  
done:
FunctionEnd

Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "Motor CPE fue desinstalado exitosamente."
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 \
    "¿Está seguro que desea desinstalar Motor CPE?" IDYES +2
  Abort
FunctionEnd

; ============================================================
; DESINSTALADOR
; ============================================================
Section Uninstall
  ; Eliminar archivos
  Delete "$INSTDIR\bin\MotorCPE.exe"
  Delete "$INSTDIR\uninst.exe"
  
  ; Eliminar accesos directos
  Delete "$SMPROGRAMS\DisateQ\Motor CPE.lnk"
  Delete "$SMPROGRAMS\DisateQ\Desinstalar.lnk"
  Delete "$DESKTOP\Motor CPE DisateQ.lnk"
  
  ; Eliminar carpetas (excepto data, config, licenses)
  RMDir /r "$INSTDIR\bin"
  RMDir /r "$INSTDIR\docs"
  RMDir /r "$INSTDIR\output"
  RMDir /r "$INSTDIR\logs"
  RMDir /r "$INSTDIR\backup"
  
  ; Preguntar si eliminar datos
  MessageBox MB_YESNO|MB_ICONQUESTION \
    "¿Desea eliminar también la configuración y datos del Motor CPE?" \
    IDYES delete_data IDNO skip_data
  
delete_data:
  RMDir /r "$INSTDIR\data"
  RMDir /r "$INSTDIR\config"
  RMDir /r "$INSTDIR\licenses"
  
skip_data:
  RMDir "$INSTDIR"
  RMDir "$SMPROGRAMS\DisateQ"
  
  ; Registro
  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
  
  ; Firewall
  ExecWait 'netsh advfirewall firewall delete rule name="Motor CPE DisateQ"'
  
  SetAutoClose true
SectionEnd
