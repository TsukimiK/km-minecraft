# KM Minecraft Fabric Server Mod 26.2 v2.1.0

Production migration build for an existing KM Minecraft datapack world.

## Requirements
- Minecraft Java 26.2
- Java 25
- Fabric Loader 0.19.3+
- Fabric API 0.159.0+26.2

## Production migration
1. Stop the server cleanly and back up the whole world first.
2. Remove the old external `km-minecraft` datapack from `world/datapacks`.
3. Put `km-minecraft-servermod-26.2-2.1.0.jar` in the server `mods` folder.
4. Keep Fabric API installed.
5. Replace the client/server-distributed KM resource pack with the production resource pack shipped with this release.
6. Fully restart the server. Do not use `/reload` for the migration.
7. Confirm `/km status`, then verify one existing KM item and one existing planted crop before reopening the server to players.

Do not run the old external datapack and this mod together. The old datapack still owns vanilla load/tick tags, while this mod owns the same runtime through Fabric lifecycle events.

## Compatibility policy
The production build intentionally preserves the `km-minecraft` namespace, existing recipe/advancement/function identifiers, custom item data keys, item model identifiers, scoreboard objective names, crop entity types and crop tags used by the former datapack.

Existing inventory/chest/shulker/ender-chest items created by the datapack remain vanilla-backed item stacks with the same KM components, so they continue to be recognized. Existing planted crops remain `minecraft:interaction` entities with the same KM tags and are picked up by the bundled runtime after restart. Crop visuals are rebuilt on server start.

For crops that were already planted before migration, their previously selected normal/rare result is preserved. Immature rare crops are simply hidden behind the normal stage-0/stage-1 appearance and reveal their preserved rare result at maturity. New crops use the new maturity-time 1% roll.

The deliberate recipe correction remains: ordinary vanilla poisonous potatoes and ordinary echo shards are no longer accepted as substitutes for KM Daikon/Asahatamon materials. Existing KM items are unaffected because they carry the required `minecraft:custom_data`.

## Admin commands
These are registered by Java through Fabric API.

- `/km status`
- `/kmgive seeds`
- `/kmgive daikon_tools`
- `/kmgive asahatamon_tools`
- `/kmgive asahatamon_armor`
- `/kmgive cigarette_box`
- `/kmgive all`

`/kmgive` is restricted to game-master/operator permission.

## Runtime
The mod has a real Java `ModInitializer`. Fabric lifecycle/tick events own startup and ticking. Recipes, loot tables, predicates, advancements and compatibility function resources are bundled inside the JAR; no external KM datapack is installed. Vanilla `#minecraft:load` and `#minecraft:tick` tags are intentionally removed to prevent duplicate execution.

## Build safety
CI verifies JSON validity, required Fabric classes, absence of the old vanilla tick tag, and that every `data/km-minecraft` resource path that existed in the former datapack still exists in the production mod build.
