# Getting Bristol into your Dock

Two approaches, for two different needs:

- **Live-source launcher (recommended while iterating).** A tiny `.app` whose
  executable is a shell script that runs the repo source directly. Edit
  `src/tools/bristol/*.py`, relaunch, done — no build step, ever. Trade-off:
  the running process is Python, so the macOS **menu-bar name reads "Python"**
  (the window title and Dock icon are still Bristol). Best while the app is
  still changing.
- **Frozen bundle (py2app).** A self-contained, relocatable `Bristol.app` with
  correct app identity. Portable, but you must **rebuild after every code
  change**. Use this once development settles and you want a standalone
  artifact.

Both produce a real Dock icon. The launcher and any built bundle are
user-specific artifacts (they hard-code your paths), so they live outside
version control, never committed.

---

## Approach A — live-source launcher (no build)

```bash
python3 src/tools/bristol/make_launcher.py
```

That writes `~/Applications/Bristol.app` — a minimal bundle whose executable is
a shell script that runs this repo's `app.py`. Open it once from Finder, then
right-click its Dock tile → Options → Keep in Dock. Editing any `ui/*.py` or
`app.py` takes effect on the next launch; there is nothing to rebuild.

Run the same command again after moving or renaming the repo folder, or after
switching to a different Python.

What the tool handles for you:

- **The Python that actually has PySide6.** A Finder-launched app gets a
  minimal `PATH`, so a bare `python3` often resolves to a system Python
  without PySide6. The tool tests candidates and bakes in the absolute path of
  one that imports it.
- **Surviving a repo move.** The generated script resolves the repo at launch
  from the instance pointer (`instance.py`), falling back to the path baked in
  when it was generated, and shows an alert naming this command if neither
  resolves.
- **The icon**, copied from `icon.icns` next to the tool.

The bundle holds absolute paths, so it is a per-machine artifact: it lives in
`~/Applications`, outside the repo, and is never committed.

---

## Approach B — frozen bundle (py2app)

This produces a self-contained `Bristol.app` you launch by double-clicking,
no Terminal, correct app identity.

### One-time setup

```bash
cd src/tools/bristol
python3 -m pip install --upgrade py2app PySide6
```

### Step 1 — write the instance pointer (once)

A built `.app` is relocatable, so it can't discover the database by walking up
the repo folders the way `python3 app.py` does. Write the per-machine pointer
that tells it where this installation lives:

```bash
python3 ../config_tools/instance_pointer.py --write
```

That creates `~/Library/Application Support/BristolTickets/instance.json`
holding the repo root, the data root, the instance slug and the config path.
It sits outside the repo, so it can never be committed and never has to be
bundled into the app. The same pointer is what lets the bundled app find the
notebook it writes reports into. Full resolution order:
`src/tools/config_tools/instance_pointer.py`.

(For a one-off you can still launch with `TICKETS_DB=/path/... open
"dist/Bristol.app"` — the env var wins over everything.)

### Step 2 — the icon (already included)

`icon.icns` already ships next to `setup.py` (the coral double-roll-ticket "B"),
and `setup.py` picks it up automatically — nothing to do. To regenerate it from
a new PNG:

```bash
mkdir icon.iconset
sips -z 512 512 source.png --out icon.iconset/icon_512x512.png
iconutil -c icns icon.iconset -o icon.icns
```

### Step 3 — build

```bash
python3 setup.py py2app
```

The app appears at `dist/Bristol.app`. Double-click it, or drag it to
`/Applications`. `build/` and `dist/` are git-ignored.

### Rebuilding

After changing any code, delete the old build and rebuild:

```bash
rm -rf build dist
python3 setup.py py2app
```

### Troubleshooting

- **"App can't be opened / unidentified developer"** — right-click the app →
  Open, once, to approve it (it's unsigned).
- **App launches then quits** — run the binary directly to see the error:
  `"dist/Bristol.app/Contents/MacOS/Bristol"`. Most often it's a wrong path
  in the instance pointer (`python3 ../config_tools/instance_pointer.py` prints
  it), or a missing Qt plugin (reinstall PySide6 and rebuild clean).
- **Prefer no build at all?** Use **Approach A** (live-source launcher) above —
  a Dock icon that runs the repo source with no build step. The frozen bundle
  is only worth it when you want a portable, self-contained artifact.
