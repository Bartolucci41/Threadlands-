# Threadlands landmark drawings

One SVG per library place, named `<slug>.svg` (the slug from `data/index.json`). Explore shows it automatically as a faint, grey background mark behind the place name (about 20% opacity, edges faded), so it must read clearly in grayscale: strong silhouettes and clear contrast between the landmark and its setting matter more than color or small detail.

## The look

Warm daylight, flat shapes, soft and toy-like, readable at 300 px wide. Match `san-francisco.svg`, `mexico-city.svg`, `montreal.svg`, `bologna.svg` and `bangkok.svg`.

- Canvas: `viewBox="0 0 320 200"`, a rounded frame (rx 18) clipped with `<clipPath>`, a thin ink border at 12% opacity.
- Palette only: sky `#eef2e8`, water `#8fbcd4`, grass `#cfe0c3`, hills `#b9cfac`, terracotta `#c9775a`, gold `#d9b24a`, cream `#f2ece1`, sand `#e8dcc8`, foliage `#4f8a5b`, ink `#1d2b25`. A soft sun `#f3d58a` is optional.
- One landmark everyone in that city recognizes (a building, bridge, monument or natural feature), in front of a simple setting: river, coast, hills or skyline.
- No text, no logos, no official seals or coats of arms, no people.
- `role="img"` and an `aria-label` that says what it shows, such as "Illustration of the Two Towers of Bologna above its porticoes".
- Hand-written SVG, under 20 KB.
