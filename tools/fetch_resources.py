"""Fetch the pinned 26.2 resource archive for reproducible local/CI builds."""
from pathlib import Path
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'test-output/mcmeta-26.2-assets.zip';target.parent.mkdir(exist_ok=True)
if not target.exists():
    temp=target.with_suffix('.download')
    urllib.request.urlretrieve('https://codeload.github.com/misode/mcmeta/zip/a4151022c4c3870ac75e8d3a90e5c28e81137b60',temp)
    temp.replace(target)
from build_resources import build
print(build(target,ROOT/'editor/data/resources','26.2'))
