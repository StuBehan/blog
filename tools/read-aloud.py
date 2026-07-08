#!/usr/bin/env python3
"""Turn a Jekyll post's Markdown into clean, speakable plain text.

Strips front matter, code, and Markdown syntax so StackVox reads prose,
not backticks and URLs. Emits one line per paragraph (better prosody than
feeding raw line breaks). Usage: read-aloud.py path/to/post.md > clean.txt
"""
import re
import sys

# Pronunciation library: written form -> how it should be spoken.
# Matched whole-word and case-insensitively, so "agy"/"AGY" both work.
# Add an entry whenever StackVox mangles a term (acronyms, product names, etc.).
PRONUNCIATIONS = {
    "agy": "antigravity",
    "1M": "1 million",
    "175K": "175 thousand",
    "xhigh": "x high",
    "SessionStart": "session start",
    "PermissionRequest": "permission request",
    "StackOne": "stack one",
    "OAuth": "oh auth",
    "Behan": "Bayan",  # say "BAY-an", not "B-hen"
    "Redis": "Reddiss",  # say "RED-iss", not "ree-dees"
    "dir": "directory",
}


def apply_pronunciations(text):
    for written, spoken in PRONUNCIATIONS.items():
        text = re.sub(rf"\b{re.escape(written)}\b", spoken, text, flags=re.IGNORECASE)
    return text


# Units & math symbols: (regex, replacement), applied after the word library.
# Digit-glued units capture the leading digit and re-emit it, so "65kg" -> "65 kilograms".
UNIT_RULES = [
    (r"£\s?(\d[\d,]*(?:\.\d+)?)", r"\1 pounds"),   # £1.63 -> 1.63 pounds
    (r"\bkWh\b", "kilowatt hours"),                 # "13.5 kWh" and "per kWh"
    (r"\bMPG\b", "miles per gallon"),
    (r"(\d)\s?kg\b", r"\1 kilograms"),              # 65kg
    (r"(\d)\s?km\b", r"\1 kilometres"),             # 4km
    (r"(\d)p\b", r"\1 pence"),                       # 25p, 167.14p
    (r"\s*÷\s*", " divided by "),
    (r"\s*×\s*", " times "),
    (r"\s*=\s*", " equals "),
]


def apply_units(text):
    for pattern, repl in UNIT_RULES:
        text = re.sub(pattern, repl, text)
    return text


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


def ensure_stop(text):
    """Guarantee terminal punctuation. StackVox pauses on punctuation, not on
    line breaks, so a title / heading / bullet fragment with no full stop runs
    straight into the next sentence. A trailing '.' gives it the missing pause."""
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
    line = re.sub(r"(?<=\d),(?=\d)", "", line)               # thousands sep: 1,198.9 -> 1198.9
    line = line.replace("→", " to ")                        # arrows
    # A dash used as punctuation (spaced hyphen, or em/en dash) rushes in Kokoro;
    # an ellipsis gives it the longest natural pause. In-word hyphens are left alone.
    line = re.sub(r"\s*[—–]\s*", " ... ", line)             # em / en dash
    line = re.sub(r"\s+--?\s+", " ... ", line)              # spaced ASCII hyphen(s)
    line = re.sub(r"(\w)\s*\(", r"\1, (", line)             # comma pause before "("
    line = apply_pronunciations(line)                       # spoken-form library
    line = apply_units(line)                                # units & math symbols
    # Decimal point -> the word "point" (a bare "." between digits can be read as a
    # full stop). Integer part stays a number, fractional digits are read one by one:
    # 1198.9 -> "1198 point 9", 770.72 -> "770 point 7 2".
    line = re.sub(r"(\d+)\.(\d+)",
                  lambda m: m.group(1) + " point " + " ".join(m.group(2)), line)
    line = re.sub(r"[ \t]{2,}", " ", line)
    return line.strip()


def clean(body):
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)  # fenced code
    paragraphs, current = [], []
    for raw in body.splitlines():
        # Audio-only override: <!-- say: ... --> injects a spoken sentence that is
        # invisible on the page. Use it to narrate content that reads badly aloud
        # (a table, a code block). The text runs through the normal cleaner, so
        # units/decimals work: "<!-- say: it cost £192.68 -->" -> "...192 point 6 8 pounds".
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
        # horizontal rules, and full Markdown table rows (pipes read badly aloud;
        # the figures are already in the prose) -> drop, break the paragraph
        row = raw.strip()
        is_table_row = row.startswith("|") and row.endswith("|")
        if is_table_row or re.fullmatch(r"\s*([-*_]\s*){3,}", raw) or re.fullmatch(r"\s*\|?[ :|-]+\|?\s*", raw):
            if current:
                paragraphs.append(" ".join(current)); current = []
            continue
        is_heading = re.match(r"^\s{0,3}#{1,6}\s+", raw)    # ## Heading
        is_item = re.match(r"^\s*([-*+]|\d+\.)\s+", raw)    # list item?
        stripped = strip_inline(raw)
        if is_heading:                                       # heading stands alone -> a pause
            if current:
                paragraphs.append(" ".join(current)); current = []
            if stripped:
                paragraphs.append(stripped)
            continue
        if is_item:                                          # each item stands alone -> a pause
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


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: read-aloud.py path/to/post.md")
    title, body = split_front_matter(load(sys.argv[1]))
    # The title is emitted on line 1 so generate-audio.sh can splice a real
    # silent beat after it (line breaks alone produce no gap in StackVox).
    lines = [ensure_stop(title)] if title else []
    lines += [ensure_stop(p) for p in clean(body)]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
