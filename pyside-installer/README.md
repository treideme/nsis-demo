# Hello NSIS — a PySide6 application behind an NSIS installer

The installer at the repository root wraps `notepad.exe`. That keeps it honest
about what NSIS itself does, and it sidesteps the question anyone shipping
software hits first: what if the payload is a Python GUI application?

This directory answers that. The application is a window with four labels, on
purpose — the subject here is the packaging, and an application with real
dependencies makes it impossible to tell which of PyInstaller's decisions were
forced by Qt and which by the code.

```
app/                the application: a window, and its version number
packaging/
  hello.spec        PyInstaller spec, with a measured exclusion list
  version.j2        Windows version resource template
  licenses.py       third-party licence manifest, read from the build env
  installer.nsi     the NSIS installer
build.py            version resource -> freeze -> manifest -> installer
```

## Building

```sh
python -m venv .venv && . .venv/bin/activate   # or .venv\Scripts\activate
pip install -r requirements.txt
python build.py                 # add --skip-installer if NSIS is not present
```

`build.py` skips the installer with an explanatory message when `makensis` is
absent, so the first three stages are usable on any platform. A *working*
Windows installer needs a Windows build of the application to wrap; the CI job
in `.github/workflows/ci.yml` does the real thing on a Windows runner.

## What the measurements showed

**NSIS is a Windows installer, so the numbers that matter are Windows numbers.**
PySide6-Essentials for `win_amd64` 6.11.2 unpacks to **201.6 MB across 2,471
files**. That is the raw material, before anything decides what a QtWidgets
application needs.

What `hello.spec`'s exclusion list targets, read from the wheel's own file table
on 2026-09-26:

```
Qt module libraries         48.2 MB     75 files
QML runtime and type data   23.1 MB   1785 files
translations                13.1 MB    196 files
developer executables       12.2 MB     14 files
unused Python bindings      11.9 MB      9 files
icudtl.dat                  10.0 MB      1 file
--------------------------------------------------
removed by default         118.4 MB    (59%)
plus the opt-in below      138.1 MB    (68%)
```

⚠️ **That is what the list removes from the WHEEL, which is not the bundle.**
PyInstaller does not collect every file a wheel contains, so the end-to-end
figure has to come from a Windows build. The CI job prints it and asserts the
exclusions held; there is no Windows machine in this project's development loop.

### Three things worth knowing, all Windows-specific

🔴 **Qt ships its own IDE tooling: 14 executables, 12.2 MB.** `designer.exe`,
`linguist.exe` and `assistant.exe` are development applications with their own
windows. `uic` and `rcc` are build-time compilers. None belongs in a distributed
application, and they are extra executable entry points in a user's install
directory. **They survived the first version of this list**, which matched
library stems like `Qt6Quick` while these are executables. A filter aimed at one
kind of file is silent about every other kind.

🔴 **`opengl32sw.dll` is 19.7 MB, larger than `Qt6Core.dll`** — the single
biggest file in the wheel. It is the Mesa llvmpipe software OpenGL fallback, used
when a machine has no usable GPU driver. ⚠️ **So it is the largest saving
available and the only exclusion here that can fail on somebody else's machine.**
A widgets app does not render through OpenGL until it lands on a VM, an RDP
session, or a fresh install with only the Microsoft Basic Display driver.
`DROP_SOFTWARE_OPENGL` therefore defaults to **False**.

⚠️ **Do not port a Linux size measurement across.** An earlier version of this
file did, and it was wrong in a way that looked authoritative:

```
             ICU entries    total
manylinux              3  37.3 MB
win_amd64              1  10.0 MB
```

On Linux `libicui18n`, `libicuuc` and `libicudata` are `DT_NEEDED` of
`libQt6Core.so.6`, so the loader resolves them before any of your code runs and
they cannot be pruned at all. On Windows they do not exist, because Qt uses the
native Win32 text and locale APIs. The one Windows entry is Chromium's ICU data
for QtWebEngine, and dropping that is free here.

**Linux figures, for completeness only:** 195 MB collected, 157 MB after pruning,
265 files down to 152. PySide6 6.11.2, PyInstaller 6.22.3, CPython 3.12.14.
Useful for checking the spec runs; not useful for sizing a Windows installer.

## Three things that are easy to get wrong

**Never prune the platform plugin.** `qwindows.dll` on Windows, `libqxcb.so` on
Linux. Cut it and the application dies before any of your code runs, with
"could not load the Qt platform plugin" and no mention of the file you removed.
It is called out by name in `hello.spec` rather than merely absent from the
list, because absence is not a decision anyone can see.

**A filter that matches nothing looks exactly like a clean build.** `hello.spec`
counts what it removed and fails the build at zero. A wrong stem, a renamed
directory or a Qt reorganisation then shows up as an assertion instead of as an
installer that is quietly three times the size it should be.

**There are two version resources and nothing connects them.** One goes on the
application executable via PyInstaller, one on the installer via NSIS. Both are
generated from `app/version.py`, which is the only reason they agree. Type
either by hand and you can ship an installer claiming 1.2.0 around an
application claiming 1.1.0, with both toolchains entirely satisfied.

## Why one directory rather than one file

`--onefile` is not used, and that is a licence decision rather than taste. Qt is
used here under the LGPL, which asks that the user be able to replace the
library. A single-file build unpacks to a temporary directory at every launch,
so there is no Qt DLL on disk for anyone to substitute. One directory also lets
the installer ship those libraries as ordinary files, which makes the obligation
visible instead of merely asserted.

`packaging/licenses.py` generates the manifest from the metadata of the
environment that produced the build, and the installer shows it on a second
licence page. A hand-maintained list is wrong the first time a transitive
dependency changes, and wrong quietly.

⚠️ **It reads three metadata fields, not one.** `License-Expression` (PEP 639),
the `License :: ` classifiers, and the old free-text `License`. Which one is
populated varies by how recently a wheel was built — here all five components
answered from `License`, carrying an SPDX expression. Reading only one field is
how a manifest reports `UNKNOWN` for most of the tree while appearing to work.
Run `python packaging/licenses.py --audit` to see which field answered for each
package; it exits non-zero if any has no licence metadata at all.
