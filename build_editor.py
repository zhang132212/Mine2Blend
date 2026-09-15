"""Build a Blender extension, including pure Python wheels, without legacy Node runtime."""
from pathlib import Path
import subprocess
import sys
import zipfile
import tomllib

ROOT = Path(__file__).resolve().parent
def main():
    wheels = ROOT / "wheels"
    wheels.mkdir(exist_ok=True)
    subprocess.run([sys.executable, "-m", "pip", "download", "--no-deps", "--only-binary=:all:",
                    "-r", str(ROOT / "requirements-editor.txt"), "-d", str(wheels)], check=True)
    version=tomllib.loads((ROOT/'blender_manifest.toml').read_text(encoding='utf-8'))['version']
    target = ROOT / f"dist/Mine2Blend-Editor-{version}.zip"
    target.parent.mkdir(exist_ok=True)
    folders = ["core", "operators", "panels", "editor", "wheels", "assets","LICENSES"]
    files = [ROOT / name for name in ("__init__.py", "preferences.py", "properties.py", "blender_manifest.toml", "LICENSE", "THIRD_PARTY.md", "ATTRIBUTION.zh-CN.md", "README.upstream.md", "EDITOR-README.zh-CN.md", "DESIGN.zh-CN.md")]
    for folder in folders:
        files.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    # Original geometry/atlas is available for fallback. Legacy converter remains optional.
    files.extend(p for p in (ROOT / "resources/converter/win-x64/assets").rglob("*") if p.is_file())
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
    print(target)

if __name__ == "__main__":
    main()
