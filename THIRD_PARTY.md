# Third-party inventory — 2026-09-15

This derivative retains Mine2Blend's GPL-3.0-or-later declaration and MCBlock attribution.
Modified/new editor files are distributed under GPL-3.0-or-later. See LICENSE.
Upstream: https://github.com/CAT-YC/Mine2Blend
Development fork: https://github.com/zhang132212/Mine2Blend

| Component | Selected version | License / use |
|---|---|---|
| Mine2Blend | upstream source 0.5.2 | GPL-3.0-or-later, original importer retained |
| litemapy | 0.11.0b0 | GPLv3 package metadata; litematic codec |
| nbtlib | 2.0.4 | MIT; typed SNBT and NBT |
| mcschematic | 11.4.4 | Apache-2.0; Sponge v2 export |
| immutable-views | 0.6.1 | Apache-2.0; mcschematic dependency |
| typing_extensions | 4.16.0 | PSF licensing; packaged wheel retains license |
| numpy | Blender-provided | BSD-3-Clause; no duplicate binary wheel in extension |
| MCP Python SDK | 2.2.0 | MIT; separate venv, not loaded into Blender |
| Pillow | 12.3.0 | MIT-CMU; build-only atlas generator |
| deepslate | 0.27.1, exact lock | MIT; build-time special model baking and optional legacy converter |
| sharp | upstream range ^0.34.5 | Apache-2.0; legacy converter only, native libvips dependency requires platform packaging |
| gl-matrix | upstream range ^3.4.3 | MIT; legacy converter only |
| Node.js | not bundled in editor ZIP | Node distribution includes multiple third-party notices; optional legacy sidecar |

Pure-Python dependency wheels retain their dist-info license files in the extension.
Before redistribution, ship corresponding modified source, GPL text and notices with the
binary/extension release, and retain each dependency's notices. Do not describe Minecraft
textures or extracted game assets as GPL-licensed: their ownership is separate from code.
Local resource builds are for the user's installed game/authorized resource packs; review
each pack's redistribution terms before publishing a release containing it.

Sources:
- https://www.gnu.org/licenses/gpl-3.0.html
- https://github.com/CAT-YC/Mine2Blend#许可
- https://github.com/misode/deepslate/blob/main/LICENSE
- https://github.com/lovell/sharp/blob/main/LICENSE
- https://github.com/Sloimayyy/mcschematic/blob/main/LICENSE
- https://github.com/misode/mcmeta (extracted Minecraft data/assets; code and assets have different provenance)

## Resource pin

## Continuity-derived CTM topology

The CTM 256-entry tile-index map and overlay topology in `editor/ctm.py` and
`editor/data/ctm-map.json` are adapted from PepperCode1/Continuity, commit
`e283f6e5ba2972d943be28809d80061974f0a6c4`, under LGPL-3.0. The port is modified
for Python and Blender. Original source: https://github.com/PepperCode1/Continuity
Files: CtmSpriteProvider.java, StandardOverlayQuadProcessor.java, DirectionMaps.java.
The original LGPL text is retained in LICENSES/Continuity-LGPL-3.0.txt.

- Minecraft Java 26.2: DataVersion 4903, resource pack 88.0, data pack 107.1.
- Summary tag commit: `711a353b47d84e6cb592a1b72f682e5f44759284`.
- Assets tag commit: `a4151022c4c3870ac75e8d3a90e5c28e81137b60`.
- Metadata: https://raw.githubusercontent.com/misode/mcmeta/26.2-summary/version.json
- Official release: https://www.minecraft.net/en-us/article/minecraft-java-edition-26-2
- `editor/data/blocks.json` is the 26.2 summary's allowed properties and defaults.
- Original legacy atlas remains pinned to the upstream converter's 2026-02-26-copy resource label.
