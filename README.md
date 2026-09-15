# Mine2Blend Editor

**在 Blender 中按 Minecraft 方块设计建筑，并导出 Litematic；让 Agent 读取方块与构件数据。**

本项目基于 **[CAT-YC/Mine2Blend](https://github.com/CAT-YC/Mine2Blend)** 二次开发，保留 MCBlock 原作者署名及 Git 历史，使用 **GPL-3.0-or-later**。当前为 **0.7.0 Alpha**，维护者为 `zhang132212`。这不是上游官方发行版。

[二次开发来源与致谢](ATTRIBUTION.zh-CN.md) · [完整第三方清单](THIRD_PARTY.md) · [使用说明](EDITOR-README.zh-CN.md) · [验收与限制](DESIGN.zh-CN.md) · [源码发布](https://github.com/zhang132212/Mine2Blend/releases)

## 从导入器扩展为编辑器

- **BlockGrid 唯一数据源**：保存坐标、方块 ID、Block State、typed NBT、区域和命名构件；导出不从 Mesh 反推。
- **编辑工具**：调色板、放置/删除/拾取、框选、填充、替换、复制粘贴、旋转/镜像/阵列、撤销重做、剖面与隔离。
- **26.2 数据**：1196 类方块、32,366 种状态物理定义、119 类实体模型；版本数据与构建资源固定。
- **分块渲染**：16³ chunk、共享 Geometry Nodes 实例、局部重建、模型/材质缓存、透明/tint、multipart、内部面剔除。
- **静态邻居逻辑**：楼梯、门、床、栅栏、墙、栏杆、铁轨和红石连接；不模拟游戏 tick。
- **资源包与 CTM**：支持 ctm、horizontal、vertical、overlay、repeat、fixed；仅改变预览。
- **投影格式**：Litematic 导入导出，多区域、实体/方块实体与计划 tick；Sponge v2/v3 导入、v2 导出。
- **持久化与 Agent**：场景保存、自动恢复、后台 I/O、修订号检查、多 Scene 隔离和结构化 MCP。

## 二次开发了哪些项目？

直接基于的 Blender 插件是 **Mine2Blend**。CTM 部分改编自 **Continuity**；使用 **deepslate、mcmeta、EntityModelJson、litemapy、mcschematic、nbtlib** 等代码或数据。每个项目的用途、版本与许可分别列在 [来源声明](ATTRIBUTION.zh-CN.md) 中。

新增 MCP server 是本仓库实现，使用 MCP Python SDK。它可以由 blender-mcp 调用，但没有复制第三方 Blender MCP 插件源码；`eunmc` 也不是本项目依赖。

## 源码构建与安装

构建需要 Python 3.13、Node.js 24、JDK 25（设置 `JAVA_HOME`）。插件运行时使用 Blender Python，不需要 Node 或 Java。

```sh
git clone --branch editor https://github.com/zhang132212/Mine2Blend.git
cd Mine2Blend
python -m venv .venv
# 激活虚拟环境后执行：
python -m pip install -r requirements-mcp.txt pillow==12.3.0
python tools/fetch_resources.py
npm ci --prefix resources/converter/win-x64 --omit=dev --ignore-scripts
node tools/bake_special_models.mjs
python tools/fetch_game_client.py
python tools/extract_game_models.py --minecraft-dir test-output/game-client
python -m unittest discover -s tests -v
python build_editor.py
```

在 Blender 的 **Preferences → Get Extensions → Install from Disk** 安装生成的 `dist/Mine2Blend-Editor-0.7.0.zip`，然后在 3D 视图按 **N → MC Editor → New Building**。

GitHub Release 提供源码包；源码 ZIP 不能直接作为 Blender 扩展安装。Minecraft 提取资源不作为 GPL 素材重新发布，需按以上步骤在本地构建。下载与提取过程不启动游戏、不读取存档。

## 结构化 MCP

面板启动 MCP Bridge 后，以独立 Python 环境运行：

```sh
python -m editor.mcp_server --descriptor <面板返回的本机descriptor路径>
```

可调用 `get_summary`、`get_components`、`query_region`、`query_chunk`、`place_block`、`fill_region`、`replace_blocks`、`validate_orientations`、`validate_support`、`export_litematic` 等工具。修改请求携带 `grid_id` 和当前 `expected_revision`。

名称为书斋/客舍等的构件由生成器或用户标注；导入未标注建筑时能精确读取方块，但不会自动获得房间用途。截图用于外观检查，结构分析使用 JSON 数据。

## 示例与测试

`examples/jiangnan_garden.py` 生成 48×48 江南园林；后续修订脚本演示山墙填充、围墙对称检查及固定柱距。示例使用本项目的 BlockGrid 与导出接口；本地 `.blend`、日志和生成输出不提交仓库。

已有 **55 项单元测试**、Blender 后台集成、GUI 编辑检查及 100k/500k 方块压力测试。最近一轮代码验证：[Windows / macOS / Linux 全部通过](https://github.com/zhang132212/Mine2Blend/actions/runs/34933488782)。实测 Blender 为 5.2.1；清单最低版本 4.2，不代表所有中间版本已经回归。

这是开发预览版：游戏端实际打开验收、动态 NBT 外观、复杂轨道分岔及外部资源包兼容仍有待完善。完整状态见 [需求矩阵](DESIGN.zh-CN.md)。请勿将其描述为全部 Minecraft 渲染/行为的完整复现。

## 许可证

插件代码：**GPL-3.0-or-later**，见 [LICENSE](LICENSE)。第三方保留各自许可证，见 [LICENSES](LICENSES)。Minecraft 客户端及美术资源属于其各自权利人，与插件代码许可分开处理。

原插件说明保存在 [README.upstream.md](README.upstream.md)。
