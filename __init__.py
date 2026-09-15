bl_info = {
    "name": "Mine2Blend Editor Alpha",
    "author": "MCBlock (upstream), zhang132212 (editor fork)",
    "version": (0, 7, 0),
    "blender": (4, 2, 0),
    "location": "3D 视图 > 侧栏 > MC Editor",
    "description": "Minecraft BlockGrid editor, Litematic export and structured Agent API",
    "category": "Import-Export",
}

import importlib
import sys

_SUBMODULES = (
    "preferences",
    "properties",
    "core.path_utils",
    "core.converter_bridge",
    "core.material_utils",
    "core.material_audit",
    "core.blender_importer",
    "core.diagnostics",
    "operators.import_ops",
    "operators.material_ops",
    "operators.website_ops",
    "operators.diagnostics_ops",
    "panels.root_panel",
    "panels.import_panel",
    "panels.settings_panel",
    "panels.material_panel",
    "panels.website_panel",
    "panels.diagnostics_panel",
    "editor.blender_ui",
)


def _iter_modules():
    package = __name__
    for name in _SUBMODULES:
        full_name = f"{package}.{name}"
        module = sys.modules.get(full_name)
        if module is None:
            module = importlib.import_module(full_name)
        yield module


def register():
    for module in _iter_modules():
        if hasattr(module, "register"):
            module.register()


def unregister():
    modules = list(_iter_modules())
    for module in reversed(modules):
        if hasattr(module, "unregister"):
            try:
                module.unregister()
            except Exception:
                pass
