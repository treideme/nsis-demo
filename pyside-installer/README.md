# Hello NSIS : PySide6 application behind an NSIS installer

Please see [my blog](https://reidemeister.com/blog/2026.02.07) for details.

The installer at the repository root wraps `notepad.exe`. That keeps it honest
about what NSIS itself does, and it sidesteps the question anyone shipping
software hits first: what if the payload is a Python GUI application?

This directory answers that. The application is a window with four labels, on
purpose, and an application with real
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

`build.py` builds the installer, assuming `makensis` is present.

## Reducing Software Bloat (like the 90s)

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

### Windows-specific optimization

**Qt ships its own IDE tooling: 14 executables, 12.2 MB.**
None belongs in a distributed
application.

**`opengl32sw.dll` is 19.7 MB, larger than `Qt6Core.dll`** and the largest file
in the wheel. It is the Mesa llvmpipe software OpenGL fallback, used when a
machine has no usable GPU driver.

That made it both the biggest saving available and the only exclusion here that
can fail on somebody else's machine rather than on the build machine. A widgets
application does not render through OpenGL, right up until it lands on a VM, an
RDP session, or a fresh install carrying only the Microsoft Basic Display
driver.

`DROP_SOFTWARE_OPENGL` is **True**, and the CI screenshot is what settled it: a
GitHub Windows runner has no GPU, so it is exactly the machine the fallback
exists for, and the window still rendered without it. A QtWidgets application
really does go through the raster paint engine. NOTE: that is a result about
widgets, not a general permission -- add a `QOpenGLWidget` or any of QtQuick and
the fallback goes back in.

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
