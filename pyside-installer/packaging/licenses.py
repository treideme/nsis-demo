"""Generate the third-party licence manifest that the installer shows.

The obligation is simple and boring: if you redistribute someone's library, you
ship its licence text or at least name it. The interesting part is where the
answer comes from. This reads the metadata of the environment that actually
produced the build, rather than a list somebody maintains by hand, because a
hand-maintained list is wrong the first time a transitive dependency changes.

THREE PLACES A LICENCE CAN HIDE, and reading only the first is the classic bug:

  1. `License-Expression`  -- PEP 639, an SPDX string. What new wheels use.
  2. `License`             -- the old free-text field. Often empty now, and
                              sometimes holds an entire licence text.
  3. `Classifier: License :: ...` -- frequently the only one populated.

Reading only `License` was how the predecessor of this script reported "UNKNOWN"
for most of the tree while looking like it had worked.
"""

import argparse
import sys
from importlib.metadata import distributions

# Build-time only. These never reach the user's disk, so listing them overstates
# what is being redistributed -- which is its own kind of wrong.
BUILD_ONLY = {
    "pyinstaller",
    "pyinstaller-hooks-contrib",
    "jinja2",
    "markupsafe",
    "setuptools",
    "wheel",
    "packaging",
    "altgraph",
    "pefile",
    "pywin32-ctypes",
    "macholib",
}

# Things pip cannot see, because they are not pip packages. The Python runtime
# is inside the bundle whether or not anything declares it.
ALWAYS = [
    ("CPython", sys.version.split()[0], "PSF-2.0", "https://docs.python.org/3/license.html"),
]

CLASSIFIER = "License :: "


def licence_of(dist):
    """Best available licence name for one distribution, and where it came from."""
    meta = dist.metadata

    expression = meta.get("License-Expression")
    if expression and expression.strip():
        return expression.strip(), "License-Expression"

    classifiers = [
        c[len(CLASSIFIER):].strip()
        for c in meta.get_all("Classifier") or []
        if c.startswith(CLASSIFIER)
    ]
    # "OSI Approved :: MIT License" -> "MIT License". The leading segment says
    # nothing about which licence it is.
    trimmed = [c.split(" :: ")[-1] for c in classifiers if c != "OSI Approved"]
    if trimmed:
        return "; ".join(trimmed), "Classifier"

    declared = (meta.get("License") or "").strip()
    if declared:
        # Some wheels put the whole licence text in this field. One line of it
        # is a name; twenty is a document, and a manifest is not the place.
        first = declared.splitlines()[0].strip()
        if len(first) <= 80:
            return first, "License"
        return "see bundled licence text", "License (full text)"

    return "UNKNOWN", "nothing"


def collect():
    rows = []
    for dist in distributions():
        name = dist.metadata.get("Name")
        if not name or name.lower() in BUILD_ONLY:
            continue
        licence, source = licence_of(dist)
        rows.append((name, dist.version or "?", licence, source))
    for name, version, licence, _url in ALWAYS:
        rows.append((name, version, licence, "hardcoded"))
    # Case-insensitive, so the order does not depend on which wheels happened to
    # capitalise their names.
    return sorted(rows, key=lambda r: r[0].lower())


def render(rows):
    width = max(len(r[0]) for r in rows)
    out = [
        "Third-party components redistributed with this application",
        "=" * 58,
        "",
        "Read from the build environment's own package metadata. Regenerate",
        "rather than edit: any change here is lost on the next build.",
        "",
    ]
    for name, version, licence, _source in rows:
        out.append("%-*s  %-10s  %s" % (width, name, version, licence))
    out += [
        "",
        "PySide6 and shiboken6 declare LGPL-3.0-only OR GPL-2.0-only OR",
        "GPL-3.0-only, and this build relies on the LGPL option. That choice is",
        "why the Qt libraries stay separate, replaceable files rather than being",
        "folded into one executable: the LGPL asks that the user be able to swap",
        "the library, and a single-file build takes that away.",
    ]
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-o", "--output", help="write here instead of stdout")
    ap.add_argument("--audit", action="store_true",
                    help="show which metadata field answered for each package")
    a = ap.parse_args(argv)

    rows = collect()
    if a.audit:
        for name, version, licence, source in rows:
            print("%-28s %-12s %-34s from %s" % (name, version, licence, source))
        unknown = [r[0] for r in rows if r[2] == "UNKNOWN"]
        print("\n%d packages, %d with no licence metadata at all" % (len(rows), len(unknown)))
        if unknown:
            print("  " + ", ".join(unknown))
        return 1 if unknown else 0

    text = render(rows)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as handle:
            handle.write(text)
        print("wrote %s (%d components)" % (a.output, len(rows)))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
