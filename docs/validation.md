# Validation snapshots — 2026-11-10

## v0.2.0

The updated local suite passed all **63 tests** on Windows with Python 3.12.3, Playwright 1.58.0 and Chromium 145.0.7632.6. New coverage includes speed continuity, native scrubber keys, downloaded HTML reopening idle at the chosen speed, PNG pixel/alpha preservation, GIF timing/matte, safe configuration updates and revision archive containment.

The public SVG example passed **15 offline playback/resource checks**. An independent Agent prepared a 6-second project at 1.5×, exported HTML/PNG/GIF, then changed it to 2× and repeated verification/export/package. Original source, SVG scene, layer schedule and final PNG were unchanged. The final GIF loop is 3.8 seconds, including its 0.8-second hold.

- [v0.2.0 SVG browser report](validation/v0.2.0-svg-verification.json)
- [v0.2.0 independent workflow evidence](validation/v0.2.0-workflow.json)

These local reports are bound to their recorded HTML hashes. Release attachments carry their own fresh CI-generated reports; automated CI does not claim model visual review.

中文：v0.2.0在本机通过63项测试、15项离线播放检查，并由独立Agent走通制作、调整速度、重新导出与归档流程。跨平台检查以GitHub Actions的实际结果为准。

## v0.1.0 (historical)

The local reference environment was Windows with Python 3.12.3, Playwright 1.58.0 and Chromium 145.0.7632.6. All 43 automated tests passed, including actual source-versus-export pixel comparisons, original photo pixel preservation, white-interior protection, revision/provenance checks, and Windows directory-junction archive containment.

Both the SVG rocket and NASA photo examples passed 13 playback/resource checks in offline Chromium using `file://`. Each run captured start, middle and final on light, dark and checkerboard backgrounds, plus a transparent final screenshot. A model reviewed those captures against the source. The photo uses disclosed approximate contours and a circular mask; the original RGB pixels are retained. See the [source attribution and limitations](../examples/source/ATTRIBUTION.md).

- [SVG verification snapshot](validation/svg-verification.json)
- [Photo verification snapshot](validation/photo-verification.json)
- [Independent Agent evaluation](validation/agent-evaluation.json)

The independent Agent followed the Skill's instructions to create an animation, then followed a natural-language request to draw the window last and remove two stars. Both revisions passed browser checks. Pixel comparisons showed changes confined to the requested stars in the final frame; the original source and previous revision were preserved.

These are dated records, not a claim that later changes or every Agent host have been tested. The JSON reports identify the exact HTML hashes; screenshot names in them refer to the corresponding verification output directories. The distributable example evidence is attached to [GitHub Releases](https://github.com/JulyanXu/typebit/releases). Live Windows/macOS/Linux CI results are available in [Actions](https://github.com/JulyanXu/typebit/actions). Claude Code has documented installation instructions but has not been interactively tested in this session.

## 中文说明

2026-11-10 已在 Windows 的 Python 3.12.3 与 Chromium 145 环境完成 43 项测试，并对 SVG 与真实照片示例分别执行 13 项离线播放检查。独立 Agent 完成了首次制作和自然语言修改流程；原图、白色细节和历史版本得到保留。以上是绑定具体 HTML 哈希的验证记录，不代表任意素材或所有 Agent 平台均已实测。照片的近似轮廓和圆形蒙版限制已在素材说明中披露。
