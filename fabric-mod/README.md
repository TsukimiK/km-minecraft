# KM Minecraft Fabric Server Mod 26.2 v2.0.0

This is the real Fabric server-mod build of KM Minecraft.

## Requirements
- Minecraft Java 26.2
- Java 25
- Fabric Loader 0.19.3+
- Fabric API 0.159.0+26.2

## Install
1. Remove the old `km-minecraft` datapack from `world/datapacks`.
2. Put the built `km-minecraft-servermod-26.2-2.0.0.jar` in the server `mods` folder.
3. Keep Fabric API installed.
4. Use the updated KM resource pack for client visuals.
5. Fully restart the server.

## Native Fabric commands
These are registered by Java through Fabric API and do not rely on a datapack function tag.

- `/km status`
- `/km functiontest`
- `/kmgive seeds`
- `/kmgive daikon_tools`
- `/kmgive asahatamon_tools`
- `/kmgive asahatamon_armor`
- `/kmgive cigarette_box`
- `/kmgive all`

## Runtime
The mod has a Java `ModInitializer`. Fabric lifecycle/tick events own startup and ticking. Recipes, loot tables, predicates, advancements and function resources are bundled inside the JAR; no external KM datapack is installed. Vanilla `#minecraft:load` and `#minecraft:tick` tags are intentionally removed to prevent duplicate execution.

## Crop gacha fix
Normal-seed crops use the same appearance for stage 0 and stage 1. The 1% Asahatamon roll happens only when stage 2 (mature) is reached, preventing plant/break/replant visual rerolling.
