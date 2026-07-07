#!/usr/bin/env bash
#
# Generate a "Read aloud with StackVox" MP3 for a blog post.
#
#   tools/generate-audio.sh [path/to/_posts/post.md]   # defaults to newest post
#   STACKVOX_VOICE=bm_george tools/generate-audio.sh    # pick a voice
#
# Requires StackVox (bundled with the Stack Nudge app, or `pipx install stackvox`)
# and ffmpeg. The Kokoro model auto-downloads on first use.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VOICE="${STACKVOX_VOICE:-af_aoede}"

# Resolve the stackvox binary: PATH first, then the Stack Nudge app's venvs.
STACKVOX="$(command -v stackvox || true)"
for cand in \
  "$HOME/.stack-nudge/venv/bin/stackvox" \
  "$HOME/Applications/StackNudge.app/Contents/Resources/venv/bin/stackvox"; do
  [ -n "$STACKVOX" ] && break
  [ -x "$cand" ] && STACKVOX="$cand"
done
[ -n "$STACKVOX" ] || { echo "error: stackvox not found (try: pipx install stackvox)" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "error: ffmpeg not found (try: brew install ffmpeg)" >&2; exit 1; }

POST="${1:-$(ls -1 "$REPO"/_posts/*.md | sort | tail -1)}"
[ -f "$POST" ] || { echo "error: no such post: $POST" >&2; exit 1; }

# Jekyll's page.slug drops the leading YYYY-MM-DD- date and the extension.
SLUG="$(basename "$POST" .md | sed -E 's/^[0-9]{4}-[0-9]{2}-[0-9]{2}-//')"
OUTDIR="$REPO/assets/audio"
mkdir -p "$OUTDIR"

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
python3 "$REPO/tools/read-aloud.py" "$POST" > "$TMP/clean.txt"

echo "→ post:  $(basename "$POST")"
echo "→ voice: $VOICE  ($(wc -w < "$TMP/clean.txt" | tr -d ' ') words)"
echo "→ synthesizing with StackVox…"
"$STACKVOX" speak --file "$TMP/clean.txt" --voice "$VOICE" --out "$TMP/out.wav"

echo "→ encoding mp3…"
ffmpeg -v error -y -i "$TMP/out.wav" -codec:a libmp3lame -b:a 96k -ac 1 "$OUTDIR/$SLUG.mp3"

echo "✓ assets/audio/$SLUG.mp3  ($(du -h "$OUTDIR/$SLUG.mp3" | cut -f1))"
