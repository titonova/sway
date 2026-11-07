# HTML/CSS browser rendering

The agent writes editable HTML inside the active post `versions/vXXX/source/`. One HTML file becomes one PNG; multiple `slide_01.html`, `slide_02.html`, etc. become a carousel. Relative local fonts/images work; external network dependencies are blocked to preserve reproducible renders. JS, CSS and inline SVG are supported.

```bash
python -m tools.rendering.render_images --org northstar --post POST_ID --width 1080 --height 1350
```

PNG files appear in `versions/vXXX/output/`. **The coding agent must open each real rendered PNG and visually inspect it**, then revise the source and rerender. Maximum three autonomous revision rounds after the first render; these micro-adjustments stay in the same version.

Motion graphics use `source/video.html` and Chromium screenshot frames piped into FFmpeg/H.264. Use deterministic CSS animations or define `window.swayFrame(seconds)` in the page to explicitly update positions/time during rendering. The renderer produces MP4 and three preview PNGs. No invented photographs, actor footage or product recordings.

```bash
python -m tools.rendering.render_video --org ORG --post POST_ID --html video.html --width 1080 --height 1920 --fps 15 --duration 6
```

Optional `--audio sound.mp3` references an actual file INSIDE the post version's `source/`. Requires installed Chromium/Playwright and FFmpeg. Rendering a complex long video can be compute-intensive. The agent must inspect preview frames and actual animation/audio; correct malformed videos rather than declaring success based on a file existing.
