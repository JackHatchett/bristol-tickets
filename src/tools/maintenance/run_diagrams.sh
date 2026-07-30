#!/usr/bin/env bash
set -euo pipefail

# build_diagrams.py defaults to config/config.local.json relative to its own
# location if no path is given, so an explicit arg is optional here too —
# pass one only to point at a non-standard checkout.
python3 ./build_diagrams.py "$@"
