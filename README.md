# behan.codes

The personal blog of **Stu Behan** — a [Jekyll](https://jekyllrb.com) site hosted on
GitHub Pages, built and deployed automatically via GitHub Actions.

**Live site:** https://behan.codes

## Local development

```bash
bundle install                       # first time only
bundle exec jekyll serve --livereload
```

Open <http://localhost:4000>.

## Writing a post

Create `_posts/YYYY-MM-DD-title.md`:

```markdown
---
layout: post
title: "My Post Title"
date: 2026-06-17 19:00:00 +0000
categories: some-category
---

Your content in Markdown.
```

Commit and push to `main` — the [Pages workflow](.github/workflows/pages.yml)
rebuilds and deploys within a minute or so.

> **Heads-up:** a post dated in the *future* is skipped at build time (Jekyll's
> `future: false` default). Make sure the deploy runs *after* the post's
> timestamp, or it won't appear.

## Read-aloud narration

Any post or page can carry a "Read aloud with StackVox" audio player. It renders
automatically whenever a matching MP3 exists at `assets/audio/<slug>.mp3` — no
file, no player.

Generate one with [StackVox](https://github.com/StackOneHQ/stackvox) **0.7.0+**
(bundled with the Stack Nudge app, or `pipx install stackvox`) plus `ffmpeg`:

```bash
tools/generate-audio.sh _posts/2026-07-02-my-post.md   # or: tools/generate-audio.sh about.md
STACKVOX_VOICE=bm_george tools/generate-audio.sh …     # override the default voice (af_aoede)
```

StackVox's `normalize` command does the Markdown → speech transform — expanding
units and numbers (`£1.63` → "1 point 6 3 pounds", `25p` → "25 pence"), shaping
pauses, dropping tables, and applying the blog's pronunciation dictionary in
`tools/pronunciations.json` (e.g. `agy → antigravity`, `Redis → Reddiss`). Add a
term to that JSON whenever a word comes out wrong.

`tools/read-aloud.py` handles the two things StackVox can't know about: it strips
the front matter (emitting the title first, so a silent beat can be spliced after
it) and expands the audio-only directive — a line that is spoken but never shown
on the page:

```markdown
<!-- say: a sentence that is spoken but never shown on the page -->
```

If the StackVox on the machine predates `normalize` (< 0.7.0), the script falls
back to `read-aloud.py --legacy`, a self-contained cleaner, so generation still
works.

The audio does **not** regenerate itself — re-run the script after editing a
post's prose, or the narration drifts from the text.

## Structure

| Path | What it is |
|------|------------|
| `_config.yml` | Site settings (title, theme, plugins) |
| `_posts/` | Blog posts |
| `_layouts/` | `post` / `page` / `default` layout overrides |
| `_includes/` | Partials — sidebar, footer, the read-aloud player |
| `assets/` | `main.scss` (dark purple skin) + `audio/` narration MP3s |
| `tools/` | `generate-audio.sh`, `read-aloud.py`, `pronunciations.json` (narration pipeline) |
| `index.md` | Home page (lists posts) |
| `about.md` | About page |
| `.github/workflows/pages.yml` | Build + deploy automation |
