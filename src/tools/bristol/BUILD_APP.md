# Building Bristol Tickets

A release is one command:

```bash
python3 src/tools/bristol/make_release.py
```

It runs the publication checks, builds `dist/BristolTickets.app` with the
project tree staged inside it, writes `BristolTickets-<version>.zip` beside it
with a `.sha256`, and prints the `gh release create` line that publishes them.
`--skip-checks` builds without the checks; a real release does not use it.

The version comes from `src/VERSION`, which is also what the app compares
against an installation it opens. Raise it before building a release, or an
existing installation will not take the update.

---

## What the bundle carries

`setup.py` stages the project's published files into
`Contents/Resources/payload/` — `payload.PUBLISHED_DIRS` and
`payload.PUBLISHED_FILES` name them. `config/config.local.json` and `data/` are
in neither list, so a download installs the system and never an instance of it,
and an update replaces the machinery without reading anyone's board.

On first launch, setup asks where Bristol should live and copies the payload
there. On every later launch, an app whose payload is newer than the folder it
opens refreshes that folder first.

---

## Signing

The release is unsigned and not notarized, so macOS blocks the first launch and
the user allows it once in System Settings → Privacy & Security.
`docs/install.md` §The first launch carries the wording they see.

Removing that step means an Apple Developer Program membership and a Developer
ID certificate: `codesign --deep --options runtime`, `notarytool submit --wait`,
then `stapler staple`, between `build()` and `package()` in `make_release.py`.
Nothing in the build is shaped around its absence, so it is an addition rather
than a change.

---

## The live-source launcher, for iterating

```bash
python3 src/tools/bristol/make_launcher.py
```

That writes `~/Applications/BristolTickets.app` — a minimal bundle whose
executable is a shell script that runs this repo's `app.py`. Editing any
`ui/*.py` or `app.py` takes effect on the next launch; there is nothing to
rebuild. It carries no payload, so it installs nothing and updates nothing.

Trade-off: the running process is Python, so the macOS **menu-bar name reads
"Python"** (the window title and Dock icon are still Bristol Tickets).

Run the same command again after moving or renaming the folder, or after
switching to a different Python.

What the tool handles for you:

- **The Python that actually has PySide6.** A Finder-launched app gets a
  minimal `PATH`, so a bare `python3` often resolves to a system Python
  without PySide6. The tool tests candidates and bakes in the absolute path of
  one that imports it.
- **Surviving a folder move.** The generated script resolves the project at
  launch from the instance pointer (`instance.py`), falling back to the path
  baked in when it was generated, and shows an alert naming this command if
  neither resolves.
- **The icon**, copied from `icon.icns` next to the tool.

The bundle holds absolute paths, so it is a per-machine artifact: it lives in
`~/Applications`, outside the project, and is never committed.

---

## One-time setup for building

```bash
cd src/tools/bristol
python3 -m pip install --upgrade py2app PySide6
```

### The icon (already included)

`icon.icns` already ships next to `setup.py` (the coral double-roll-ticket "B"),
and `setup.py` picks it up automatically. To regenerate it from a new PNG:

```bash
mkdir icon.iconset
sips -z 512 512 source.png --out icon.iconset/icon_512x512.png
iconutil -c icns icon.iconset -o icon.icns
```

### Building the bundle alone

```bash
python3 setup.py py2app          # → dist/BristolTickets.app
```

`build/` and `dist/` are git-ignored. After changing any code, `make_release.py`
clears both before building; doing it by hand means `rm -rf build dist` first.

---

## Troubleshooting

- **"App can't be opened" / "Apple could not verify"** — expected on an
  unsigned build. See §Signing, and `docs/install.md` for the steps a user
  takes.
- **App launches then quits** — run the binary directly to see the error:
  `"dist/BristolTickets.app/Contents/MacOS/BristolTickets"`. Most often a
  missing Qt plugin (reinstall PySide6 and rebuild clean), or a wrong path in
  the instance pointer (`python3 ../config_tools/instance_pointer.py` prints
  it).
- **Setup opens on an app that should already be installed** — the payload did
  not stage. `make_release.py` fails the build on this rather than shipping it;
  a bare `setup.py py2app` does not check.
