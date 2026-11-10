# Validation snapshot — 2026-11-10

The local reference environment was Windows with Python 3.12.3, Playwright 1.58.0 and Chromium 145.0.7632.6. All 43 automated tests passed, including actual source-versus-export pixel comparisons, original photo pixel preservation, white-interior protection, revision/provenance checks, and Windows directory-junction archive containment.

Both the SVG rocket and NASA photo examples passed 13 playback/resource checks in offline Chromium using `file://`. Each run captured start, middle and final on light, dark and checkerboard backgrounds, plus a transparent final screenshot. A model reviewed those captures against the source. The photo uses disclosed approximate contours and a circular mask; the original RGB pixels are retained. See the [source attribution and limitations](../examples/source/ATTRIBUTION.md).

- [SVG verification snapshot](validation/svg-verification.json)
- [Photo verification snapshot](validation/photo-verification.json)
- [Independent Agent evaluation](validation/agent-evaluation.json)

The independent Agent followed the Skill's instructions to create an animation, then followed a natural-language request to draw the window last and remove two stars. Both revisions passed browser checks. Pixel comparisons showed changes confined to the requested stars in the final frame; the original source and previous revision were preserved.

These are dated records, not a claim that later changes or every Agent host have been tested. The JSON reports identify the exact HTML hashes; screenshot names in them refer to the corresponding verification output directories. The distributable example evidence is attached to [GitHub Releases](https://github.com/JulyanXu/typebit/releases). Live Windows/macOS/Linux CI results are available in [Actions](https://github.com/JulyanXu/typebit/actions). Claude Code has documented installation instructions but has not been interactively tested in this session.

## 中文说明

2026-11-10 已在 Windows 的 Python 3.12.3 与 Chromium 145 环境完成 43 项测试，并对 SVG 与真实照片示例分别执行 13 项离线播放检查。独立 Agent 完成了首次制作和自然语言修改流程；原图、白色细节和历史版本得到保留。以上是绑定具体 HTML 哈希的验证记录，不代表任意素材或所有 Agent 平台均已实测。照片的近似轮廓和圆形蒙版限制已在素材说明中披露。
