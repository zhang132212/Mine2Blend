# 二次开发来源与致谢

本仓库是 [CAT-YC/Mine2Blend](https://github.com/CAT-YC/Mine2Blend) 的独立衍生项目，保留 Git 历史、原作者 MCBlock 的署名和许可证。上游起点为 `c73e8e66863fd48b16161fea46c406bcd807ac48`，原插件版本 0.5.2。编辑器维护者为 GitHub 用户 `zhang132212`。

## 直接基于的 Blender 插件

**Mine2Blend**：沿用插件工程、原投影导入器、转换桥接、材质与诊断等代码。原项目主要解决把 Minecraft 投影转换为 Blender 几何。本衍生版新增权威 BlockGrid、编辑事务、分块预览、实例化、Block State 与邻居逻辑、资源包/CTM、投影导出和结构化 Agent 接口。

代码沿用 **GPL-3.0-or-later**，完整文本见 [LICENSE](LICENSE)。原项目说明保存在 [README.upstream.md](README.upstream.md)。本项目并非上游官方发布版本。

## 其他使用或改编的项目

| 项目 | 关系与用途 | 许可证 |
|---|---|---|
| [Continuity](https://github.com/PepperCode1/Continuity) | CTM 连接纹理索引及 overlay 拓扑的 Python 改编；原提交 `e283f6e5ba2972d943be28809d80061974f0a6c4` | LGPL-3.0，保留专门声明和许可证 |
| [deepslate](https://github.com/misode/deepslate) | 上游转换器依赖；本版固定 0.27.1，用于构建期特殊模型 | MIT |
| [mcmeta](https://github.com/misode/mcmeta) | 固定 26.2 方块注册表、状态及构建资源来源 | Minecraft 提取数据/资源与工具代码分开对待 |
| [EntityModelJson](https://github.com/SizableShrimp/EntityModelJson) | 旧实体目录/贴图映射的来源；当前实体几何由 26.2 客户端重新提取 | MIT；保留 SizableShrimp 署名 |
| [litemapy](https://github.com/SmylerMC/litemapy) | Litematic 编解码库 | GPLv3 包元数据 |
| [mcschematic](https://github.com/Sloimayyy/mcschematic) | Sponge Schem 导出库 | Apache-2.0 |
| [nbtlib](https://github.com/vberlier/nbtlib) | 有类型 NBT/SNBT 读写 | MIT |
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | 独立 MCP server 的协议实现 | MIT |

完整版本、附属依赖和源码位置见 [THIRD_PARTY.md](THIRD_PARTY.md)，许可证副本见 [LICENSES](LICENSES)。

## 与 Blender MCP、eunmc 的关系

- 本仓库新增了自己的结构化 MCP server 和 Blender 主线程桥接层。
- 普通 blender-mcp 客户端可以通过执行插件 Python 接口进行调用；本仓库没有复制第三方 Blender MCP 插件源码，不能将“兼容调用”描述成“基于其源码二次开发”。
- `eunmc` 是独立的 Minecraft 测试服建造工具，不是本插件依赖，也不是本插件的源码来源。

## Minecraft 资源边界

Minecraft 客户端、模型与贴图属于其各自权利人，不因本仓库代码使用 GPL 而变为 GPL 素材。新版图集、客户端 JAR、构建依赖和生成的模型数据不提交到源码仓库；构建脚本从固定来源获取并在本地生成。公开发布的源码归档不包含本地安装包中的新版提取资源。
