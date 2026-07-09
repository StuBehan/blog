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

# Resolve the stackvox binary. STACKVOX is the first runnable one (used for
# synthesis, which is identical across versions). NORM is the first that speaks
# the 0.7.0 `normalize` subcommand — the Markdown->speech normalizer. Candidates:
# PATH, the local StackVox clone's venv, then the Stack Nudge app's venvs.
# Override either with STACKVOX_BIN / STACKVOX_NORMALIZE.
STACKVOX="" ; NORM="${STACKVOX_NORMALIZE:-}"
for cand in \
  "${STACKVOX_BIN:-$(command -v stackvox || true)}" \
  "$HOME/stackone/stackvox/.venv/bin/stackvox" \
  "$HOME/.stack-nudge/venv/bin/stackvox" \
  "$HOME/Applications/StackNudge.app/Contents/Resources/venv/bin/stackvox"; do
  [ -n "$cand" ] && [ -x "$cand" ] || continue
  [ -n "$STACKVOX" ] || STACKVOX="$cand"
  if [ -z "$NORM" ] && "$cand" --help 2>&1 | grep -qw normalize; then NORM="$cand"; fi
done
[ -n "$NORM" ] && STACKVOX="$NORM"   # prefer the capable binary for synth too
[ -n "$STACKVOX" ] || { echo "error: stackvox not found (try: pipx install stackvox)" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "error: ffmpeg not found (try: brew install ffmpeg)" >&2; exit 1; }

POST="${1:-$(ls -1 "$REPO"/_posts/*.md | sort | tail -1)}"
[ -f "$POST" ] || { echo "error: no such post: $POST" >&2; exit 1; }

# Jekyll's page.slug drops the leading YYYY-MM-DD- date and the extension.
SLUG="$(basename "$POST" .md | sed -E 's/^[0-9]{4}-[0-9]{2}-[0-9]{2}-//')"
OUTDIR="$REPO/assets/audio"
mkdir -p "$OUTDIR"

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

# Turn the post into speakable text. Preferred path: read-aloud.py preps the
# Markdown (front matter -> title on line 1, say: directives -> visible prose),
# then `stackvox normalize` does the Markdown->speech transform with the blog's
# pronunciation dict. If no 0.7.0-capable stackvox is around, fall back to
# read-aloud.py's self-contained --legacy cleaner so nothing breaks.
PRON="$REPO/tools/pronunciations.json"
if [ -n "$NORM" ]; then
  python3 "$REPO/tools/read-aloud.py" "$POST" > "$TMP/prepped.md"
  "$NORM" normalize --file "$TMP/prepped.md" --pronunciations "$PRON" --tables drop > "$TMP/clean.txt"
else
  echo "⚠ no normalize-capable stackvox found; using legacy cleaner" >&2
  python3 "$REPO/tools/read-aloud.py" --legacy "$POST" > "$TMP/clean.txt"
fi

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
