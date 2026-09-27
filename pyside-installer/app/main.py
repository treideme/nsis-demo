"""A PySide6 window holding a greeting and the versions of what is around it.
"""
__author__ = "Thomas Reidemeister"

import sys

from app.version import __version__


def report():
    """Version lines, importable without a display so tests can read them."""
    from PySide6.QtCore import qVersion

    return [
        "Hello, world.",
        "Application %s" % __version__,
        "Qt %s" % qVersion(),
        "Python %d.%d.%d" % sys.version_info[:3],
    ]


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)

    # A frozen GUI application still needs a way to prove it starts without a
    # human at the screen. CI runs this, and it is the difference between
    # "the file was written" and "the bundle works".
    #
    # BUT `print()` IS USELESS HERE ON WINDOWS. PyInstaller builds this with
    # console=False, which is correct for a GUI application and means the process
    # has no console attached: stdout goes nowhere, and a caller that pipes it
    # gets an empty string and a zero exit code. A CI check that greps that
    # output passes vacuously on a bundle that is in fact broken.
    #
    # So the machine-readable path writes to a FILE. It works identically
    # windowed or not, and it is the only form that can be asserted on.
    if "--report" in argv:
        path = argv[argv.index("--report") + 1]
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(report()) + "\n")
        return 0

    # Kept for a developer running it from a terminal, where a console does
    # exist because they built with console=True or ran it unfrozen.
    if "--version" in argv:
        print("\n".join(report()))
        return 0

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

    app = QApplication(argv)
    window = QWidget()
    window.setWindowTitle("Hello, NSIS")
    layout = QVBoxLayout(window)
    for line in report():
        label = QLabel(line)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
    window.resize(360, 170)
    window.show()

    # `--quit-after N` lets CI photograph a real window and then get its runner
    # back. Without it the screenshot step has to kill the process, which on
    # Windows means the exit code tells you nothing about whether the
    # application was healthy when the picture was taken.
    if "--quit-after" in argv:
        from PySide6.QtCore import QTimer

        seconds = float(argv[argv.index("--quit-after") + 1])
        QTimer.singleShot(int(seconds * 1000), app.quit)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
