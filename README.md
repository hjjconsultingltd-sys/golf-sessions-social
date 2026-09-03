# Golf Sessions social graphics

Brand-exact PNGs for the Golf Sessions LinkedIn page and @golf.sessions, rendered by GitHub Actions. Nothing in this repo depends on Base44.

## How it works

1. A spec file lands in `specs/` (one JSON object, or a list of objects for a carousel). Each object has an `id`, a `template`, a `size` and `fields`. The scheduled Cowork run writes it through Zapier's GitHub "Create or Update File" action.
2. The push triggers `.github/workflows/render.yml`. It installs Playwright's Chromium, fetches the brand fonts from google/fonts (Big Shoulders Display, Instrument Sans instanced at 400/500/600), renders every spec whose hash is not in `out/manifest.json`, and commits the PNGs to `out/` with `[skip ci]`.
3. The PNG is then public at `https://raw.githubusercontent.com/hjjconsultingltd-sys/golf-sessions-social/main/out/<id>.png` and LinkedIn and Instagram fetch it from there. The repo has to be public for that URL to work without a token.

Re-render everything: Actions, Render social graphics, Run workflow, tick force. Change a spec and push: only that graphic re-renders.

Zapier's GitHub token cannot write under `.github/` (no workflow scope), so the workflow file was committed as `workflow/render.yml` and moved into `.github/workflows/render.yml` by hand. Edit it there.

## Templates

`statement`, `numeral`, `match`, `testimonial`, `cover`, `carousel`, `photo`. Sizes: `portrait` 1080x1350, `square` 1080x1080, `story` 1080x1920, `linkedin_cover` 1584x396, `og` 1200x630. The `photo` template takes `photo` (a filename in `photos/`, or a public URL), `crop` (`top|centre|bottom`) and renders the picture desaturated with a scrim into ink, type below it. Photographs are committed to `photos/` by hand (binary files do not survive Zapier's GitHub action).

## Local

```
pip install -r requirements.txt && python -m playwright install chromium
python render.py --fonts
python render.py --demo          # one of everything
python render.py specs/w2-04.json
```

Brand rules are enforced in `render.py`, not left to chance: monochrome only (team colours only on `match`), radius 0, no shadows, halves as the half glyph, hairlines 1px, 34/66 split.
