# TypeBit → TraceGIF

**TraceGIF** combines traced line animation with GIF creation. Version 0.4.0 introduces the name; it continues the same project and release history.

| Before | Now |
| --- | --- |
| `JulyanXu/typebit` | `JulyanXu/tracegif` |
| Install `skills/typebit-line-animation` | Install the complete `skills/tracegif` folder |
| Invoke `$typebit-line-animation` | Invoke `$tracegif` in Codex or `/tracegif` in Claude Code |
| `scripts/typebit.py` | `scripts/tracegif.py` |
| `typebit-line-animation-*.zip` | `tracegif-*.zip` |

Existing standalone HTML files keep working without an upgrade. To give an old editable project the new controls, use the new Skill to render it, run verification, export the formats you need, then package it. A working project with its private render snapshot archives the prior revision. Delivery ZIPs omit that snapshot: **retain the original ZIP and edit an extracted copy** so its old HTML and source remain available. Do not prepare the original image again just to change the player.

```text
python skills/tracegif/scripts/tracegif.py render PATH_TO_EXISTING_PROJECT
python skills/tracegif/scripts/tracegif.py verify PATH_TO_EXISTING_PROJECT/animation.html
python skills/tracegif/scripts/tracegif.py export PATH_TO_EXISTING_PROJECT --format gif
python skills/tracegif/scripts/tracegif.py package PATH_TO_EXISTING_PROJECT
```

The new standalone Skill also includes `scripts/typebit.py` as a compatibility entrypoint. In a repository checkout, the old path `skills/typebit-line-animation/scripts/typebit.py` forwards to TraceGIF. The small legacy Skill folder is an optional alias that requires the new `tracegif` folder beside it; do not install the alias alone. New installations should use only the complete `tracegif` folder. Existing project schema keys and the `window.typebit` browser API remain compatible; `window.tracegif` exposes the same player.

To update a clone's remote after the GitHub rename:

```text
git remote set-url origin https://github.com/JulyanXu/tracegif.git
```

Historical releases and their checksummed attachments remain unchanged. The new release has its own fresh verification reports.

## 中文

TypeBit 从 v0.4.0 起更名为 **TraceGIF（描线 GIF）**。新安装复制完整的 `skills/tracegif`，在 Codex 使用 `$tracegif`，在 Claude Code 使用 `/tracegif`。

已有 HTML 无需升级即可继续离线使用。已有可编辑工程只需重新渲染、验证和导出，就能获得新版播放器，不会因为改名而重新描摹原图。带有内部渲染快照的工作目录会归档旧版本；交付 ZIP 不包含该内部快照，升级时请**保留原 ZIP，并在解压副本中修改**，以保留旧 HTML 和源文件。

新 Skill 内保留旧脚本入口；仓库中的旧目录提供转发入口。旧名称的 Skill 别名需要与新 `tracegif` 文件夹并排安装，不能单独安装。新用户只安装完整的 `tracegif` 即可。
