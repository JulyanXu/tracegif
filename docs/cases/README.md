# From still artwork to a drawn entrance

Three original examples you can inspect, download and revise. Each uses the same TypeBit workflow: preserve the source, draw meaningful contours, reveal color, then verify the exported file offline.

[Download all cases](https://github.com/JulyanXu/typebit/releases/download/v0.3.0/typebit-cases-0.3.0.zip) · [Install TypeBit](../../README.md#install-the-skill) · [中文说明](#中文案例)

The bundle contains an offline HTML, GIF, transparent PNG and editable project for each case. Open an HTML, choose a speed and click **Save GIF**. These are demonstrations created for TypeBit, not commissioned customer work or business-performance claims. All three source designs are available under MIT.

## Leaf Studio — a botanical identity

![Leaf Studio animation](leaf-studio/animation.gif)

![Leaf Studio source, drawing and final](leaf-studio/preview.png)

**Use:** introduce a small brand or a presentation section with a restrained botanical mark. The leaf structure draws first; its smaller contours and green/gold color follow. The editable source is native SVG, so no automatic tracing or font substitution is involved.

**Try this request:** “Make the main leaf appear more slowly, keep the smaller details late, then give me a GIF for my project README.”

[Original SVG](../../examples/source/leaf-studio.svg) · [HTML file](leaf-studio/animation.html) · [GIF](leaf-studio/animation.gif) · [Transparent PNG](leaf-studio/final.png) · [Verification](leaf-studio/report.json)

## Coffee Story — a product illustration

![Coffee Story animation](coffee-story/animation.gif)

![Coffee Story source, drawing and final](coffee-story/preview.png)

**Use:** a coffee product introduction or a compact visual in a pitch deck. The cup, steam and beans give the animation a recognizable subject before color appears. Original SVG paths remain editable rather than being flattened into a video.

**Try this request:** “Start with the cup, show the steam later, and export a faster GIF plus a transparent final PNG.”

[Original SVG](../../examples/source/coffee-story.svg) · [HTML file](coffee-story/animation.html) · [GIF](coffee-story/animation.gif) · [Transparent PNG](coffee-story/final.png) · [Verification](coffee-story/report.json)

## White Letter Badge — keep the white details

![White Letter Badge animation](white-letter-badge/animation.gif)

![White Letter Badge source, drawing and final](white-letter-badge/preview.png)

**Use:** a badge or logo whose white lettering must remain visible. This case starts from a transparent PNG rendered from an original SVG. The aligned contours are supplied from that known source; final color uses the PNG pixels. It demonstrates preserved white interiors, not a claim that any raster logo can be perfectly traced automatically.

**Try this request:** “Keep the white letters intact, draw their contours last, and save the result as HTML, GIF and PNG.”

[Source design](../../examples/source/white-letter-badge.svg) · [Input PNG](white-letter-badge/source.png) · [HTML file](white-letter-badge/animation.html) · [GIF](white-letter-badge/animation.gif) · [Transparent PNG](white-letter-badge/final.png) · [Verification](white-letter-badge/report.json)

## What to compare

- The GIFs use a solid background; the HTML and PNG outputs retain transparency.
- Every preview comes from the actual renderer. Reports identify the exact HTML that was checked.
- Changing playback speed does not regenerate the artwork. Changing the source or timeline requires a new render and verification.
- GitHub displays the source of an HTML file. Download it and open it locally to try the player; the case bundle is the simplest way to get every file.

Each example has a 6-second timeline and starts at 1.5×. Its GIF lasts 4.8 seconds including the final hold, at 480 × 360 and 10 fps. The gallery GIFs use a cream matte selected through the helper; the HTML's **Save GIF** button uses white.

After [installing the dependencies](../../README.md#install-the-skill), reproduce the cases from the repository root:

```text
python tools/build_cases.py --build-root build/cases --media-root build/cases/media
```

This creates fresh offline evidence and editable packages. Automated rebuilding leaves visual review marked unverified until a human or Agent inspects the new captures.

## 中文案例

**三个案例，三种使用场景：**植物标识用于品牌亮相，咖啡插画用于产品介绍，白字徽章用于验证内部白色细节的保留。素材均为 TypeBit 原创演示，并附 MIT 许可，不代表真实客户项目或营销转化成绩。

下载案例包后，打开 HTML，调节速度，点击 **Save GIF** 即可离线生成 GIF。每个案例同时提供原稿、描线与成品对照、透明 PNG、可编辑工程和绑定 HTML 校验值的报告。

可以直接说：“杯子先出现，蒸汽晚一点”“保留白字”“总时长改为 8 秒，再导出 GIF”。Agent 会在原工程上修改并保留此前版本。

GIF 使用实色背景，HTML 和 PNG 保留透明度。白字案例的轮廓来自已知的原始 SVG，并非自动恢复任意图片的精确矢量路径。

案例默认采用 6 秒时间线、1.5 倍速；GIF 为 480 × 360、10 fps，含末尾定格共 4.8 秒。案例页的 GIF 使用辅助脚本设置的奶油色背景，HTML 中的 Save GIF 使用白底。上面的命令可重新制作案例、导出全部格式并生成真实离线验证记录。
