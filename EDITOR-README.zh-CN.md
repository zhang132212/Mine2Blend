# Mine2Blend Editor 0.7.0 开发版

功能与尚未完成的验收详见 [设计记录](DESIGN.zh-CN.md)。

## 安装与编辑

1. Blender → Preferences → Get Extensions → Install from Disk，安装 `dist/Mine2Blend-Editor-0.7.0.zip`。
2. 3D 视图按 N → **MC Editor** → New Building。
3. From/To 使用 MC XYZ、Y 向上、端点包含在内。选择方块后 Fill 建底板。
4. Brush：左键放置、Shift+左键删除、Alt+左键拾取、1–9 切换快捷栏、Esc 退出。
5. Block State 下方显示合法属性表单。开启 Orient from view 根据视线/点击面推断方向。
6. 框选与坐标选区共用 From/To；工具区提供替换、复制/粘贴、旋转/镜像/平移/阵列、剖面/图层/隔离。
7. Undo Blocks/Redo Blocks 撤销方块与关联元数据。保存 .blend 会保存 BlockGrid。
8. Import/Export 使用后台作业；状态区显示作业结果，可取消尚未发布的输出。导出从 BlockGrid 生成。

Load Resource Pack 接受本地 ZIP 或文件夹。CTM 仅影响预览，不写进投影。
自动恢复每 60 秒生成压缩快照；恢复时创建新网格，保留当前建筑。

## 使用 blender-mcp

在 Blender 主线程执行：

```python
from bl_ext.user_default.mcblock_mine2blend.editor.blender_ui import execute
g = execute('create_grid', {'name': 'Agent Building'})
execute('fill_region', {
    'grid_id': g['grid_id'], 'expected_revision': g['revision'],
    'minimum': [0,0,0], 'maximum': [15,0,15], 'state': 'minecraft:stone_bricks'
})
print(execute('get_summary', {'grid_id': g['grid_id']}))
```

每次修改先查询 revision。`query_region` 提供精确方块、材料、楼层统计；`define_component`/`get_components` 保存墙、屋顶等命名构件。
`list_scenes` 返回 Scene ID；后续参数附带 `scene_id` 可避免窗口切换影响 Agent。
同一 `request_id` 的相同请求可重试，当前进程缓存最近 512 个成功结果；不同参数重用同一键会报错。

`render_preview` 可带 `path`、`size` 输出 PNG，使用临时场景，不更改工作相机。
`start_io_job`、`get_job_status`、`cancel_job` 提供后台投影 I/O。

## 独立 MCP

安装 `requirements-mcp.txt` 到独立 Python 3.13 环境。Blender 面板 Start MCP Bridge 返回 `%TEMP%/mine2blend-<PID>.json` descriptor。

```text
command: D:\blender\dev\Mine2Blend\.venv\Scripts\python.exe
args: -m editor.mcp_server --descriptor <实际 descriptor 路径>
cwd: D:\blender\dev\Mine2Blend
```

descriptor 内含随机 token，不必发送给 LLM。每个 Blender 进程独立。MCP SDK 不加载进 Blender。

## 可复现构建

```powershell
python -m pip install -r requirements-mcp.txt pillow==12.3.0
python tools/fetch_resources.py
npm ci --prefix resources/converter/win-x64 --omit=dev --ignore-scripts
node tools/bake_special_models.mjs
python -m unittest discover -s tests -v
python build_editor.py
```

`tools/build_biome_colors.py` 可重新生成 26.2 的 biome 色表。Minecraft 资源的许可与插件代码不同，源码仓库提供构建工具，不将生成的新版图集作为 GPL 资源发布。

Windows Blender 5.2.1 的流程已实测；Linux/macOS 验收状态以 CI 实际结果为准。
当前仍需完成 GN 后端、复杂建筑压力测试、实体动态外观及游戏端格式/方向对照。详见设计记录中的 13 项矩阵。
