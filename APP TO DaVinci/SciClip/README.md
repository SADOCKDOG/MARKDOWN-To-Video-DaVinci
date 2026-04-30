# SciClip Pro v2

Streamlit app to search science-friendly video and image sources (royalty-free / CC / public domain) across Pexels, Pixabay, NASA, Wikimedia, Unsplash, and more. Results are grouped by source with inline playback/previews and one-click downloads.

## Features
- Parallel search across 20+ curated science-friendly sources
- Per-source grouping with collapsible sections for videos/images
- License/usage cues and source badges
- Download helpers with fallback handling for NASA assets
- Secrets-first config via `.streamlit/secrets.toml`

## Quick Start
1) Install deps (recommend venv):
```bash
pip install -r requirements.txt
```
2) Add secrets at `.streamlit/secrets.toml` (example below). Do **not** commit real keys.
3) Run:
```bash
streamlit run app.py
```

## secrets.toml example
```toml
PEXELS_API_KEY = "your_pexels_key"
PIXABAY_API_KEY = "your_pixabay_key"
NASA_API_KEY = "DEMO_KEY"          # or your real key
UNSPLASH_ACCESS_KEY = "your_unsplash_access_key"
UNSPLASH_SECRET_KEY = "your_unsplash_secret_key"
FLICKR_API_KEY = ""                # leave blank if not using Flickr
```

## Notes
- Flickr can stay blank; Unsplash uses only the access key for current flows.
- Downloads set a UA header and include NASA fallbacks (`~orig` → `~large` → `~medium` → `~thumb`).
- If you change sources, update `SOURCES`, `VIDEO_FUNCS`, and `IMAGE_FUNCS` in `app.py`.

## Contributing / Git basics
If this folder is not yet a repo:
```bash
git init
git add .
git commit -m "chore: initial commit"
```
If it already is, typical flow:
```bash
git status
git add .
git commit -m "feat: refine UI panes"   # adjust message
```
Push (replace origin if not set):
```bash
git remote add origin <your-repo-url>  # only once
git push -u origin main                 # or master
```

## License / Content
This app helps you find assets; always verify licenses on the source site before publishing. For CC-BY content, include attribution as required.
