#!/bin/sh
# Render the release notes template into a local file for review.
set -eu
out="${1:-release-notes.md}"
sed "s/{{DATE}}/$(date +%Y-%m-%d)/" "$(dirname "$0")/../assets/template.txt" > "$out"
echo "wrote $out"
