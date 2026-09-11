# Credits

This project is a fork. Nothing here was written from scratch.

## EaglercraftX

The client itself - `classes.js`, `bootstrap.js` and the loader and resource
code inside `assets.epw` - is **EaglercraftX**, by **lax1dude**, released under
the MIT License (see `LICENSE`). The bundle identifies itself as
`net.lax1dude.eaglercraft.v1_8.client` and credits **PeytonPlayz585** as a
contributor. The default multiplayer relays it ships with are run by lax1dude
and ayunami.

Upstream: https://gitlab.com/lax1dude/eaglercraftx-1.8

## Textures

The bundled resource tree uses the **NTOV** pack, which backports 1.16-era
Minecraft textures to the 1.12 asset layout. 630 of the bundle's 1432 textures
come from it. Credit belongs to the pack's author - please add their name and a
link here.

## Minecraft

Minecraft is a trademark of Mojang Studios. This project is not affiliated with
or endorsed by Mojang Studios or Microsoft.

## Changes in this fork

* Swapped the stock 1.12 textures for the NTOV pack (see `README.md`).
* Added `tools/epw_tool.py`, which reads and rewrites the `.epw` asset bundle.
