# Building the client from source

The files at the root of this repo (`classes.js`, `bootstrap.js`, `assets.epw`)
are compiled output. This document records how to rebuild them from the source
tree, which was verified end to end on 2026-09-11.

## Where the source is

**https://github.com/yeanoyeano/fakelercraft-1.17-finale**

The repo is named "1.17" but its README says plainly:
`# Eaglercraft 1.12 (README ripped from 1.8)`. It is a 1.12 tree - the same
version this site runs - plus a client-base mod menu under
`com.isacofff.clientbase`. 3655 Java files.

It builds two targets. `wasm_gc_teavm/` is the WASM-GC one, which is what this
site serves; the root project targets plain JavaScript instead.

### Proof it is this site's source

Building it produces files identical to what is already deployed here:

| artifact | result |
| --- | --- |
| `bootstrap.js` | byte-identical to this repo's copy |
| `favicon.png` | byte-identical to this repo's copy |
| `eagruntime.js` | 104833 bytes, the exact size of that section in `assets.epw` |
| EPK entry list | 5790 entries, same paths, none added or missing |

Most files that do differ are JSON (models, advancements, recipes,
blockstates) and differ only in formatting from a fresh EPK compile.

## Prerequisites

* JDK - built with OpenJDK 21; the tree's README recommends 17 for TeaVM
* Gradle - the wrapper downloads what it needs
* Network access to `repo1.maven.org`, `services.gradle.org` and GitHub

## The catch: the TeaVM fork

WASM-GC needs a modified TeaVM published at
`https://eaglercraft-teavm-fork.github.io/maven/`. If that host is reachable,
the build resolves `org.teavm:0.11.0-EAGLER-R1` on its own and you can skip
this section.

It is *not* reachable from the Claude Code sandbox, whose egress proxy blocks
`*.github.io` (`CONNECT tunnel failed, 403`). Git access is a separate lane and
does work, so build the fork from source instead:

```sh
git clone --depth 1 -b eagler-r1 \
    https://github.com/Eaglercraft-TeaVM-Fork/eagler-teavm
cd eagler-teavm
./gradlew publishToMavenLocal -x test --no-daemon      # ~4 min
```

Its `gradle.properties` declares `teavm.project.version=0.11.0-EAGLER-R1`,
exactly what the client build asks for. Then add `mavenLocal()` as the *first*
repository in both `wasm_gc_teavm/settings.gradle` (inside `pluginManagement`)
and `wasm_gc_teavm/build.gradle`, so Gradle resolves locally and never reaches
the blocked host.

Do not commit that change upstream - it is a sandbox workaround, not a fix.

## Build

```sh
cd wasm_gc_teavm
sh CompileEPK.sh            # -> javascript/assets.epk      (20331880 bytes)
sh CompileWASM.sh           # -> javascript/classes.wasm    (7761581 bytes, ~1m20s)
sh CompileEagRuntimeJS.sh   # -> javascript/eagruntime.js   (104833 bytes)
sh MakeWASMClientBundle.sh  # -> javascript_dist/
```

The result is `javascript_dist/assets.epw` (16808804 bytes), `bootstrap.js`,
`index.html`, `favicon.png`, and a single-file offline
`Eaglercraft_1.12.2_WASM_Offline_Download.html` (22424924 bytes).

To deploy, copy those over this repo's root files and bump the `?v=` on
`assetsURI` in `index.html` - see the cache note there.

## Why this matters

With the source, changes that are impossible against a compiled bundle become
ordinary edits:

* Textures come from `desktopRuntime/resources/`, so `tools/epw_tool.py` is no
  longer needed to change them - it stays useful for inspecting a bundle you
  do not have the source for.
* Game behaviour is editable. Two things worth knowing about this tree:
  * `ItemSword` has no `getItemUseAction`/`onItemRightClick`, so there is no
    1.8-style sword blocking.
  * `ItemShield` is the real 1.12 implementation - `EnumAction.BLOCK`, the
    `blocking` property override that drives the model, 336 durability, and
    `EntityPlayer.damageShield()` at line 974.
  * but `disableShield` appears nowhere in the tree, so an axe hit does not
    stagger a shield the way it does in vanilla 1.12.
