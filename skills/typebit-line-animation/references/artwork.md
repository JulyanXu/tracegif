# Artwork preparation

## Preserve the source

Keep the original source file and its hash in the project. Work in the original coordinate system, retaining aspect ratio and placement. Do not replace a photograph, logo, or text region with generated artwork and describe it as unchanged.

For raster artwork, keep original color pixels in the final image layer. A host-created mask determines alpha; contours determine the drawing effect. This separation allows the final reveal to preserve original color and detail while using simplified animation paths.

## Choose a method

| Source | Preferred approach | Disclosure |
| --- | --- | --- |
| SVG with usable paths | Reuse original geometry and group it semantically | Note unsupported elements or any conversions. |
| Raster logo | Host-assisted contours plus original-color reveal | Identify approximate tracing and raster reveal. |
| Line art | Sparse useful contours; avoid tracing both edges of every thick stroke when that makes the result noisy | Do not claim recovered original pen order. |
| Photograph | Main subject mask, simplified structural contours, localized detail reveal | Describe it as approximate contours with an original-image reveal, not a fully reconstructed vector photo. |

The raster preparation helper packages supplied paths and pixels; it does not automatically trace the image. The Agent must create or obtain the contours through its existing capabilities, distinguish lettering from texture, and arrange the intended drawing order. `--kind auto` uses only a palette heuristic for raster files, so the Agent should inspect the image and supply the correct kind explicitly.

Expand every visible SVG `<use>` instance into ordinary geometry before preparation. This applies even when the same SVG also contains direct paths; a mixed file is not exempt. References inside definitions can remain when supported, but they do not become drawable timeline layers.

## Masks and white backgrounds

Use an image mask aligned to the source dimensions after EXIF orientation correction. Prefer an 8-bit grayscale mask: white keeps source pixels, black removes them, and gray gives partial alpha. An image with a non-opaque alpha channel uses that channel instead. The mask multiplies the source alpha. Keep its coordinate mapping exact; a shifted mask causes halos or cuts into the subject.

For a simple white background, the connected-border removal option can help. Inspect white subject parts connected to the border, enclosed lettering, antialiased edges, highlights, and internal negative space. Use a host-produced mask for complex backgrounds. Never remove all near-white pixels indiscriminately.

If the host's image tool returns a regenerated cutout, check whether it preserves the source geometry. When it provides a usable alpha mask, apply that mask to the original pixels. Do not use altered lettering or reconstructed textures as evidence of source fidelity.

If a mask is approximate, say so. If no useful mask can be produced, explain that the transparent-subject requirement remains incomplete and preserve the current project. A transparent rectangle around an opaque full photograph is not subject isolation.

## Contours and typography

Keep contour paths in the same coordinate space as the source and use stable element IDs. For raster inputs, the contour SVG must use `viewBox="0 0 WIDTH HEIGHT"` matching the orientation-corrected source dimensions. Let the Agent assign meaningful phases: main structure, secondary outlines, and lettering/details. Avoid dense texture and shadow edges on photos. Contour simplification should not move the subject or change its silhouette.

Preserve existing text as paths or original raster pixels whenever possible. Live SVG text requires the correct redistributable font embedded with `--font PATH --font-family NAME`; the single supplied font applies to all live text. Live text appears during the final image reveal; outline it to animate the letter strokes. Outline mixed-font artwork instead of forcing it into one font. An unavailable font is an unresolved fidelity issue, not permission to choose a similar font. Do not OCR and retype logo lettering to claim exact letterform preservation.

Brand-blue doodles belong behind the subject. Keep them sparse, preserve readability, and treat preview backgrounds as inspection surfaces rather than artwork fills.
