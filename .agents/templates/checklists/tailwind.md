## Tailwind CSS

### Styling & accessibility
- v4: custom `@keyframes` live inside `@layer base` and custom classes are `@utility` directives; unlayered custom CSS is tree-shaken silently (class present in the DOM, `animation-name: none` in computed style).
- `animate-in`, `fade-in`, `zoom-in-*`, `slide-in-*` do nothing without `tailwindcss-animate`; the plugin is confirmed in `package.json` before those classes are used.
- Tokens are defined once in `{{TOKEN_SOURCE_PATH}}` via `@theme`; no hex literal appears in a component.
- Light and dark classes are paired on the same element (`bg-card dark:bg-...`).
- Before theorizing about a variant, the stylesheet is searched for handwritten rules on the same element or a reused stale class name.
- Motion honors `prefers-reduced-motion` via `motion-reduce:` or a media query on every animated element.
- `ml-auto` is used instead of `justify-between` when the left child of a row may mount late.
- Mount and unmount animations use the component library's transition primitive; `transition-*` utilities alone do nothing on mount.

### Testing
- Motion is verified in the browser (computed `animationName`, keyframe present in `document.styleSheets`), not by asserting a class name.
- A visual or geometric test locks in layout invariants that hover or animation must not shift (header x, grid width).
