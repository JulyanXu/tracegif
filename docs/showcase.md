# Live showcase

The [TraceGIF homepage](https://julyanxu.github.io/tracegif/) embeds the actual standalone HTML from `docs/cases/<scene>/animation.html`. The scene is rendered by the same SVG and JavaScript used in the downloadable artwork. No screenshot or prerecorded GIF substitutes for the interactive preview.

Visitors can play, pause, replay, scrub, choose speed and use the player's HTML, PNG and GIF downloads. These controls operate inside the selected scene. A scene's direct HTML link opens the complete player in a separate tab. The homepage itself needs HTTP hosting to load the case manifest; downloaded animation HTML remains fully offline.

## Update and verify

1. Author a redistributable source and add its metadata to `examples/cases.json`.
2. Generate the project and exports using `tools/build_cases.py`, then inspect the real source, drawing and final frames. Keep the visual review attached to the exact HTML hash.
3. Copy the checked artifacts into the scene's `docs/cases/` directory and update the case manifest. Preserve existing case bytes when adding a new scene.
4. Run `python tools/verify_site.py` for real-browser interaction checks, desktop/mobile captures and a report in `build/site-qa/`.
5. Push to `main`. The **Live showcase** workflow waits for **Checks** to pass, checks out that exact commit, runs the live-site tests and deploys `docs/` to GitHub Pages. A failed check prevents that automated deployment.

The **Live showcase** manual workflow is available for a deliberate redeployment and runs its own site checks. Hosting uses GitHub Pages with a custom Actions workflow; setup follows [GitHub's official workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

The original v0.4.0 release remains immutable and contains seven cases. The three newer detailed cases are distributed from their case-library entries and the repository. The runtime remains v0.4.0; a site refresh is not a new Skill release.

## 中文说明

[宣传首页](https://julyanxu.github.io/tracegif/?lang=zh)直接嵌入实际导出的 HTML，不用截图或录屏冒充交互。切换案例后，播放、暂停、倍速、进度与导出都由该作品自身的播放器完成。

首页通过 GitHub Pages 发布，读取案例列表需要网络；下载的独立动画 HTML 仍可离线播放。GitHub README 不支持运行 JavaScript 播放器，因此仓库首页提供真实演示入口。

新增案例需经过素材授权、实际浏览器验证和视觉复核。自动部署等待仓库检查通过，并发布对应提交；v0.4.0 的历史发布包保留七个旧案例，新增加的三个复杂案例从案例库单独下载。
