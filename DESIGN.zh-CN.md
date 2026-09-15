# Minecraft 建筑编辑器：架构与验收记录

当前为 **0.7.0 开发版**。本文件区分已经实现的代码与尚未通过的验收，不能将全部 13 项需求视为完成。

工程：`D:\blender\dev\Mine2Blend`。上游保留完整 Git 历史；个人 Fork 为 https://github.com/zhang132212/Mine2Blend 。当前集成分支 `editor`，`import`、`exporter`、`mcp` 为预留模块分支。

## 架构决策

- BlockGrid 是唯一方块数据源。MC `(x,y,z)` 映射 Blender `(x,-z,y)`；不从网格反推 state。
- Python 负责编辑与格式；deepslate 0.27.1 在构建时生成特殊模型，插件运行时不需要 Node。原 Node 导入器保留为独立可选路径。
- JDK 25 仅用于构建期读取官方 26.2 客户端模型层和方块物理定义。客户端元数据 SHA-1 为 `1595470509933451a460bd157624e6e4f083890b`；下载逐文件校验，不启动游戏或访问存档。
- 位置字典、chunk 索引、不可变 BlockRecord、typed SNBT、region-local 实体；每次事务同时记录方块和元数据变化。
- NumPy 只读 uint16 chunk 调色板缓存，用于紧凑结构查询；编辑时按 chunk 失效，字典仍为唯一真源。
- 每 16³ chunk 一个派生对象，支持合并网格和 Geometry Nodes 实例化；相同表面/UV/材质共享模型。边界编辑使相关 3×3×3 chunk 失效。
- 修改必须携带 revision；Agent 可指定持久 Scene ID 和请求幂等键。所有 bpy 调用在主线程。
- 后台线程执行文件编解码；导出使用固定修订快照与临时文件原子替换；取消可阻止导出发布。
- 自动恢复为独立 gzip JSON，每 Scene 每 60 秒保存，保留最近 5 份。普通 .blend 保存含完整网格数据。
- 场景 JSON 在后台序列化，保存 .blend 前同步刷入最新修订。Blender 全局撤销保留方块历史；方块撤销使用 Undo Blocks/Redo Blocks。

## 需求矩阵

| # | 主题 | 已实现 | 尚需完成或进一步验收 |
|---|---|---|---|
| 1 | 工程/许可证 | Fork、GPL、依赖锁、纯 Python wheel 打包、deepslate 升级 | 三平台安装验证；旧 sidecar 的可选跨平台运行入口 |
| 2 | 26.2 | 1196 方块、32,366 状态物理定义；1198 blockstates、3928 models、1994 textures；66 biome 颜色；119 类实际实体模型 | 所有非默认状态视觉对照；动态 NBT 外观 |
| 3 | BlockGrid | bounds、chunk、regions、typed NBT、dirty、metadata、undo、NumPy 调色板查询 | 重叠导入 region 当前拒绝；不猜测冲突块优先级 |
| 4 | 渲染 | 分块、GN 实例化、模型缓存、atlas、cutout/alpha、tint、AO、静态流体、26.2 实体模型/变体/资源包贴图/未知占位 | 动态旗帜图案/告示牌文字/皮肤；动画 |
| 5 | 编辑 | 搜索、9 格快捷栏、画笔、框选、选区轮廓、填充替换、含实体/ticks 的复制粘贴、变换阵列、剖面隔离、恢复、region 面板 | 完整交互回归 |
| 6 | 方向 | 属性表单、点击面放置、半砖合并、双格门/铰链、stairs/fence/wall/pane/rail/wire 静态连接 | 墙与红石特殊邻居的游戏端逐例对照；支撑规则覆盖 |
| 7 | Multipart | AND/OR/when、多个模型组合、缓存、邻居失效、uvlock、按位置稳定的加权模型选择 | 加权随机种子不同于游戏；uvlock 精确性对照 |
| 8 | Culling | cullface、实际游戏 can_occlude/solid_render/面遮挡形状、边界矩形覆盖、贴图透明信息、透明同类连接；数据不删除 | 外部模型资源包视觉回归 |
| 9 | CTM | ctm47、horizontal、vertical、overlay、repeat、fixed、状态/贴图/面/biome/weight、实际 UV 面基底、基础规则与 overlay 叠加 | 外部资源包兼容回归；不含 OptiFine 全部扩展方法 |
| 10 | 格式 | Litematic 正负尺寸多区域、实体/Block Entity/ticks；Sponge v2/v3 读、v2 写；typed NBT 回环 | 游戏端 26.2 实际打开；Sponge biome 完整保存；根自定义标签策略 |
| 11 | MCP | JSON schema、结构查询/命名构件、NumPy chunk 查询、门/床配对与支撑检查、主线程桥、Scene ID、幂等请求、PNG 预览、IO 作业 | 跨客户端回归；静态支撑不等于游戏 tick 验证 |
| 12 | 性能 | 100k/500k 实心和混合实例测试、局部重建、后台 IO/序列化、取消、恢复、轮转错误日志 | 首次复杂场景预览优化、内存和帧时间预算 |
| 13 | 测试 | Python 单测、Blender 后台流程、47 CTM 图块、GUI 放置/框选；含 GN/实体的三平台 CI 已通过 e14b394 | 新客户端提取链三平台复验；游戏端对照 |

## 实际验证

- `tests/test_*.py`：状态、连接、变换、CTM、遮挡、流体、格式/NBT、任务与恢复、MCP stdio。
- `tests/blender_workflows.py`：后台导出/导入、Scene 隔离、按 Scene 指定操作、幂等、独立 PNG、恢复、保存重开。
- `tests/blender_ctm.py`：47 种连接形态在 Blender 面材质上逐一匹配编号贴图。
- `tests/blender_gallery.py`：146 类特殊模型候选总览，26.2 普通模型优先于旧特殊渲染器。
- `tests/blender_instances.py`：实例化后逐顶点与网格后端比较，保存重开、切换后资源释放。
- `tests/blender_entities.py`：实体预览、未知实体占位、原始 NBT 导出。
- 三平台 CI： https://github.com/zhang132212/Mine2Blend/actions/runs/34931258914 （提交 e14b394）。
- 官方客户端下载后的独立提取构建已在 Windows 通过：358 模型层、32,366 状态/364 物理配置，119 类实体，旧实体几何回退为 0。`tests/blender_entity_gallery.py` 的 15 类实体渲染已检查。
- `tools/audit_resources.py`：1196 默认状态无缺失模型、无缺失贴图；这不等于全部视觉与游戏一致。
- `tests/blender_benchmark.py`：原始机器耗时见 `test-output/benchmark.json`，仅实心石头场景，不能代表复杂建筑。
- Computer Use 已在独立 QA 窗口验证 Fill、画笔放置、面拾取/方向，用户原窗口未修改。
- `Editor-QA-Instances.blend` 的 GN 场景画笔 GUI 验证：297 → 298 块，楼梯正确落在拾取表面。
- 混合 8 种模型、间隔 2 格的 GN 基准：100k 为 338 chunk / 8 原型，首次预览 5.76 秒、单次编辑 0.35 秒；500k 为 1183 chunk / 8 原型，首次预览 132.04 秒、单次编辑 1.08 秒。见 `test-output/complex-benchmark.json`。所有 chunk 共享一个节点组。此基准不能代表所有复杂材质包或硬件。
- 资源包支持新版主次版本范围和按顺序应用的 overlays；解析依据 Mojang 25w31a 元数据规范。旧包可加载预览，但会返回不兼容版本提示。
- 独立测试 profile 的安装包启用、18 块 Litematic 导出、真实 HTTP Bridge 和未授权请求拒绝均通过；不修改用户原 Blender profile。

## 数据保真边界

新 grid 使用 DataVersion 4903，导入文件保留原 DataVersion，不执行 DataFixer 升级。多个冲突 region 不静默压平，越界块导出报错并要求明确区域。Sponge 无标准 scheduled-tick 字段，含待执行 tick 的建筑须使用 Litematic。实体和方向性属性随变换更新；未知 mod NBT 的方向语义不能自动推断。

本项目编辑离线建筑，不连接或修改 eunmc 测试服；未修改现有 blender-mcp 客户端配置。
