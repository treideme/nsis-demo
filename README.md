# nsis-demo

A small [NSIS](https://nsis.sourceforge.io/) installer project built to accompany a blog post touring
NSIS's feature set. It's exercised entirely by GitHub Actions on `windows-latest`:

- `install.nsi` builds a real GUI installer (Modern UI 2) that installs a stand-in "app"
  (`notepad.exe`, copied from the runner itself at build time - never committed here) plus the
  Visual C++ Redistributable (x64) as an optional, skip-if-present component.
- A custom [`nsDialogs`](https://nsis.sourceforge.io/Docs/nsDialogs/Readme.html) page shows release
  notes pulled straight from [`releasenotes/`](releasenotes) at build time.
- [`.github/workflows/ci.yml`](.github/workflows/ci.yml) compiles the installer, runs it in full GUI
  mode (not `/S` silent), drives the wizard, takes a screenshot mid-install, verifies the install,
  and uploads the installer, the screenshot, and the installed file tree as run artifacts.
- [`.github/workflows/release.yml`](.github/workflows/release.yml) does the same build on a `vX.Y.Z`
  tag push and attaches the installer plus the matching release notes to a GitHub Release.

## Cutting a release

1. Add `releasenotes/X.Y.Z.md`.
2. `git tag vX.Y.Z && git push --tags`.

See the accompanying blog post for the full walkthrough: <https://reidemeister.com/blog/2026.02.07>
