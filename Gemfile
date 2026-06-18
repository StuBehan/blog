source "https://rubygems.org"

# Jekyll — static site generator. Using the latest 4.x (built via GitHub
# Actions), not GitHub's older native-build version, so we get full plugin
# freedom.
gem "jekyll", "~> 4.3"

# Theme. minima is the clean, well-maintained default Jekyll blog theme.
gem "minima", "~> 2.5"

# Plugins run as part of the Jekyll build.
group :jekyll_plugins do
  gem "jekyll-feed", "~> 0.17"   # Atom feed at /feed.xml
  gem "jekyll-seo-tag", "~> 2.8" # <meta> tags for SEO / social cards
  gem "jekyll-sitemap", "~> 1.4" # sitemap.xml for search engines
end

# `webrick` was removed from Ruby's stdlib in 3.0; needed for `jekyll serve`.
gem "webrick", "~> 1.8"

# These were demoted from default gems in Ruby 3.4 — pin them so Jekyll's
# transitive requires don't warn or fail.
gem "csv", "~> 3.3"
gem "base64", "~> 0.2"
gem "logger", "~> 1.6"
