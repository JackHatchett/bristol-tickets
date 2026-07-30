#!/usr/bin/env bash
# run_smoke.sh — provision a headless Qt env (if needed) and run smoke.py.
#
# On a normal machine with PySide6 + a display this is basically a passthrough.
# In the Linux Cowork sandbox it also: installs PySide6, and — because the
# sandbox lacks the GL/EGL libs Qt needs and has no root to apt-install them —
# fetches those .debs and extracts the .so files into a local cache pointed at
# by LD_LIBRARY_PATH. All throwaway; the sandbox resets each session.
#
# Usage:
#   bash run_smoke.sh                 # all targets
#   bash run_smoke.sh bristol         # one or more named targets
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE="${TMPDIR:-/tmp}/qt_headless_cache"
LIBDIR="$CACHE/lib/x86_64-linux-gnu"

python3 -c "import PySide6" 2>/dev/null \
  || pip install --break-system-packages --quiet PySide6

# Only needed on Linux where libEGL is absent (skipped on macOS / where present).
if [ "$(uname -s)" = "Linux" ] && ! ldconfig -p 2>/dev/null | grep -q libEGL.so.1 \
   && [ ! -e "$LIBDIR/libEGL.so.1" ]; then
  echo "[run_smoke] fetching GL/EGL libs (no root) ..."
  mkdir -p "$CACHE/debs" "$CACHE/x" "$LIBDIR"
  ( cd "$CACHE/debs" && apt-get download libegl1 libglvnd0 libgles2 >/dev/null 2>&1 )
  for d in "$CACHE"/debs/*.deb; do dpkg-deb -x "$d" "$CACHE/x"; done
  cp -a "$CACHE"/x/usr/lib/x86_64-linux-gnu/. "$LIBDIR/" 2>/dev/null || true
fi

if [ -e "$LIBDIR/libEGL.so.1" ]; then
  export LD_LIBRARY_PATH="$LIBDIR:${LD_LIBRARY_PATH:-}"
fi
export QT_QPA_PLATFORM=offscreen

python3 "$HERE/smoke.py" "$@"
