;----------------------------------------------------------------------------------------------------------------------
; NSIS Demo Installer
;
; Companion project for a blog post touring NSIS features. Demonstrates:
;   - Modern UI 2 page flow, including an optional-components page
;   - A custom nsDialogs page that reads release notes from a plain-text file at build time
;   - Conditional installation of the VC++ Redistributable (skipped if already present)
;   - Previous-install detection and cleanup
;   - A full uninstaller with Add/Remove Programs registration
;
; https://github.com/treideme/nsis-demo
;----------------------------------------------------------------------------------------------------------------------

!define COMPANYNAME "Reidemeister Labs"
!define APPNAME "NSIS Demo"
!define SHORTNAME "nsisdemo"
!define ENTRYPOINT "${SHORTNAME}.exe"

!ifndef VERSION
  !define VERSION "0.0.0"
!endif
!ifndef SRC
  !define SRC "stage"
!endif
!ifndef RELNOTES
  !define RELNOTES "stage\ReleaseNotes.txt"
!endif
!ifndef OUT
  !define OUT "NsisDemoSetup.exe"
!endif

Unicode True
SetCompressor /FINAL lzma

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "nsDialogs.nsh"
!include "WinMessages.nsh"

;----------------------------------------------------------------------------------------------------------------------
; Distribution settings
Name "${APPNAME}"
BrandingText "${COMPANYNAME} Installer"
OutFile "${OUT}"
InstallDir "$PROGRAMFILES64\${COMPANYNAME}\${APPNAME}"
RequestExecutionLevel admin

VIAddVersionKey /LANG=0 "ProductName" "${APPNAME}"
VIAddVersionKey /LANG=0 "CompanyName" "${COMPANYNAME}"
VIAddVersionKey /LANG=0 "LegalCopyright" "(C) ${COMPANYNAME}"
VIAddVersionKey /LANG=0 "FileDescription" "${APPNAME} Setup"
VIAddVersionKey /LANG=0 "FileVersion" "${VERSION}.0"
VIAddVersionKey /LANG=0 "ProductVersion" "${VERSION}.0"
VIProductVersion "${VERSION}.0"

;----------------------------------------------------------------------------------------------------------------------
; Modern UI customizations - deliberately retro: a full-screen gradient background
; instead of the flat default, the way installers looked before Windows XP.
!define MUI_ABORTWARNING
!define MUI_HEADERIMAGE
BGGradient 0000FF 000000 FFFFFF

;--------------------------------
; Custom "Release Notes" page (nsDialogs)
;--------------------------------
Var ReleaseNotesText

Function ReleaseNotesPageCreate
  nsDialogs::Create 1018
  Pop $0

  ${NSD_CreateLabel} 0 0 100% 12u "What's new in ${APPNAME} ${VERSION}:"
  Pop $1

  nsDialogs::CreateControl EDIT "${DEFAULT_STYLES}|${ES_MULTILINE}|${ES_AUTOVSCROLL}|${ES_READONLY}|${WS_VSCROLL}" ${WS_EX_CLIENTEDGE} 0 15u 100% 190u ""
  Pop $ReleaseNotesText

  StrCpy $4 ""
  ClearErrors
  FileOpen $2 "${RELNOTES}" r
  IfErrors notes_missing

  notes_loop:
    FileRead $2 $3
    IfErrors notes_done
    StrCpy $4 "$4$3"
    Goto notes_loop
  notes_done:
    FileClose $2
    ${NSD_SetText} $ReleaseNotesText "$4"
    Goto notes_end
  notes_missing:
    ${NSD_SetText} $ReleaseNotesText "(No release notes found for this build.)"
  notes_end:

  nsDialogs::Show
FunctionEnd

;--------------------------------
; Pages
;--------------------------------
!insertmacro MUI_PAGE_WELCOME
Page custom ReleaseNotesPageCreate
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

;--------------------------------
; Sections
;--------------------------------
Section "NSIS Demo App (required)" SecApp
  SectionIn RO

  ; A well-behaved installer always installs to the same, deterministic path, so
  ; detecting a previous install is just a matter of checking whether it's there -
  ; no filesystem-wide search plugin needed for the common case.
  IfFileExists "$INSTDIR\${ENTRYPOINT}" 0 NoOldInstall
    DetailPrint "Previous installation found at $INSTDIR, removing..."
    ClearErrors
    RMDir /r "$INSTDIR"
    IfErrors 0 NoOldInstall
      DetailPrint "Could not fully remove the previous installation (in use?). Continuing anyway."
  NoOldInstall:

  SetOutPath "$INSTDIR"
  DetailPrint "Installing application files..."
  Sleep 800
  File "/oname=${ENTRYPOINT}" "${SRC}\${ENTRYPOINT}"
  File "/oname=ReleaseNotes.txt" "${RELNOTES}"
  DetailPrint "Finalizing installation..."
  Sleep 2500

  CreateDirectory "$SMPROGRAMS\${COMPANYNAME}"
  CreateShortCut "$SMPROGRAMS\${COMPANYNAME}\${APPNAME}.lnk" "$INSTDIR\${ENTRYPOINT}"
  CreateShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\${ENTRYPOINT}"

  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}" "DisplayName" "${APPNAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}" "Publisher" "${COMPANYNAME}"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}" "NoRepair" 1
SectionEnd

Section "Visual C++ Redistributable (x64)" SecVCRedist
  ReadRegDWORD $0 HKLM "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" "Installed"
  ${If} $0 == 1
    DetailPrint "VC++ Redistributable already installed, skipping."
  ${Else}
    DetailPrint "Installing VC++ Redistributable (this can take a minute)..."
    InitPluginsDir
    SetOutPath "$PLUGINSDIR"
    File "/oname=vc_redist.x64.exe" "${SRC}\vc_redist.x64.exe"
    ExecWait '"$PLUGINSDIR\vc_redist.x64.exe" /install /quiet /norestart' $0
    DetailPrint "VC++ Redistributable installer exit code: $0"
  ${EndIf}
SectionEnd

;--------------------------------
; Uninstaller
;--------------------------------
Section "Uninstall"
  Delete "$INSTDIR\${ENTRYPOINT}"
  Delete "$INSTDIR\ReleaseNotes.txt"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"

  Delete "$SMPROGRAMS\${COMPANYNAME}\${APPNAME}.lnk"
  RMDir "$SMPROGRAMS\${COMPANYNAME}"
  Delete "$DESKTOP\${APPNAME}.lnk"

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SHORTNAME}"
SectionEnd
