#!/usr/bin/env bash
#
# Generate a "Read aloud with StackVox" MP3 for a blog post.
#
#   tools/generate-audio.sh [path/to/_posts/post.md]   # defaults to newest post
#   STACKVOX_VOICE=bm_george tools/generate-audio.sh    # pick a voice
#   STACKVOX_SPEED=0.9 tools/generate-audio.sh          # tweak speech rate (default 0.95)
#
# Requires StackVox (bundled with the Stack Nudge app, or `pipx install stackvox`)
# and ffmpeg. The Kokoro model auto-downloads on first use.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VOICE="${STACKVOX_VOICE:-af_aoede}"
SPEED="${STACKVOX_SPEED:-0.95}"

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
echo "→ voice: $VOICE @ ${SPEED}x  ($(wc -w < "$TMP/clean.txt" | tr -d ' ') words)"
# read-aloud.py emits the title on line 1. Synthesize it separately and splice a
# real silent beat before the body — StackVox concatenates text with no gap, so
# punctuation alone can't make a meaningful pause after the title.
GAP="${STACKVOX_TITLE_GAP:-0.7}"
sed -n '1p' "$TMP/clean.txt" > "$TMP/title.txt"
sed '1d'    "$TMP/clean.txt" > "$TMP/body.txt"
synth() { "$STACKVOX" speak --file "$1" --voice "$VOICE" --speed "$SPEED" --out "$2"; }

echo "→ synthesizing with StackVox…"
if [ -s "$TMP/title.txt" ] && [ -s "$TMP/body.txt" ]; then
  synth "$TMP/title.txt" "$TMP/title.wav"
  synth "$TMP/body.txt"  "$TMP/body.wav"
  echo "→ stitching a ${GAP}s pause after the title…"
  ffmpeg -v error -y -i "$TMP/title.wav" -i "$TMP/body.wav" \
    -filter_complex "[0]apad=pad_dur=${GAP}[t];[t][1]concat=n=2:v=0:a=1[a]" \
    -map "[a]" "$TMP/out.wav"
else
  synth "$TMP/clean.txt" "$TMP/out.wav"
fi

echo "→ encoding mp3…"
ffmpeg -v error -y -i "$TMP/out.wav" -codec:a libmp3lame -b:a 96k -ac 1 "$OUTDIR/$SLUG.mp3"

echo "✓ assets/audio/$SLUG.mp3  ($(du -h "$OUTDIR/$SLUG.mp3" | cut -f1))"
