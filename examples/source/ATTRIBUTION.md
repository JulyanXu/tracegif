# Example sources and attribution

## TypeBit mark

`typebit-mark.svg` was created for this repository and is covered by the repository's MIT license.

## Original marketing cases

`leaf-studio.svg`, `coffee-story.svg` and `white-letter-badge.svg` were authored specifically for TypeBit and are covered by this repository's MIT license. They are fictional demonstration artwork, not customer work or third-party brands. No commercial fonts are included: the badge's TB lettering consists of original path geometry.

`white-letter-badge.png` is a transparent Chromium rendering of the authored badge SVG. Its animation uses the same known SVG geometry as supplied contours, then reveals the original PNG pixels. This is a controlled demonstration of white-letter and alpha preservation, not a claim of automatic vector recovery or background removal. Regenerate the PNG with `python tools/build_cases.py --refresh-raster` and choose a fresh `--build-root` if the source changes.

The reproducible cases are defined in `examples/cases.json`. Run `python tools/build_cases.py` to rebuild their offline HTML, browser verification, GIF/PNG exports and editable packages. Preview backgrounds are inspection mattes; the original SVG/PNG and HTML backgrounds remain transparent.

新增的植物标识、咖啡插画与白字徽章均为 TypeBit 原创演示素材，采用 MIT 许可，不代表真实客户案例。白字徽章的 PNG 来自随附 SVG，动画使用已知原始路径；它展示白字和透明度保留，不宣称从任意图片自动恢复精确矢量。

## Apollo 17 Blue Marble

- **File:** `blue-marble.jpg` (1041 × 1041 pixels).
- **Credit:** NASA / Apollo 17 crew.
- **Source article:** [Apollo 17: Blue Marble](https://www.nasa.gov/image-article/apollo-17-blue-marble/).
- **Downloaded image:** [NASA image AS17-148-22727](https://www.nasa.gov/wp-content/uploads/2023/03/as17-148-22727_lrg.jpg).
- **Use guidance:** [NASA Images and Media Usage Guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/).

This photograph is used as a factual example of source-preserving image processing. NASA states that its content generally is not subject to copyright in the United States and allows factual use consistent with its guidelines, with attribution and without implied endorsement. The image is not relicensed under TypeBit's MIT license. NASA and the Apollo 17 crew do not endorse TypeBit.

`blue-marble-contours.svg` was authored by the host Agent after viewing the photograph. It contains an approximate globe boundary and simplified outlines of Africa and Madagascar. These are illustrative contours, not scientific coastlines, recovered photographic vectors, or evidence of automatic segmentation.

`blue-marble-mask.png` is an approximate circular grayscale mask centered at (520, 520) with radius 491 pixels and a one-pixel alpha transition. It is specific to this image; it can trim the atmospheric edge slightly. Reproduce it with `python examples/source/create_blue_marble_mask.py`. The script draws a known circle and does not classify or segment arbitrary photographs.

The generated animation combines these contours with the original decoded RGB pixels under that mask. It omits most cloud and terrain detail from the drawing stage, then reveals the photograph. The mask, contour SVG, and reproduction script are original TypeBit example files covered by MIT. Keep this attribution with redistributions of the photograph or its example project.

## 中文说明

`blue-marble.jpg` 来自 NASA 的阿波罗 17 号“蓝色弹珠”照片，署名 **NASA / Apollo 17 crew**。依据上述 NASA 媒体使用指南，用于展示保留原图像素的处理方式；照片不改用本仓库 MIT 许可，也不表示 NASA 或宇航员为 TypeBit 背书。

轮廓由宿主 Agent 实际看图后编写，仅近似表现地球外缘、非洲与马达加斯加。圆形蒙版只适用于这张照片，可能略微裁掉大气边缘；它不是通用自动抠图。动画描线阶段省略大多数云层和地表细节，最后显露蒙版下的原图。分发照片或示例工程时请保留本说明。

## TraceGIF scenario illustrations

`courtyard-house.svg`, `city-route.svg`, `orbit-lesson.svg` and `celebration-card.svg` are original artwork authored for TraceGIF and covered by this repository's MIT license. The house, itinerary and invitation are fictional demonstrations, not client work, a real property listing, navigation data or a scheduled event. Every visible letter and numeral is native path geometry; no external font is included.

The orbital lesson is visibly labeled **NOT TO SCALE**. Its planet sizes, distances, arrangement and orbital shapes are illustrative, not a physical simulation, measured astronomical diagram or ephemeris. The same limitation travels with its editable project and case record.

庭院住宅、城市路线、轨道课堂与庆典邀请卡均为 TraceGIF 原创 MIT 示例。房屋、地图与活动均为虚构，不代表客户案例、真实房源、导航信息或已安排的活动；字母与数字均为原生路径，不含外部字体。轨道课堂明确标注“不按比例”，仅用于示意，不构成天文数据或物理模拟。
