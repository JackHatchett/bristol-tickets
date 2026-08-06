# Third-party components

Bristol Tickets is distributed under the terms in `LICENSE`. It builds on the
components below, which carry their own terms.

## Qt for Python (PySide6) and the Qt libraries

Copyright The Qt Company Ltd. and other contributors.

Licensed under the GNU Lesser General Public License version 3 (LGPLv3). The
full text is at <https://www.gnu.org/licenses/lgpl-3.0.html>, and a copy ships
inside the installed package as `PySide6/licenses/`.

A `BristolTickets.app` bundle carries a compiled copy of these libraries inside
`Contents/Resources/lib/`. LGPLv3 §4 entitles a recipient of that bundle to
replace them with their own build. To do so:

1. Build or install the PySide6 version the bundle was built against.
2. Replace the `PySide6` directory under `Contents/Resources/lib/python*/` with
   that copy.
3. Re-launch the bundle.

// Replacing the libraries invalidates any code signature on the bundle; macOS
// asks the user to approve the modified copy on its next launch.

Qt for Python's own source is at <https://code.qt.io/cgit/pyside/pyside-setup.git/>.

## Python

Copyright the Python Software Foundation. Licensed under the PSF License
Agreement, <https://docs.python.org/3/license.html>. A bundle built with py2app
carries a copy of the interpreter.
