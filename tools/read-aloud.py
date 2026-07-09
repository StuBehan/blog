#!/usr/bin/env python3
"""Prepare a Jekyll post's Markdown for StackVox's speech normalizer.

StackVox 0.7.0+ owns the Markdown->speech transform (`stackvox normalize`):
units, numbers, pauses, pronunciations, terminal stops. Two things it can't
know about stay here, and this script handles them, emitting Markdown for the
normalizer to consume:

  * front matter — strip it, and put the title on line 1 so generate-audio.sh
    can splice a silent beat after it (line breaks alone make no gap);
  * the ``<!-- say: … -->`` directive — audio-only text that is invisible on
    the page. The normalizer strips HTML comments, so a raw directive would be
    *deleted*; we surface it as visible prose first.

Usage:
  read-aloud.py path/to/post.md        # emit prepped Markdown for `stackvox normalize`
  read-aloud.py --legacy path/to/post.md   # self-contained cleaner (pre-0.7.0 fallback)
"""
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def split_front_matter(text):
    """Return (title, body). Front matter is the first --- ... --- block."""
    title = ""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = text[3:end]
            body = text[end + 4:]
            m = re.search(r'^\s*title:\s*"?(.*?)"?\s*$', fm, re.MULTILINE)
            if m:
                title = m.group(1).strip()
            return title, body
    return title, text


def expand_say(body):
    """Turn ``<!-- say: X -->`` into a standalone paragraph ``X``.

    StackVox's normalizer strips HTML comments, so a raw say: directive would
    vanish. Surfacing it as its own paragraph (blank lines around it) keeps it
    invisible on the page but spoken, and X still flows through normalization,
    so units/decimals inside a directive are voiced correctly."""
    return re.sub(r"<!--\s*say:\s*(.*?)\s*-->", r"\n\n\1\n\n", body, flags=re.DOTALL)


def preprocess(path):
    """Front matter -> title on line 1; say: directives -> visible prose. No
    text transforms here — that's the normalizer's job."""
    title, body = split_front_matter(load(path))
    body = expand_say(body).strip()
    parts = [title] if title else []
    if body:
        parts.append(body)
    return "\n\n".join(parts)


# --------------------------------------------------------------------------- #
# Legacy fallback: self-contained cleaner for StackVox < 0.7.0 (no normalizer).
# Kept only as a bridge so audio generation never breaks on an old bundle;
# remove once `stackvox normalize` ships everywhere this runs. The pronunciation
# dict is shared with the CLI path via tools/pronunciations.json.
# --------------------------------------------------------------------------- #


def _load_pronunciations():
    try:
        with open(os.path.join(_HERE, "pronunciations.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}


PRONUNCIATIONS = _load_pronunciations()

UNIT_RULES = [
    (r"£\s?(\d[\d,]*(?:\.\d+)?)", r"\1 pounds"),   # £1.63 -> 1.63 pounds
    (r"\bkWh\b", "kilowatt hours"),
    (r"\bMPG\b", "miles per gallon"),
    (r"(\d)\s?kg\b", r"\1 kilograms"),
    (r"(\d)\s?km\b", r"\1 kilometres"),
    (r"(\d)p\b", r"\1 pence"),
    (r"\s*÷\s*", " divided by "),
    (r"\s*×\s*", " times "),
    (r"\s*=\s*", " equals "),
]


def apply_pronunciations(text):
    for written, spoken in PRONUNCIATIONS.items():
        text = re.sub(rf"\b{re.escape(written)}\b", spoken, text, flags=re.IGNORECASE)
    return text


def apply_units(text):
    for pattern, repl in UNIT_RULES:
        text = re.sub(pattern, repl, text)
    return text


def ensure_stop(text):
    return text if text.endswith((".", "!", "?", ":", "…")) else text + "."


def strip_inline(line):
    line = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", line)        # images
    line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)     # links -> text
    line = re.sub(r"`([^`]*)`", r"\1", line)                 # inline code
    line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)           # bold
    line = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"\1", line)    # _italic_
    line = re.sub(r"\*([^*]+)\*", r"\1", line)               # *italic*
    line = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)            # headings
    line = re.sub(r"^\s*>\s?", "", line)                     # blockquote
    line = re.sub(r"^\s*[-*+]\s+", "", line)                 # bullet markers
    line = re.sub(r"^\s*\d+\.\s+", "", line)                 # ordered markers
    line = re.sub(r"<[^>]+>", "", line)                      # stray HTML
    line = re.sub(r"(?<=\d),(?=\d)", "", line)               # thousands sep
    line = line.replace("→", " to ")                        # arrows
    line = re.sub(r"\s*[—–]\s*", " ... ", line)             # em / en dash
    line = re.sub(r"\s+--?\s+", " ... ", line)              # spaced ASCII hyphen(s)
    line = re.sub(r"(\w)\s*\(", r"\1, (", line)             # comma pause before "("
    line = apply_pronunciations(line)
    line = apply_units(line)
    line = re.sub(r"(\d+)\.(\d+)",
                  lambda m: m.group(1) + " point " + " ".join(m.group(2)), line)
    line = re.sub(r"[ \t]{2,}", " ", line)
    return line.strip()


def clean(body):
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)  # fenced code
    paragraphs, current = [], []
    for raw in body.splitlines():
        says = re.findall(r"<!--\s*say:\s*(.*?)\s*-->", raw)
        if says:
            raw = re.sub(r"<!--\s*say:\s*.*?-->", "", raw)
            if current:
                paragraphs.append(" ".join(current)); current = []
            for s in says:
                spoken = strip_inline(s)
                if spoken:
                    paragraphs.append(spoken)
            if not raw.strip():
                continue
        row = raw.strip()
        is_table_row = row.startswith("|") and row.endswith("|")
        if is_table_row or re.fullmatch(r"\s*([-*_]\s*){3,}", raw) or re.fullmatch(r"\s*\|?[ :|-]+\|?\s*", raw):
            if current:
                paragraphs.append(" ".join(current)); current = []
            continue
        is_heading = re.match(r"^\s{0,3}#{1,6}\s+", raw)
        is_item = re.match(r"^\s*([-*+]|\d+\.)\s+", raw)
        stripped = strip_inline(raw)
        if is_heading:
            if current:
                paragraphs.append(" ".join(current)); current = []
            if stripped:
                paragraphs.append(stripped)
            continue
        if is_item:
            if current:
                paragraphs.append(" ".join(current)); current = []
            if stripped:
                paragraphs.append(stripped)
        elif stripped:
            current.append(stripped)
        elif current:
            paragraphs.append(" ".join(current)); current = []
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs


def legacy(path):
    title, body = split_front_matter(load(path))
    lines = [ensure_stop(title)] if title else []
    lines += [ensure_stop(p) for p in clean(body)]
    return "\n".join(lines)


def main():
    args = sys.argv[1:]
    use_legacy = "--legacy" in args
    args = [a for a in args if a != "--legacy"]
    if len(args) != 1:
        sys.exit("usage: read-aloud.py [--legacy] path/to/post.md")
    print(legacy(args[0]) if use_legacy else preprocess(args[0]))


if __name__ == "__main__":
    main()
