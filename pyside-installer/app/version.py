"""The one place the version number is written down.

The PyInstaller version resource, the NSIS script and the third-party licence
manifest all read it from here. A release therefore cannot ship an installer
that claims 1.2.0 wrapped around an executable that claims 1.1.0, which is the
failure this file exists to prevent: nothing in either toolchain checks that
those two numbers agree.
"""

__version__ = "1.0.0"
