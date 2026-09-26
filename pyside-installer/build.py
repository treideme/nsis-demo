"""Build the application, the licence manifest and the installer, in that order.

The order is not arbitrary. The licence manifest has to exist before makensis
runs, because the installer script embeds it in a licence page and NSIS resolves
that path at compile time -- a missing file is a compile error, which is the
good outcome, but only if it happens before you ship.

WHAT THIS SCRIPT IS REALLY FOR: there is one version number, in app/version.py,
and it has to reach two completely unrelated version resources -- the one
PyInstaller stamps on the application executable, and the one NSIS stamps on the
installer executable. Nothing connects them. Typing either by hand is how you
ship an installer claiming 1.2.0 wrapped around an application claiming 1.1.0,
with both toolchains perfectly satisfied.

Usage:
    python build.py                 # everything available on this platform
    python build.py --skip-installer  # stop after PyInstaller and the manifest
"""

import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGING = os.path.join(HERE, "packaging")
DIST = os.path.join(HERE, "dist")
BUILD = os.path.join(HERE, "build")
MANIFEST = os.path.join(DIST, "THIRD-PARTY-LICENSES.txt")
VERSION_FILE = os.path.join(BUILD, "version_resource.txt")


def read_version():
    """Read __version__ without importing the package, so this runs before PySide6 does."""
    path = os.path.join(HERE, "app", "version.py")
    namespace = {}
    with open(path, encoding="utf-8") as handle:
        exec(compile(handle.read(), path, "exec"), namespace)
    version = namespace["__version__"]
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise SystemExit(
            "app/version.py must hold three dot-separated integers, not %r. "
            "Windows version resources are numeric tuples and will not take "
            "anything else." % version
        )
    return version, [int(p) for p in parts]


def render_version_resource(version, triple):
    from jinja2 import Template

    with open(os.path.join(PACKAGING, "version.j2"), encoding="utf-8") as handle:
        template = Template(handle.read(), keep_trailing_newline=True)

    os.makedirs(BUILD, exist_ok=True)
    text = template.render(
        major=triple[0], minor=triple[1], patch=triple[2], version=version,
        publisher="Reidemeister Labs",
        product="Hello NSIS",
        description="Hello NSIS -- a PySide6 application behind an NSIS installer",
        exe_name="HelloNsis",
        copyright="(C) Reidemeister Labs",
    )
    with open(VERSION_FILE, "w", encoding="utf-8") as handle:
        handle.write(text)
    print("[build] version resource -> %s" % VERSION_FILE)
    return VERSION_FILE


def run(argv, **kwargs):
    print("[build] %s" % " ".join(argv))
    subprocess.run(argv, check=True, **kwargs)


def freeze(version_file):
    env = dict(os.environ, HELLO_VERSION_FILE=version_file)
    # The spec is addressed by path and PyInstaller is run through the current
    # interpreter, so this works the same from a venv on either platform.
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
         "--distpath", DIST, "--workpath", os.path.join(BUILD, "pyinstaller"),
         os.path.join(PACKAGING, "hello.spec")], env=env, cwd=PACKAGING)


def manifest():
    os.makedirs(DIST, exist_ok=True)
    run([sys.executable, os.path.join(PACKAGING, "licenses.py"), "-o", MANIFEST])


def find_makensis():
    found = shutil.which("makensis")
    if found:
        return found
    # The default choco/installer location, which is not on PATH.
    candidate = r"C:\Program Files (x86)\NSIS\makensis.exe"
    return candidate if os.path.exists(candidate) else None


def compile_installer(version):
    makensis = find_makensis()
    if not makensis:
        print("[build] makensis not found -- skipping the installer.\n"
              "        On Windows: choco install nsis. On Debian/Ubuntu: apt install nsis\n"
              "        (makensis cross-compiles a Windows installer from Linux, but the\n"
              "         payload it wraps still has to be a Windows build.)")
        return None

    out = os.path.join(DIST, "HelloNsisSetup.exe")
    run([makensis,
         "/DVERSION=%s" % version,
         "/DSRC=%s" % os.path.join(DIST, "HelloNsis"),
         "/DLICENSE_APP=%s" % os.path.join(os.path.dirname(HERE), "LICENSE"),
         "/DLICENSE_THIRDPARTY=%s" % MANIFEST,
         "/DOUT=%s" % out,
         os.path.join(PACKAGING, "installer.nsi")])
    print("[build] installer -> %s" % out)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skip-installer", action="store_true")
    a = ap.parse_args(argv)

    version, triple = read_version()
    print("[build] version %s" % version)

    version_file = render_version_resource(version, triple)
    freeze(version_file)
    manifest()

    if a.skip_installer:
        print("[build] stopping before the installer, as asked.")
        return 0

    compile_installer(version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
