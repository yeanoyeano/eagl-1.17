# ABOUT

This project is a version of eaglercraftX based on Minecraft 1.12, specifically optimized for performance. It is legally licensed under the MIT License.

## Key Features

* **Fake version 1.17:** Built upon the core features of Minecraft version 1.12.
* **Performance Focused:** Engineered for enhanced performance and efficiency.

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

## Textures

The bundled resource tree uses the **NTOV** pack (1.16-era textures backported
to the 1.12 asset layout) in place of the stock 1.12 textures. 630 of the
bundle's 1432 textures were swapped; the rest are byte-identical between the
two and were left alone.

## tools/epw_tool.py

`assets.epw` is a container of xz-compressed sections, one of which holds the
whole resource tree as a lax1dude EPK v2.0 archive. `tools/epw_tool.py` reads
and rewrites it:

```sh
python3 tools/epw_tool.py list    assets.epw              # every entry + size
python3 tools/epw_tool.py extract assets.epw out/         # unpack the tree
python3 tools/epw_tool.py patch   assets.epw pack/ new.epw
```

`patch` overlays `pack/assets/minecraft/textures/**` (a normal `pack_format: 3`
resource pack directory) onto the bundle, recompresses the archive, and repairs
the container's offsets and length. It only touches paths the bundle already
contains, so pack files for blocks and mobs that do not exist in 1.12 are
ignored rather than injected.
