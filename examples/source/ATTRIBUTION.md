# Example sources and attribution

## TypeBit mark

`typebit-mark.svg` was created for this repository and is covered by the repository's MIT license.

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
