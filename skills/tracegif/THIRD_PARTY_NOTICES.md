# Third-party notices

TraceGIF's own code and documentation are licensed under the [MIT License](LICENSE). Dependencies retain their own licenses. The Python packages and Chromium are installed separately; TraceGIF's source distribution does not relicense or bundle their distributions.

| Component | Purpose | Upstream license |
| --- | --- | --- |
| [Pillow](https://github.com/python-pillow/Pillow) | Raster image decoding, alpha masks, image output | [MIT-CMU](https://github.com/python-pillow/Pillow/blob/main/LICENSE) |
| [defusedxml](https://github.com/tiran/defusedxml) | Safer XML parsing | [Python Software Foundation License 2](https://github.com/tiran/defusedxml/blob/main/LICENSE) |
| [Playwright for Python](https://github.com/microsoft/playwright-python) | Real-browser verification and screenshots | [Apache License 2.0](https://github.com/microsoft/playwright-python/blob/main/LICENSE) |
| [pyee](https://github.com/jfhbrook/pyee) | Playwright dependency | [MIT](https://github.com/jfhbrook/pyee/blob/main/LICENSE) |
| [greenlet](https://github.com/python-greenlet/greenlet) | Playwright dependency | [MIT and PSF-2.0](https://github.com/python-greenlet/greenlet/blob/master/LICENSE) |
| [typing_extensions](https://github.com/python/typing_extensions) | Runtime typing dependency | [PSF-2.0](https://github.com/python/typing_extensions/blob/main/LICENSE) |
| [Chromium](https://www.chromium.org/) | Browser installed by Playwright | [Chromium license](https://chromium.googlesource.com/chromium/src/+/main/LICENSE), plus its bundled third-party notices |
| [gifenc 1.0.3](https://github.com/mattdesl/gifenc) | Offline GIF encoding in the exported HTML toolbar | [MIT](assets/vendor/gifenc.LICENSE.md) |

Consult the notices shipped with the exact installed versions, including their transitive dependencies. Keep those notices if redistributing their files or browser binaries.

The pinned `gifenc` JavaScript release is vendored and embedded in exported HTML, including its complete upstream copyright and MIT notice. Its npm package integrity, source checksum, wrapper changes and bundled checksum are recorded in [gifenc.provenance.json](assets/vendor/gifenc.provenance.json). Browser GIF exports require no CDN, network request, Node.js installation or external worker file. The Python GIF helper continues to use Pillow.

The exported player uses TraceGIF's native SVG/JavaScript runtime. It does not include GSAP or a model runtime. TraceGIF does not distribute model weights, commercial fonts, or third-party brand artwork. User-provided images and fonts remain subject to their own rights; only embed fonts that may be redistributed with the artwork.

The example artwork created for this repository is covered by the repository's MIT license unless an adjacent attribution states otherwise. Agent hosts and any image tools used through them are separate services governed by their own terms.

The Blue Marble photograph in the source examples is credited to NASA / Apollo 17 crew and used under [NASA's media-use guidance](https://www.nasa.gov/nasa-brand-center/images-and-media/), not relicensed under MIT. Keep its [source attribution](https://github.com/JulyanXu/tracegif/blob/main/examples/source/ATTRIBUTION.md) with redistributed copies. The illustrative contour SVG and example-specific circular mask were created for TraceGIF. No NASA endorsement is implied.
