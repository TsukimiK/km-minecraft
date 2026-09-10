from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent
runtime_path = ROOT / "src/main/java/jp/km/ripperdoc/RipperdocRuntime.java"
items_path = ROOT / "src/main/java/jp/km/ripperdoc/RipperdocItems.java"
mod_path = ROOT / "src/main/java/jp/km/ripperdoc/RipperdocMod.java"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 match, found {count}")
    return text.replace(old, new, 1)


def sub_once(text: str, pattern: str, repl: str, label: str) -> str:
    new, count = re.subn(pattern, repl, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 regex match, found {count}")
    return new


# ---------------------------------------------------------------------------
# Java runtime: low-overhead HUD, revised Moontech input, Aquatic state machine
# ---------------------------------------------------------------------------
text = runtime_path.read_text(encoding="utf-8")

# v1.0.1 used ActionBar as a use-progress display. v1.0.2 removes it entirely.
text = text.replace("import net.minecraft.network.chat.Component;\n", "")
text = text.replace("import net.minecraft.network.protocol.game.ClientboundSetActionBarTextPacket;\n", "")
if "import net.minecraft.world.entity.player.Input;" not in text:
    text = replace_once(
        text,
        "import net.minecraft.world.entity.ai.attributes.Attributes;",
        "import net.minecraft.world.entity.ai.attributes.Attributes;\nimport net.minecraft.world.entity.player.Input;",
        "Input import",
    )

text = text.replace(
    "private static final int USE_HOLD_TICKS = 20;\n    private static final int USE_PROGRESS_SEGMENTS = 10;",
    "private static final int USE_HOLD_TICKS = 20;",
)
text = text.replace("    private static final double MOONTECH_JUMP_ADD = 0.265;\n", "")
text = text.replace(
    "private static final double MOONTECH_SECOND_JUMP_Y = 0.685;",
    "private static final double MOONTECH_BOOST_JUMP_Y = 0.685;",
)
text = text.replace(
    'private static final Identifier MOONTECH_JUMP_MOD = Identifier.parse("ripperdoc:moontech_jump");',
    'private static final Identifier MOONTECH_LEGACY_JUMP_MOD = Identifier.parse("ripperdoc:moontech_jump");',
)
text = replace_once(
    text,
    'private static final Identifier AQUATIC_MOVE_MOD = Identifier.parse("ripperdoc:aquatic_surface_movement");',
    'private static final Identifier AQUATIC_MOVE_MOD = Identifier.parse("ripperdoc:aquatic_surface_movement");\n'
    '    private static final Identifier AQUATIC_WATER_MOVE_MOD = Identifier.parse("ripperdoc:aquatic_surface_water_movement");',
    "Aquatic water movement id",
)

# Activation is ~1 second of the drink animation. No use-progress HUD.
text = sub_once(
    text,
    r"    private void tickUse\(ServerPlayer player, PlayerState state\) \{.*?\n    \}\n\n    private void toggleTimedAbility",
    '''    private void tickUse(ServerPlayer player, PlayerState state) {
        String currentId = "";
        if (player.isUsingItem()) {
            ItemStack use = player.getUseItem();
            if (RipperdocItems.isTimedImplant(use)) currentId = RipperdocItems.id(use);
        }

        if (currentId.isEmpty()) {
            state.useId = "";
            state.useHoldTicks = 0;
            return;
        }

        if (!currentId.equals(state.useId)) {
            state.useId = currentId;
            state.useHoldTicks = 1;
        } else {
            state.useHoldTicks++;
        }

        if (state.useHoldTicks < USE_HOLD_TICKS) return;

        // Toggle at ~1 second, before the reusable implant could be consumed by vanilla.
        player.stopUsingItem();
        toggleTimedAbility(player, state, currentId);
        state.useId = "";
        state.useHoldTicks = 0;
        state.visualDirty = true;
    }

    private void toggleTimedAbility''',
    "tickUse replacement",
)

# Moontech: normal SPACE is vanilla; SHIFT+SPACE on the ground is a ~3 block jump.
# One additional ~3 block SPACE jump is available while airborne (max two jumps total).
text = sub_once(
    text,
    r"    private void tickMoontech\(ServerPlayer player, PlayerState state\) \{.*?\n    \}\n\n    private void updateMoontechEquip",
    '''    private void tickMoontech(ServerPlayer player, PlayerState state) {
        updateMoontechEquip(player, state);
        Input input = player.getLastClientInput();
        boolean jump = input.jump();

        if (!state.moontechEquipped) {
            state.previousJumpInput = jump;
            return;
        }

        boolean jumpEdge = jump && !state.previousJumpInput;
        state.previousJumpInput = jump;

        if (player.onGround()) state.airTicks = 0;
        else state.airTicks++;

        boolean groundJump = jumpEdge && (player.onGround() || state.previousOnGround);
        if (groundJump) {
            startMoontechFallSession(player, state);
            if (input.shift()) performMoontechBoostJump(player);
        } else if (jumpEdge
                && state.moonFallSession
                && state.airJumpsUsed < 1
                && state.airTicks >= 2
                && canAirJump(player)) {
            performAirJump(player, state);
        }

        if (state.moonFallSession) {
            state.moonAge++;
            if (player.onGround()) state.moonGroundTicks++;
            else state.moonGroundTicks = 0;

            if (state.moonGroundTicks >= 3
                    || state.moonAge >= MOONTECH_SESSION_TIMEOUT
                    || !canMaintainMoonSession(player)) {
                endMoontechFallSession(player, state);
            }
        }
    }

    private void updateMoontechEquip''',
    "Moontech tick replacement",
)

text = sub_once(
    text,
    r"    private void updateMoontechEquip\(ServerPlayer player, PlayerState state\) \{.*?\n    \}\n\n    private void startMoontechFallSession",
    '''    private void updateMoontechEquip(ServerPlayer player, PlayerState state) {
        boolean equipped = RipperdocItems.is(player.getItemBySlot(EquipmentSlot.FEET), RipperdocItems.MOONTECH);
        if (equipped == state.moontechEquipped) return;
        state.moontechEquipped = equipped;

        // v1.0.2 no longer modifies JUMP_STRENGTH while the boots are equipped.
        // This keeps a normal SPACE jump completely vanilla.
        removeModifier(player, Attributes.JUMP_STRENGTH, MOONTECH_LEGACY_JUMP_MOD);
        if (!equipped) endMoontechFallSession(player, state);
    }

    private void startMoontechFallSession''',
    "Moontech equip replacement",
)

text = text.replace("MOONTECH_SECOND_JUMP_Y", "MOONTECH_BOOST_JUMP_Y")
text = text.replace("state.airJumpsUsed < 2", "state.airJumpsUsed < 1")

# Insert explicit ground boost helper immediately before the air-jump helper.
marker = "    private void performAirJump(ServerPlayer player, PlayerState state) {"
boost_helper = '''    private void performMoontechBoostJump(ServerPlayer player) {
        Vec3 velocity = player.getDeltaMovement();
        player.setDeltaMovement(velocity.x, MOONTECH_BOOST_JUMP_Y, velocity.z);
        player.resetFallDistance();
        player.setOnGround(false);
        // Event-only packet: sent once when the boost jump starts, never every tick.
        player.connection.send(new ClientboundSetEntityMotionPacket(player));
    }

'''
text = replace_once(text, marker, boost_helper + marker, "Moontech boost helper")

# Aquatic: replace the old near-surface snap logic with a small per-player state machine.
text = sub_once(
    text,
    r"    private void tickAquatic\(ServerPlayer player, PlayerState state\) \{.*?\n    \}\n\n    private Double findWaterSurface",
    '''    private void tickAquatic(ServerPlayer player, PlayerState state) {
        Input input = player.getLastClientInput();
        boolean jump = input.jump();
        boolean jumpEdge = jump && !state.previousAquaticJump;
        state.previousAquaticJump = jump;

        if (state.aquaticTicks <= 0 || player.isPassenger() || player.isFallFlying() || player.isInLava()) {
            disableAquaticSurface(player, state);
            state.aquaticAirborne = false;
            state.aquaticDiveGraceTicks = 0;
            return;
        }

        if (state.aquaticAirborne && player.onGround() && !player.isInWater()) {
            state.aquaticAirborne = false;
        }

        Double surfaceY = findWaterSurface(player);

        if (state.aquaticOnSurface) {
            if (surfaceY == null) {
                disableAquaticSurface(player, state);
                return;
            }

            // SHIFT alone intentionally drops through the synthetic water surface.
            // SHIFT+SPACE is reserved for Moontech's boosted first jump.
            if (input.shift() && !jump) {
                beginAquaticDive(player, state);
                return;
            }

            if (jumpEdge) {
                launchFromAquaticSurface(player, state, input.shift());
                return;
            }

            if (!Double.isNaN(state.aquaticSurfaceY)
                    && Math.abs(surfaceY - state.aquaticSurfaceY) > 1.1) {
                disableAquaticSurface(player, state);
                return;
            }

            holdAquaticSurface(player, state, surfaceY);
            return;
        }

        // While intentionally diving, do not immediately pull the player back to the surface.
        if (input.shift() && !jump) {
            state.aquaticDiveGraceTicks = 12;
            state.aquaticAirborne = false;
            return;
        }
        if (state.aquaticDiveGraceTicks > 0) {
            state.aquaticDiveGraceTicks--;
            if (player.isInWater()) return;
        }

        if (surfaceY == null) return;

        Vec3 velocity = player.getDeltaMovement();
        double nextY = player.getY() + velocity.y;

        if (state.aquaticAirborne) {
            // Never snap upward while a water-surface jump is still ascending.
            if (velocity.y > 0.0) return;

            boolean crossesSurface = player.getY() >= surfaceY - 0.35 && nextY <= surfaceY + 0.20;
            boolean closeToSurface = player.getY() >= surfaceY - 0.30 && player.getY() <= surfaceY + 0.25;
            if (crossesSurface || closeToSurface) landOnAquaticSurface(player, state, surfaceY);
            return;
        }

        boolean fallingOntoSurface = velocity.y <= 0.0
                && player.getY() >= surfaceY - 0.35
                && nextY <= surfaceY + 0.20;
        boolean nearSurface = player.getY() >= surfaceY - 0.25 && player.getY() <= surfaceY + 0.25;
        boolean swimmingUp = player.isInWater()
                && velocity.y >= 0.0
                && player.getY() >= surfaceY - 0.30
                && player.getY() <= surfaceY + 0.20;

        if (fallingOntoSurface || nearSurface || swimmingUp) {
            landOnAquaticSurface(player, state, surfaceY);
        }
    }

    private Double findWaterSurface''',
    "Aquatic tick replacement",
)

text = sub_once(
    text,
    r"    private Double findWaterSurface\(ServerPlayer player\) \{.*?\n    \}\n\n    private void enableAquaticSurface",
    '''    private Double findWaterSurface(ServerPlayer player) {
        ServerLevel level = player.level();
        int topY = (int)Math.floor(player.getY() + 2.0);

        // At most ten local block checks, only while AQUATIC is active.
        // This also works when the feet are slightly inside water, which is required for
        // reliable re-landing after a jump.
        for (int y = topY; y >= topY - 9; y--) {
            BlockPos water = BlockPos.containing(player.getX(), y, player.getZ());
            if (!level.getFluidState(water).is(FluidTags.WATER)) continue;
            if (level.getFluidState(water.above()).is(FluidTags.WATER)) continue;
            return water.getY() + 1.0;
        }
        return null;
    }

    private void holdAquaticSurface(ServerPlayer player, PlayerState state, double surfaceY) {
        enableAquaticSurface(player, state);
        state.aquaticSurfaceY = surfaceY;

        if (Math.abs(player.getY() - surfaceY) > 0.06) {
            player.setPos(player.getX(), surfaceY + 0.001, player.getZ());
        }

        Vec3 velocity = player.getDeltaMovement();
        if (Math.abs(velocity.y) > 1.0E-4) {
            player.setDeltaMovement(velocity.x, 0.0, velocity.z);
        }
        player.resetFallDistance();
        player.setOnGround(true);
    }

    private void landOnAquaticSurface(ServerPlayer player, PlayerState state, double surfaceY) {
        enableAquaticSurface(player, state);
        state.aquaticAirborne = false;
        state.aquaticDiveGraceTicks = 0;
        state.aquaticSurfaceY = surfaceY;

        player.setPos(player.getX(), surfaceY + 0.001, player.getZ());
        Vec3 velocity = player.getDeltaMovement();
        player.setDeltaMovement(velocity.x, 0.0, velocity.z);
        player.resetFallDistance();
        player.setOnGround(true);
        // Event-only motion sync on landing. No continuous packet spam.
        player.connection.send(new ClientboundSetEntityMotionPacket(player));
    }

    private void launchFromAquaticSurface(ServerPlayer player, PlayerState state, boolean shiftHeld) {
        disableAquaticSurface(player, state);
        state.aquaticAirborne = true;
        state.aquaticDiveGraceTicks = 0;

        if (state.moontechEquipped && !state.moonFallSession) {
            startMoontechFallSession(player, state);
        }

        Vec3 velocity = player.getDeltaMovement();
        double jumpY = state.moontechEquipped && shiftHeld ? MOONTECH_BOOST_JUMP_Y : NORMAL_JUMP_Y;
        player.setDeltaMovement(velocity.x, jumpY, velocity.z);
        player.resetFallDistance();
        player.setOnGround(false);
        player.connection.send(new ClientboundSetEntityMotionPacket(player));
    }

    private void beginAquaticDive(ServerPlayer player, PlayerState state) {
        disableAquaticSurface(player, state);
        state.aquaticAirborne = false;
        state.aquaticDiveGraceTicks = 12;
        Vec3 velocity = player.getDeltaMovement();
        player.setDeltaMovement(velocity.x, Math.min(velocity.y, -0.18), velocity.z);
        player.setOnGround(false);
        player.connection.send(new ClientboundSetEntityMotionPacket(player));
    }

    private void enableAquaticSurface''',
    "Aquatic surface finder/helpers replacement",
)

text = sub_once(
    text,
    r"    private void enableAquaticSurface\(ServerPlayer player, PlayerState state\) \{.*?\n    \}\n\n    private void disableAquaticSurface",
    '''    private void enableAquaticSurface(ServerPlayer player, PlayerState state) {
        state.aquaticOnSurface = true;

        AttributeInstance gravity = player.getAttribute(Attributes.GRAVITY);
        if (gravity != null && !gravity.hasModifier(AQUATIC_GRAVITY_MOD)) {
            gravity.addTransientModifier(new AttributeModifier(AQUATIC_GRAVITY_MOD, -1.0, AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL));
        }

        // These two attributes remove the synthetic-surface slowdown without touching
        // horizontal velocity every tick.
        AttributeInstance movementEfficiency = player.getAttribute(Attributes.MOVEMENT_EFFICIENCY);
        if (movementEfficiency != null && !movementEfficiency.hasModifier(AQUATIC_MOVE_MOD)) {
            movementEfficiency.addTransientModifier(new AttributeModifier(AQUATIC_MOVE_MOD, 1.0, AttributeModifier.Operation.ADD_VALUE));
        }
        AttributeInstance waterMovement = player.getAttribute(Attributes.WATER_MOVEMENT_EFFICIENCY);
        if (waterMovement != null && !waterMovement.hasModifier(AQUATIC_WATER_MOVE_MOD)) {
            waterMovement.addTransientModifier(new AttributeModifier(AQUATIC_WATER_MOVE_MOD, 1.0, AttributeModifier.Operation.ADD_VALUE));
        }
    }

    private void disableAquaticSurface''',
    "Aquatic modifier enable replacement",
)

text = sub_once(
    text,
    r"    private void disableAquaticSurface\(ServerPlayer player, PlayerState state\) \{.*?\n    \}\n\n    private void cleanupLegacyPlayer",
    '''    private void disableAquaticSurface(ServerPlayer player, PlayerState state) {
        state.aquaticOnSurface = false;
        state.aquaticSurfaceY = Double.NaN;
        removeModifier(player, Attributes.GRAVITY, AQUATIC_GRAVITY_MOD);
        removeModifier(player, Attributes.MOVEMENT_EFFICIENCY, AQUATIC_MOVE_MOD);
        removeModifier(player, Attributes.WATER_MOVEMENT_EFFICIENCY, AQUATIC_WATER_MOVE_MOD);
    }

    private void cleanupLegacyPlayer''',
    "Aquatic modifier disable replacement",
)

text = sub_once(
    text,
    r"    private void disableAquatic\(ServerPlayer player, PlayerState state\) \{.*?\n    \}\n\n    private void applyZande",
    '''    private void disableAquatic(ServerPlayer player, PlayerState state) {
        state.aquaticTicks = 0;
        state.aquaticMissingChecks = 0;
        state.aquaticAirborne = false;
        state.aquaticDiveGraceTicks = 0;
        state.visualDirty = true;
        disableAquaticSurface(player, state);
    }

    private void applyZande''',
    "disable Aquatic replacement",
)

# Remove the v1.0.1 use-progress helper methods completely.
text = re.sub(
    r"    private void showUseProgress\(ServerPlayer player, int ticks\) \{.*?\n    \}\n\n    private void clearUseProgress\(ServerPlayer player\) \{.*?\n    \}\n\n",
    "",
    text,
    count=1,
    flags=re.S,
)

# Native HUD runs every tick only as three boolean comparisons; network packets are only sent
# on state changes or a 30-second resync.
text = replace_once(
    text,
    "            tickAquatic(player, state);\n            syncVisualsIfNeeded(player, state, fallbackVisualPass);",
    "            tickAquatic(player, state);\n            RipperdocHud.tick(player, state);\n            syncVisualsIfNeeded(player, state, fallbackVisualPass);",
    "HUD tick hook",
)

# Legacy jump modifier is cleanup-only now. Add Aquatic water movement cleanup too.
text = text.replace("Attributes.JUMP_STRENGTH, MOONTECH_JUMP_MOD", "Attributes.JUMP_STRENGTH, MOONTECH_LEGACY_JUMP_MOD")
text = replace_once(
    text,
    "        removeModifier(player, Attributes.MOVEMENT_EFFICIENCY, AQUATIC_MOVE_MOD);\n    }\n\n    private void reapplyFromState",
    "        removeModifier(player, Attributes.MOVEMENT_EFFICIENCY, AQUATIC_MOVE_MOD);\n"
    "        removeModifier(player, Attributes.WATER_MOVEMENT_EFFICIENCY, AQUATIC_WATER_MOVE_MOD);\n"
    "    }\n\n    private void reapplyFromState",
    "global Aquatic water cleanup",
)

# Player state additions for Aquatic landing/dive and packet-light potion-style HUD.
text = replace_once(
    text,
    "        boolean aquaticOnSurface;\n        int lastInventoryChange = -1;",
    "        boolean aquaticOnSurface;\n"
    "        boolean aquaticAirborne;\n"
    "        int aquaticDiveGraceTicks;\n"
    "        double aquaticSurfaceY = Double.NaN;\n"
    "        boolean hudZandeVisible;\n"
    "        boolean hudBerserkVisible;\n"
    "        boolean hudAquaticVisible;\n"
    "        int hudResyncTicker;\n"
    "        int lastInventoryChange = -1;",
    "PlayerState additions",
)
text = replace_once(
    text,
    "            previousAquaticJump = false;\n            aquaticOnSurface = false;",
    "            previousAquaticJump = false;\n"
    "            aquaticOnSurface = false;\n"
    "            aquaticAirborne = false;\n"
    "            aquaticDiveGraceTicks = 0;\n"
    "            aquaticSurfaceY = Double.NaN;",
    "movement state reset",
)

runtime_path.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Item visual state: keep active model if desired, but never force enchantment glint.
# ---------------------------------------------------------------------------
items = items_path.read_text(encoding="utf-8")
items = replace_once(
    items,
    '''        Boolean glint = stack.get(DataComponents.ENCHANTMENT_GLINT_OVERRIDE);
        boolean modelMatches = wantedModel.equals(currentModel);
        boolean glintMatches = Boolean.valueOf(active).equals(glint);
        if (currentActive == active && modelMatches && glintMatches) return false;''',
    '''        Boolean glintOverride = stack.get(DataComponents.ENCHANTMENT_GLINT_OVERRIDE);
        boolean modelMatches = wantedModel.equals(currentModel);
        boolean glintClear = glintOverride == null;
        if (currentActive == active && modelMatches && glintClear) return false;''',
    "glint match logic",
)
items = replace_once(
    items,
    "        stack.set(DataComponents.ENCHANTMENT_GLINT_OVERRIDE, active);",
    "        stack.remove(DataComponents.ENCHANTMENT_GLINT_OVERRIDE);",
    "remove forced glint",
)
items_path.write_text(items, encoding="utf-8")

# ---------------------------------------------------------------------------
# Version and static data text/use animation cleanup
# ---------------------------------------------------------------------------
mod = mod_path.read_text(encoding="utf-8")
mod = replace_once(mod, 'public static final String VERSION = "1.0.1";', 'public static final String VERSION = "1.0.2";', "mod version")
mod_path.write_text(mod, encoding="utf-8")

resource_root = ROOT / "src/main/resources/data/ripperdoc"

# Slightly longer vanilla consumable duration than the Java toggle threshold prevents the
# reusable item from ever being consumed, while still giving an approximately one-second drink.
for rel in [
    "loot_table/items/zandevistan.json",
    "loot_table/items/berserk.json",
    "loot_table/items/aquatic.json",
    "recipe/zandevistan.json",
    "recipe/berserk.json",
    "recipe/aquatic.json",
]:
    path = resource_root / rel
    data = json.loads(path.read_text(encoding="utf-8"))

    def tune_consumable(obj):
        if isinstance(obj, dict):
            value = obj.get("minecraft:consumable")
            if isinstance(value, dict):
                value["consume_seconds"] = 1.25
                value["animation"] = "drink"
                value["sound"] = "minecraft:entity.generic.drink"
            for child in obj.values():
                tune_consumable(child)
        elif isinstance(obj, list):
            for child in obj:
                tune_consumable(child)

    tune_consumable(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

moon_lore = [
    {"text": "SPACE：通常ジャンプ", "italic": False, "color": "gray"},
    {"text": "SHIFT + SPACE：強化ジャンプ 約3ブロック", "italic": False, "color": "gray"},
    {"text": "空中でSPACE：2段目ジャンプ 約3ブロック", "italic": False, "color": "gray"},
    {"text": "MOONTECHジャンプ後：着地時の落下ダメージ無効", "italic": False, "color": "gray"},
]

for rel in ["loot_table/items/moontech.json", "recipe/moontech_upgrade.json"]:
    path = resource_root / rel
    data = json.loads(path.read_text(encoding="utf-8"))

    def patch_moontech(obj):
        if isinstance(obj, dict):
            custom = obj.get("minecraft:custom_data")
            if isinstance(custom, dict) and custom.get("ripperdoc_id") == "moontech" and "minecraft:lore" in obj:
                obj["minecraft:lore"] = moon_lore
            for child in obj.values():
                patch_moontech(child)
        elif isinstance(obj, list):
            for child in obj:
                patch_moontech(child)

    patch_moontech(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Document intentional dive input on new Aquatic items/recipes.
for rel in ["loot_table/items/aquatic.json", "recipe/aquatic.json"]:
    path = resource_root / rel
    data = json.loads(path.read_text(encoding="utf-8"))

    def patch_aquatic(obj):
        if isinstance(obj, dict):
            custom = obj.get("minecraft:custom_data")
            if isinstance(custom, dict) and custom.get("ripperdoc_id") == "aquatic" and isinstance(obj.get("minecraft:lore"), list):
                lore = obj["minecraft:lore"]
                if not any(isinstance(x, dict) and x.get("text") == "SHIFTのみ：水中へ潜る" for x in lore):
                    lore.insert(-1, {"text": "SHIFTのみ：水中へ潜る", "italic": False, "color": "gray"})
            for child in obj.values():
                patch_aquatic(child)
        elif isinstance(obj, list):
            for child in obj:
                patch_aquatic(child)

    patch_aquatic(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

for path in (ROOT / "src/main/resources").rglob("*.json"):
    json.loads(path.read_text(encoding="utf-8"))

print("Applied Ripperdoc native v1.0.2 low-overhead feedback patch")
