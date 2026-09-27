;----------------------------------------------------------------------------------------------------------------------
; Hello NSIS -- the second installer in this repository.
;
; The one at the repository root wraps notepad.exe, which keeps it honest about
; what NSIS itself does. This one wraps a real PySide6 application, because the
; interesting decisions are not inside NSIS at all -- they sit on the seam
; between NSIS and whatever produced the directory tree it is shipping.
;
; Demonstrates, beyond what the root installer covers:
;   - Shipping a PyInstaller one-dir bundle, Qt libraries and all
;   - A second MUI_PAGE_LICENSE carrying the generated third-party manifest
;   - A version resource that is generated, not typed (see the note below)
;   - Chain-installing the VC++ Redistributable, and the coupling that creates
;
; https://github.com/treideme/nsis-demo
; (C) 2026 Thomas Reidemeister
;----------------------------------------------------------------------------------------------------------------------

!define COMPANYNAME "Reidemeister Labs"
!define APPNAME "Hello NSIS"
!define SHORTNAME "hellonsis"
!define ENTRYPOINT "HelloNsis.exe"

; VERSION is passed in by build.py, which reads it from app/version.py. The
; fallback exists so a bare `makensis installer.nsi` still compiles for a syntax
; check, and 0.0.0 is chosen to be obviously wrong rather than plausibly stale.
!ifndef VERSION
  !define VERSION "0.0.0"
!endif
!ifndef SRC
  !define SRC "..\dist\HelloNsis"
!endif
!ifndef LICENSE_APP
  !define LICENSE_APP "..\..\LICENSE"
!endif
!ifndef LICENSE_THIRDPARTY
  !define LICENSE_THIRDPARTY "..\dist\THIRD-PARTY-LICENSES.txt"
!endif
!ifndef OUT
  !define OUT "HelloNsisSetup.exe"
!endif

Unicode True
SetCompressor /SOLID lzma

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"

Name "${APPNAME} ${VERSION}"
BrandingText "${COMPANYNAME}"
OutFile "${OUT}"
InstallDir "$PROGRAMFILES64\${COMPANYNAME}\${APPNAME}"
InstallDirRegKey HKLM "Software\${COMPANYNAME}\${APPNAME}" "InstallDir"
RequestExecutionLevel admin

;----------------------------------------------------------------------------------------------------------------------
; Version resource number TWO.
;
; There are two version resources for one version number, and nothing
; connects them. This one goes on the installer executable. The other goes on
; the application executable and is written by PyInstaller from the file that
; packaging/version.j2 renders. Both are generated from app/version.py by
; build.py, which is the only reason they agree.
;
; Type either of them by hand and you can ship an installer that says 1.2.0
; wrapped around an application that says 1.1.0. Neither NSIS nor PyInstaller
; will say a word: each is correct about its own file.
VIProductVersion "${VERSION}.0"
VIAddVersionKey /LANG=0 "ProductName" "${APPNAME}"
VIAddVersionKey /LANG=0 "CompanyName" "${COMPANYNAME}"
VIAddVersionKey /LANG=0 "LegalCopyright" "(C) ${COMPANYNAME}"
VIAddVersionKey /LANG=0 "FileDescription" "${APPNAME} Setup"
VIAddVersionKey /LANG=0 "FileVersion" "${VERSION}.0"
VIAddVersionKey /LANG=0 "ProductVersion" "${VERSION}.0"

;----------------------------------------------------------------------------------------------------------------------
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"
!define MUI_FINISHPAGE_RUN "$INSTDIR\${ENTRYPOINT}"
!define MUI_FINISHPAGE_RUN_TEXT "Start ${APPNAME}"

!insertmacro MUI_PAGE_WELCOME

; Two licence pages, and the second one is the point.
;
; The first is the licence the application is offered under -- the thing a user
; is being asked to accept. The second is a list of what is being redistributed
; *inside* the bundle, which the user is not agreeing to so much as being
; informed of. MUI2 has no "notice" page, so a licence page with its button text
; rewritten is the closest honest fit.
;
; The manifest is GENERATED at build time by packaging/licenses.py from the
; metadata of the environment that produced the build. A hand-maintained list is
; wrong the first time a transitive dependency changes, and wrong quietly.
!insertmacro MUI_PAGE_LICENSE "${LICENSE_APP}"

!define MUI_PAGE_HEADER_TEXT "Third-party components"
!define MUI_PAGE_HEADER_SUBTEXT "What this application redistributes"
!define MUI_LICENSEPAGE_TEXT_TOP "The following components ship inside ${APPNAME}."
!define MUI_LICENSEPAGE_TEXT_BOTTOM "Qt is used under the LGPL. Its libraries are installed as separate, replaceable files."
!define MUI_LICENSEPAGE_BUTTON "Next"
!insertmacro MUI_PAGE_LICENSE "${LICENSE_THIRDPARTY}"

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

;----------------------------------------------------------------------------------------------------------------------
Function .onInit
  ; The bundle is 64-bit because the Python that built it was. Saying so here
  ; beats the alternative, which is an application that installs cleanly and
  ; then refuses to start.
  ${IfNot} ${RunningX64}
    MessageBox MB_OK|MB_ICONSTOP "${APPNAME} requires 64-bit Windows."
    Abort
  ${EndIf}
  SetRegView 64

  ReadRegStr $0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString"
  ${If} $0 != ""
    MessageBox MB_YESNO|MB_ICONQUESTION \
      "${APPNAME} is already installed. Uninstall the previous version first?" \
      IDYES uninst
    Abort
    uninst:
      ExecWait '$0 /S _?=$INSTDIR'
  ${EndIf}
FunctionEnd

;----------------------------------------------------------------------------------------------------------------------
Section "${APPNAME}" SecMain
  SectionIn RO
  SetOutPath "$INSTDIR"

  ; The whole PyInstaller one-dir tree, _internal and all. /r because the Qt
  ; plugins live in subdirectories, and a non-recursive copy produces an
  ; application that starts and then dies on the platform plugin.
  File /r "${SRC}\*.*"

  ; Keep the manifest on disk as well as showing it during install. A user who
  ; wants to know what they are running six months later is not going to re-run
  ; the installer to find out.
  File "/oname=THIRD-PARTY-LICENSES.txt" "${LICENSE_THIRDPARTY}"

  WriteRegStr HKLM "Software\${COMPANYNAME}\${APPNAME}" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "Software\${COMPANYNAME}\${APPNAME}" "Version" "${VERSION}"

  CreateDirectory "$SMPROGRAMS\${COMPANYNAME}"
  CreateShortCut "$SMPROGRAMS\${COMPANYNAME}\${APPNAME}.lnk" "$INSTDIR\${ENTRYPOINT}"

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  !define ARP "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
  WriteRegStr   HKLM "${ARP}" "DisplayName"     "${APPNAME}"
  WriteRegStr   HKLM "${ARP}" "DisplayVersion"  "${VERSION}"
  WriteRegStr   HKLM "${ARP}" "Publisher"       "${COMPANYNAME}"
  WriteRegStr   HKLM "${ARP}" "DisplayIcon"     "$INSTDIR\${ENTRYPOINT}"
  WriteRegStr   HKLM "${ARP}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr   HKLM "${ARP}" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKLM "${ARP}" "NoModify" 1
  WriteRegDWORD HKLM "${ARP}" "NoRepair" 1
SectionEnd

;----------------------------------------------------------------------------------------------------------------------
Section "Visual C++ Runtime" SecVCRedist
  ; THIS SECTION IS COUPLED TO packaging/hello.spec, AND NOTHING ENFORCES IT.
  ;
  ; CPython on Windows is built against the Universal CRT, so the bundle needs
  ; VCRUNTIME140.dll and friends. There are exactly two ways to satisfy that,
  ; and the choice has to be made once and honoured in both files:
  ;
  ;   (a) let PyInstaller collect the CRT DLLs into the bundle -- app-local
  ;       deployment, permitted by the redistributable's own licence -- and
  ;       delete this section; or
  ;   (b) exclude them from the bundle and chain-install the redistributable,
  ;       which is what this does.
  ;
  ; hello.spec currently takes (a) and does NOT exclude the CRT, so this section
  ; is belt-and-braces rather than load-bearing. It stays because a redistributable
  ; that is already present costs one registry read, and because the day someone
  ; adds those DLLs to the spec's exclusion list, the application has to keep
  ; starting.
  ;
!ifdef VCREDIST
  SetRegView 64
  ReadRegDWORD $0 HKLM "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" "Installed"
  ${If} $0 == 1
    DetailPrint "Visual C++ Runtime already present -- skipping."
  ${Else}
    DetailPrint "Installing the Visual C++ Runtime..."
    SetOutPath "$PLUGINSDIR"
    File "${VCREDIST}"
    ExecWait '"$PLUGINSDIR\vc_redist.x64.exe" /install /quiet /norestart' $1
    DetailPrint "Visual C++ Runtime installer returned $1"
  ${EndIf}
!else
  DetailPrint "Built without a staged vc_redist.x64.exe -- nothing to chain-install."
!endif
SectionEnd

;----------------------------------------------------------------------------------------------------------------------
Section "Uninstall"
  SetRegView 64

  Delete "$SMPROGRAMS\${COMPANYNAME}\${APPNAME}.lnk"
  RMDir  "$SMPROGRAMS\${COMPANYNAME}"

  ; /REBOOTOK queues anything still locked for deletion on the next reboot. A Qt
  ; DLL that the application is still holding open is the ordinary case here, not
  ; an exotic one, so the flag earns its place.
  RMDir /r /REBOOTOK "$INSTDIR"

  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
  DeleteRegKey HKLM "Software\${COMPANYNAME}\${APPNAME}"
  DeleteRegKey /ifempty HKLM "Software\${COMPANYNAME}"
SectionEnd
