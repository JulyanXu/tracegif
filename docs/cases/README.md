# 🎬 TraceGIF — ten scenes, one real player

**Press play. Change the speed. Export your own GIF.** The [interactive showcase](https://julyanxu.github.io/tracegif/) runs the actual exported HTML player, with pause, replay, scrubbing and HTML / GIF / PNG export. It is not a video, GIF loop or screenshot of an interface.

[▶ Open the live showcase](https://julyanxu.github.io/tracegif/) · [Install the Skill](../../README.md#install-the-skill) · [中文案例](#中文案例)

GitHub Markdown cannot execute the player. The links below open the playable GitHub Pages version; download an individual HTML to use the same player offline. Every scene waits for you to start it.

## ✨ Three richer scene studies

| Scene | What unfolds | Play and download |
| --- | --- | --- |
| 🌙 **Night Market** · 169 paths | A layered skyline, three shops, windows, striped awnings, ten lanterns, food counters, visitors and a bicycle. | [Play](https://julyanxu.github.io/tracegif/?scene=night-market) · [HTML](https://julyanxu.github.io/tracegif/cases/night-market/animation.html) · [GIF](night-market/animation.gif) · [PNG](night-market/final.png) · [Editable project](https://julyanxu.github.io/tracegif/cases/night-market/project.zip) |
| 📷 **Camera Exploded** · 123 paths | Separated optical elements, aperture, sensor board and camera body, followed by grip texture, contacts, fasteners and callout leaders. | [Play](https://julyanxu.github.io/tracegif/?scene=camera-exploded) · [HTML](https://julyanxu.github.io/tracegif/cases/camera-exploded/animation.html) · [GIF](camera-exploded/animation.gif) · [PNG](camera-exploded/final.png) · [Editable project](https://julyanxu.github.io/tracegif/cases/camera-exploded/project.zip) |
| 🌿 **Greenhouse Study** · 147 paths | Curved glazing and structural ribs, tiered benches, sixteen individually editable plants, pots, irrigation and garden tools. | [Play](https://julyanxu.github.io/tracegif/?scene=greenhouse-study) · [HTML](https://julyanxu.github.io/tracegif/cases/greenhouse-study/animation.html) · [GIF](greenhouse-study/animation.gif) · [PNG](greenhouse-study/final.png) · [Editable project](https://julyanxu.github.io/tracegif/cases/greenhouse-study/project.zip) |

These scenes use 960 × 640 source canvases and 10-second timelines at a default 1.5× speed. Their GIF downloads use a solid light matte and include an end hold. HTML and PNG preserve transparency outside the authored artwork. The night sky and greenhouse glass are part of their original illustrations.

**Try a revision:** “Give the lanterns more drawing time,” “Draw the lenses before the camera body,” or “Keep the foreground plants until the end.” The Agent can revise those existing layers without recreating the whole scene.

## 🧭 Seven more everyday scenarios

| Scene | A useful place to start | Open the actual player |
| --- | --- | --- |
| 🌱 Leaf Studio | A botanical identity for a brand introduction or presentation | [Play](https://julyanxu.github.io/tracegif/?scene=leaf-studio) · [HTML](https://julyanxu.github.io/tracegif/cases/leaf-studio/animation.html) |
| ☕ Coffee Story | A product illustration for a launch, menu or README | [Play](https://julyanxu.github.io/tracegif/?scene=coffee-story) · [HTML](https://julyanxu.github.io/tracegif/cases/coffee-story/animation.html) |
| 🔤 White Letter Badge | A raster logo that retains white lettering and transparent margins | [Play](https://julyanxu.github.io/tracegif/?scene=white-letter-badge) · [HTML](https://julyanxu.github.io/tracegif/cases/white-letter-badge/animation.html) |
| 🏡 Courtyard House | An architectural facade for a property concept or portfolio | [Play](https://julyanxu.github.io/tracegif/?scene=courtyard-house) · [HTML](https://julyanxu.github.io/tracegif/cases/courtyard-house/animation.html) |
| 🗺️ City Route | A fictional itinerary and numbered walking-route stops | [Play](https://julyanxu.github.io/tracegif/?scene=city-route) · [HTML](https://julyanxu.github.io/tracegif/cases/city-route/animation.html) |
| 🪐 Orbit Lesson | An educational schematic, visibly marked NOT TO SCALE | [Play](https://julyanxu.github.io/tracegif/?scene=orbit-lesson) · [HTML](https://julyanxu.github.io/tracegif/cases/orbit-lesson/animation.html) |
| 🎈 Celebration Card | A portrait invitation with native path lettering | [Play](https://julyanxu.github.io/tracegif/?scene=celebration-card) · [HTML](https://julyanxu.github.io/tracegif/cases/celebration-card/animation.html) |

[Download the original seven editable cases (v0.4.0)](https://github.com/JulyanXu/tracegif/releases/download/v0.4.0/tracegif-cases-0.4.0.zip). The three new scene projects are available individually in the table above; they are not in that older release bundle.

## 🔍 Inspect the evidence

Each case folder includes its original source, GIF, transparent final PNG, source → drawing → finish comparison, export settings and report bound to the checked HTML's SHA-256. Those comparison images are review evidence; the showcase itself uses live HTML.

| New scene | Source | Browser comparison | Verification |
| --- | --- | --- | --- |
| Night Market | [SVG](../../examples/source/night-market.svg) | [Three actual frames](night-market/preview.png) | [Report](night-market/report.json) |
| Camera Exploded | [SVG](../../examples/source/camera-exploded.svg) | [Three actual frames](camera-exploded/preview.png) | [Report](camera-exploded/report.json) |
| Greenhouse Study | [SVG](../../examples/source/greenhouse-study.svg) | [Three actual frames](greenhouse-study/preview.png) | [Report](greenhouse-study/report.json) |

All ten designs are original MIT-licensed demonstrations, not customer work or claims of marketing results. The city and buildings are fictional. The camera is an illustrative anatomy, not a repair guide; the greenhouse is not a construction or plant identification plan. The white-letter case uses supplied, aligned contours from its known source SVG, and does not claim automatic vector recovery from any image. See [attribution and limitations](../../examples/source/ATTRIBUTION.md).

To reproduce all ten cases after [installing the dependencies](../../README.md#install-the-skill):

```text
python tools/build_cases.py --build-root build/cases --media-root build/cases/media
```

This produces fresh HTML, GIF, PNG, editable packages and actual offline browser checks. Automated rebuilding leaves visual review unverified until a person or Agent inspects the new captures.

## 中文案例

**🎬 宣传页就是实际播放器：**[打开在线体验](https://julyanxu.github.io/tracegif/)，直接播放、暂停、拖动进度、调速，或通过 **GIF settings** 修改尺寸、帧率与背景，再保存 GIF。下载 HTML 后，同一套功能可以离线使用。页面初始等待点击，不自动播放。

新增三个更复杂的场景：**🌙 城市夜市全景（169 条路径）**、**📷 相机拆解示意（123 条路径）**、**🌿 温室生态剖面（147 条路径）**。加上植物品牌、咖啡产品、白字徽章、建筑展示、旅行路线、轨道教学和活动邀请，共十种场景。新案例的可编辑工程可在上表分别下载；v0.4.0 的历史案例包仍包含原先七个。

可以直接告诉 Agent：“灯笼画慢一些”“先画镜片，后画机身”“前景植物晚点出现，再导出 720 像素宽的 GIF”。它会在已有工程上调整对应图层和时间安排。保留原始交付 ZIP，并在副本中修改，便于回到上一版。

所有素材均为本项目原创演示并采用 MIT 许可，不包含用户上传的私人图片。GIF 使用实色背景；HTML 与 PNG 保留作品外部的透明度。夜市天空与温室玻璃属于原始画面内容。页面中的实际播放与报告里的自动检查、人工视觉复核分别记录，不能把一项通过当作其他项也已验证。
