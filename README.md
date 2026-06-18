# Stuart's Blog

A [Jekyll](https://jekyllrb.com) blog hosted on GitHub Pages, built and
deployed automatically via GitHub Actions.

**Live site:** https://stubehan.github.io/blog/

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
date: 2026-06-17
---

Your content in Markdown.
```

Commit and push to `main` — the [Pages workflow](.github/workflows/pages.yml)
rebuilds and deploys within a minute or so.

## Structure

| Path | What it is |
|------|------------|
| `_config.yml` | Site settings (title, theme, plugins) |
| `_posts/` | Blog posts |
| `index.md` | Home page (lists posts) |
| `about.md` | About page |
| `.github/workflows/pages.yml` | Build + deploy automation |
