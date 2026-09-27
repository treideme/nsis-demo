# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the hello-world PySide6 application.

MEASURED, NOT GUESSED. With no filtering at all, PyInstaller collects 195 MB
across 265 files for a window containing four text labels. (PySide6 6.11.2,
Linux, 2026-09-26. Windows differs in file names and somewhat in size; the
shape of the over-collection is the same, because it comes from PySide6's
hooks rather than from the platform.)

The biggest single line item is QML and Quick at about 16 MB, in an application
that is QtWidgets-only and does not contain the string "QML" anywhere. Qt's PDF
module is another 4 MB. Neither is a bug in PyInstaller: its Qt hooks
deliberately over-collect, because collecting too little fails at run time on a
user's machine with a cryptic plugin error, while collecting too much merely
ships a large installer. Given only one default to pick, that is the right one.

TWO THINGS THIS SPEC DOES DIFFERENTLY from the usual hand-maintained blacklist:

  1. It filters on STEMS, not filenames. `Qt6Quick` matches libQt6Quick.so.6 on
     Linux and Qt6Quick.dll on Windows, so one list serves both and a Qt version
     bump does not silently stop matching. A literal list of file names is wrong
     the first time the soversion changes, and it fails OPEN -- the file is
     simply kept, the bundle grows, and nothing says so.

  2. It asserts that it actually removed something. A filter that matches
     nothing looks exactly like a clean build. See the CHECK block at the end,
     which fails the build rather than quietly shipping 195 MB.
"""
__author__ = "Thomas Reidemeister"

import os
import sys

# --- what this application genuinely needs ----------------------------------
# QtWidgets pulls QtCore and QtGui. Nothing here wants QML, Quick, 3D, charts,
# multimedia, PDF, WebEngine, SQL, or a virtual keyboard.
EXCLUDE_MODULES = [
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQuickControls2",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtNetwork",
    "PySide6.QtMultimedia",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtSql",
    "PySide6.Qt3DCore",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtTest",
    "PySide6.QtDesigner",
    # 8.28 MB on Windows, the LARGEST .pyd in the wheel -- bigger than
    # QtWidgets.pyd. Safe to drop here: nothing in app/ imports it, and
    # Qt6Core/Gui/Widgets do not link Qt6OpenGL as a hard dependency (checked
    # with readelf on the Linux build, 2026-09-26). The DLL itself is left
    # alone; only the Python binding goes.
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    # Not Qt, but PyInstaller's analysis reaches them through setuptools and
    # they are large and never used at run time.
    "tkinter",
    "unittest",
    "pydoc_data",
    "lib2to3",
    # FROM THE WINDOWS TOC DUMP, not from a guess. libssl-3.dll is collected
    # because PyInstaller found Python's _ssl, in an application that opens no
    # sockets.
    "ssl",
    "_ssl",
    # AND HERE IS WHERE THAT STOPS. `hashlib` and `_hashlib` were on this
    # list for one run and the frozen application died on startup with
    # 0xC0000409, a fast-fail with no message and nothing in the log.
    #
    # The reason is one line in the standard library:
    #
    # random.py:  from hashlib import sha512 as _sha512
    #
    # So excluding hashlib breaks `import random`, and random is imported all
    # over the stdlib. **libcrypto-3.dll, at 5.1 MB, is therefore NOT
    # prunable**: _hashlib links it as well as _ssl, and _hashlib has to stay.
    # A hello-world GUI application ships 5 MB of OpenSSL because random wants
    # a SHA-512, and there is no exclusion that fixes it.
    # "hashlib", "_hashlib",   <- do not
]

# --- binaries and data to drop, matched as stems -----------------------------
# qwindows / qxcb / qwayland are NOT here, and must never be. The platform
# abstraction plugin is the one Qt cannot start without: prune it and the
# application dies before any of your code runs, with
# "could not load the Qt platform plugin" and no mention of the file you cut.
# It is the single most expensive entry to get wrong, so it is called out rather
# than merely absent.
DROP_STEMS = [
    "Qt6Quick",
    "Qt6Qml",
    "Qt6Pdf",
    "Qt6Network",
    "Qt6VirtualKeyboard",
    "Qt6Multimedia",
    "Qt6WebEngine",
    "Qt6Sql",
    "Qt6Charts",
    "Qt6Test",
    "Qt6Designer",
    "Qt63D",
    # The binding is excluded above, so the library has nothing to bind to.
    # 1.9 MB. If Qt6Gui imports it statically on Windows this will fail at
    # startup with a named missing-DLL error, which the screenshot step catches.
    "Qt6OpenGL",
    # 0.59 MB, and only the qsvg/qsvgicon plugins above use it.
    "Qt6Svg",
]

# Windows ships TWO platform plugins and needs one. qdirect2d is the Direct2D
# alternative, 1.0 MB; qwindows is the default and is the one that must never be
# pruned. NOTE: dropping qdirect2d is safe only while qwindows stays -- CI asserts
# qwindows is present for exactly this reason.
DROP_PLUGINS = [
    "qdirect2d.dll",
]

# WINDOWS-ONLY, AND THE BIGGEST SINGLE WIN AVAILABLE. Read out of the
# win_amd64 wheel on 2026-09-26: icudtl.dat is 10.0 MB and is Chromium's ICU
# data, used by QtWebEngine. This application excludes WebEngine entirely, so it
# is dead weight. (There is no libicu on Windows at all -- Qt uses the native
# Win32 text and locale APIs. On Linux libicu IS a DT_NEEDED of libQt6Core and
# cannot be dropped at any price; the two platforms are not comparable here.)
DROP_FILES = [
    "icudtl.dat",
]

# THE WINDOWS WHEEL SHIPS QT'S DEVELOPER TOOLCHAIN: 14 executables, 12.2 MB,
# read out of pyside6_essentials-6.11.2-cp310-abi3-win_amd64.whl on 2026-09-26.
# `designer.exe`, `linguist.exe` and `assistant.exe` are GUI applications in
# their own right; `uic`, `rcc` and the qml* tools are build-time compilers.
#
# None of them has any business inside a distributed application, and shipping
# them is worse than merely wasteful: they are separate entry points a user or a
# malware scanner can find in your install directory.
#
# They are NOT matched by the Qt6* stems above, because they are executables
# rather than libraries -- which is exactly why they survived the first version
# of this list unnoticed.
DROP_EXES = [
    "qmlls.exe", "qmlformat.exe", "assistant.exe", "linguist.exe",
    "lupdate.exe", "lrelease.exe", "designer.exe", "uic.exe",
    "qmltyperegistrar.exe", "qmlimportscanner.exe", "rcc.exe",
    "qmllint.exe", "qmlcachegen.exe", "svgtoqml.exe",
]

# 19.7 MB, the LARGEST file in the Windows wheel -- bigger than Qt6Core.dll.
# opengl32sw.dll is the Mesa llvmpipe software OpenGL fallback, which is what Qt
# uses when the machine has no usable GPU driver.
DROP_SOFTWARE_OPENGL = True

# DIRECTORIES ARE MATCHED BY SEGMENT, NOT BY PREFIX, AND THAT IS NOT
# PEDANTRY. The first version of this list used full prefixes copied from a
# Linux build -- `PySide6/Qt/qml`, `PySide6/Qt/translations`. On Windows the
# wheel puts those at `PySide6/qml` and `PySide6/translations`, one level up.
DROP_SEGMENTS = [
    "qml",              # 1,762 files / 19.0 MB in the Windows wheel
    "translations",     # 196 files / 13.1 MB
    "sqldrivers",
    "multimedia",
    "virtualkeyboard",
    "qmltooling",
    "designer",
    "webengine",
    # 2.2 MB of image codecs -- qjpeg, qwebp, qtiff, qgif, qicns, qtga, qsvg
    # -- in an application whose entire interface is four text labels. Qt loads
    # these lazily when something asks it to decode an image, and nothing here
    # ever does. Add them back the moment this window grows an icon or a
    # QPixmap: the failure is a silently blank image, not an error.
    "imageformats",
    "iconengines",
]


def unwanted(dest):
    """True if this destination path should not ship. Case-insensitive.

    Windows paths arrive with backslashes and Linux with forward slashes, so
    both separators are normalised before the directory test. Getting that wrong
    is a filter that works on one platform and silently keeps everything on the
    other.
    """
    flat = dest.replace("\\", "/").lower()
    base = flat.rsplit("/", 1)[-1]
    if base in [f.lower() for f in DROP_FILES]:
        return True
    if base in [f.lower() for f in DROP_EXES]:
        return True
    if base in [f.lower() for f in DROP_PLUGINS]:
        return True
    if DROP_SOFTWARE_OPENGL and base == "opengl32sw.dll":
        return True
    if any(stem.lower() in base for stem in DROP_STEMS):
        return True
    # Whole path components, so the depth of the layout does not matter.
    return any(seg in flat.split("/")[:-1] for seg in DROP_SEGMENTS)

a = Analysis(
    ["../app/main.py"],
    pathex=[".."],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDE_MODULES,
    noarchive=False,
    optimize=0,
)

# --- the filter, and the assertion that it worked ---------------------------
before = (len(a.binaries), len(a.datas))
# Plain lists: TOC still exists in 6.x but is deprecated, and it was only ever
# a list subclass.
a.binaries = [e for e in a.binaries if not unwanted(e[0])]
a.datas = [e for e in a.datas if not unwanted(e[0])]
after = (len(a.binaries), len(a.datas))

removed = (before[0] - after[0]) + (before[1] - after[1])
print("[spec] binaries %d -> %d, datas %d -> %d (%d entries dropped)"
      % (before[0], after[0], before[1], after[1], removed))

# Set HELLO_DUMP_TOC=1 to print what SURVIVED, largest first.
if os.environ.get("HELLO_DUMP_TOC"):
    rows = []
    for dest, src, _kind in list(a.binaries) + list(a.datas):
        try:
            rows.append((os.path.getsize(src), dest))
        except OSError:
            rows.append((0, dest))
    print("[spec] %d entries survive, largest 30:" % len(rows))
    for size, dest in sorted(rows, reverse=True)[:30]:
        print("[spec]   %9.2f KB  %s" % (size / 1024.0, dest))

# A pattern list that matches nothing is indistinguishable from a tidy build.
# Fail here instead: a wrong stem, a renamed directory or a Qt reorganisation all
# show up as this assertion rather than as an installer that is quietly 195 MB.
if removed == 0:
    raise SystemExit(
        "[spec] the exclusion list matched nothing. Either PySide6 stopped "
        "collecting these components (delete the stale entries) or the stems "
        "no longer match (fix them). Do not ignore this: an unfiltered bundle "
        "builds and runs perfectly well, just three times the size."
    )

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HelloNsis",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Written by build.py from app/version.py. Absent on non-Windows, where
    # PyInstaller ignores the argument.
    version=os.environ.get("HELLO_VERSION_FILE") or None,
    icon=os.environ.get("HELLO_ICON") or None,
)

# COLLECT, not a one-file EXE, and this is a licence decision rather than a
# packaging preference. The LGPL asks that the user be able to replace the
# library; a --onefile build unpacks to a temporary directory at every launch,
# so there is no Qt DLL on disk for anyone to substitute. One directory also
# means the installer can ship the Qt libraries as ordinary files, which is what
# makes the obligation visible instead of merely claimed.
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="HelloNsis",
)
