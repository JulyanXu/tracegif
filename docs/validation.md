# Validation snapshots

## Live showcase — 2026-11-11

The live homepage uses the actual standalone player in an iframe. **109 local tests passed** on Windows, including eight new site and artifact-integrity checks. The browser scenarios cover playback, pause, speed, scrubbing, English/Chinese scene links, mobile controls, real PNG/GIF downloads, downloadable HTML reopened offline, and recovery when the gallery or a scene fails to load.

The embedded layout reserves room for the native toolbar so it does not obscure the artwork. This layout stays on the homepage; the downloaded HTML is captured from the player's original document and remains self-contained. A real download test checks that separation.

The three new scenes — Night Market (169 paths), Camera Exploded (123), and Greenhouse Study (147) — each passed 15 offline checks. Source and final comparison panels match pixel for pixel at 480 × 320. Their visual reviews and editable ZIPs are bound to the current HTML and asset checksums. The earlier seven case files remain unchanged.

- [Homepage browser report and source hashes](validation/live-showcase.json)
- [Complex-scene visual and GIF measurements](validation/complex-scenes.json)
- [Actual interactive homepage](https://julyanxu.github.io/tracegif/)
- [Deployment and maintenance](showcase.md)

The **Live showcase** workflow waits for repository checks on Windows, macOS and Linux before automatic publication, checks the exact passed commit again, and skips superseded commits. Local evidence identifies what was tested here; workflow results record the hosted checks separately.

中文：本机通过 109 项测试，包含 8 项首页与资源一致性检查。宣传页使用真实播放器，支持中英文、场景直达、倍速与实际格式下载；已修复工具栏遮挡画面，并验证下载的 HTML 可以独立离线播放。三个复杂案例各通过 15 项离线检查，原稿与终帧一致，可编辑 ZIP 与报告均绑定具体文件校验值。自动发布等待跨平台检查通过。

## v0.4.0 — 2026-11-11

The renamed TraceGIF runtime passed **101 local automated tests** in Windows, Python 3.12.3, Playwright 1.58.0 and Chromium 145.0.7632.6. These include real browser GIF downloads at selected sizes, frame rates and matte colors; exact white/black/matte retention; settings persistence in saved HTML; short-screen controls; and new/legacy command portability.

The audit added regression coverage for stale or missing export evidence, protected package destinations, atomic package replacement, empty/opaque masks, and keeping prior verification captures with their report on retries. The source/drawing/final comparison capture now tests landscape, square and portrait proportions in an actual browser.

All **seven original cases** were rebuilt with 0.4.0. Their browser checks, source comparisons, GIF timings, dimensions and visual reviews are bound to each current HTML in the [case records](cases/manifest.json). The new scenarios are a courtyard house, a fictional city route, an illustrative orbital lesson and a portrait invitation. GIF previews are actual captures, not simulated video.

- [v0.4.0 sample verification](validation/v0.4.0-svg-verification.json)
- [Independent upgrade and export workflow](validation/v0.4.0-workflow.json)
- [Migration notes and compatibility limits](migration.md)
- [Tagged release checks](https://github.com/JulyanXu/tracegif/actions/workflows/release.yml)

The installable folder and legacy entrypoints were exercised outside the repository. Archived v0.1.0, v0.2.0 and v0.3.0 projects were rendered with 0.4.0 while retaining source bytes and layer schedules. An extracted delivery ZIP lacks its private snapshot: retain that original ZIP before revision, as documented in the migration guide.

中文：TraceGIF v0.4.0 在本机通过 101 项自动测试，并重新生成七个案例。检查覆盖 GIF 参数、白色细节、短屏幕操作、工程包完整性、无效蒙版和验证记录归档；横版、方版、竖版比例通过真实浏览器对照。旧版本工程与旧命令入口已验证兼容。各案例视觉复核记录绑定其具体 HTML，不能替代对其他素材的检查。

## v0.3.0

All **83 local automated tests** passed in the reference environment.

The offline HTML now contains its own licensed GIF encoder. Seven focused tests exercise real Chromium downloads, decode the GIF bytes, check colors and selected-speed timing, and confirm cancellation, encoder-error recovery, playback-state restoration and GIF export from a downloaded HTML copy. These run in offline browser contexts and reject external resource requests.

Three [original public cases](https://github.com/JulyanXu/tracegif/blob/v0.3.0/docs/cases/README.md) each passed **15 offline playback/resource checks**. An Agent inspected the source/drawing/final strips, the three validation backgrounds and decoded GIF phases; the review notes and HTML hashes are recorded in each case's report. The controlled raster badge retains its original RGBA pixels, including white letters and transparent margins. The 480 × 360 case GIFs last 4.8 seconds including the final hold.

- [v0.3.0 SVG browser report](validation/v0.3.0-svg-verification.json)
- [v0.3.0 case records and exact artifact hashes](https://github.com/JulyanXu/tracegif/blob/v0.3.0/docs/cases/manifest.json)
- [Release and artifact checks](../tests/test_release.py)

The reference environment remains Windows, Python 3.12.3, Playwright 1.58.0 and Chromium 145.0.7632.6. The [release workflow](https://github.com/JulyanXu/typebit/actions/workflows/release.yml) reruns the suite on Windows, macOS and Linux before publishing. Its fresh case build records automated checks separately from visual review; CI does not inherit or claim an Agent's visual inspection of another build.

中文：v0.3.0 增加 7 项真实浏览器 GIF 下载检查，覆盖倍速、取消、恢复、错误处理与离线副本。三个原创案例各通过 15 项离线检查，并对原稿、描线、终帧、三种背景和 GIF 实际帧完成视觉复核。白字徽章保留原始 RGBA 像素。发布流程要求 Windows、macOS、Linux 检查全部通过；自动构建与 Agent 视觉判断分别记录。

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
