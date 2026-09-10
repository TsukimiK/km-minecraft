from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent
runtime_path = ROOT / "src/main/java/jp/km/ripperdoc/RipperdocRuntime.java"
items_path = ROOT / "src/main/java/jp/km/ripperdoc/RipperdocItems.java"
commands_path = ROOT / "src/main/java/jp/km/ripperdoc/RipperdocCommands.java"
mod_path = ROOT / "src/main/java/jp/km/ripperdoc/RipperdocMod.java"
hud_path = ROOT / "src/main/java/jp/km/ripperdoc/RipperdocHud.java"


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
# Runtime: remove AQUATIC, harden Moontech recharge, reduce background polling.
# ---------------------------------------------------------------------------
text = runtime_path.read_text(encoding="utf-8")

for imp in [
    "import net.minecraft.core.BlockPos;\n",
    "import net.minecraft.server.level.ServerLevel;\n",
    "import net.minecraft.tags.FluidTags;\n",
]:
    text = text.replace(imp, "")

text = text.replace("    private static final int OWNERSHIP_CHECK_INTERVAL = 10;\n", "    private static final int OWNERSHIP_CHECK_INTERVAL = 40;\n")
text = text.replace("    private static final int VISUAL_FALLBACK_INTERVAL = 40;\n", "    private static final int VISUAL_FALLBACK_INTERVAL = 20 * 30;\n")
text = text.replace("    private static final double NORMAL_JUMP_Y = 0.42;\n", "")

# AQUATIC v1.0.2 attribute ids are no longer part of active runtime.
for line in [
    '    private static final Identifier AQUATIC_GRAVITY_MOD = Identifier.parse("ripperdoc:aquatic_surface_gravity");\n',
    '    private static final Identifier AQUATIC_MOVE_MOD = Identifier.parse("ripperdoc:aquatic_surface_movement");\n',
    '    private static final Identifier AQUATIC_WATER_MOVE_MOD = Identifier.parse("ripperdoc:aquatic_surface_water_movement");\n',
]:
    text = text.replace(line, "")

text = text.replace(
    "            tickMoontech(player, state);\n            tickAquatic(player, state);\n            RipperdocHud.tick(player, state);\n            syncVisualsIfNeeded(player, state, fallbackVisualPass);",
    "            tickMoontech(player, state);\n            syncVisualsIfNeeded(player, state, fallbackVisualPass);",
)
text = text.replace("            existing.aquaticOnSurface = false;\n", "")
text = text.replace("        if (state != null) state.aquaticOnSurface = false;\n", "")

text = sub_once(
    text,
    r"    private void toggleTimedAbility\(ServerPlayer player, PlayerState state, String id\) \{.*?\n    \}\n\n    private void tickTimedAbilities",
    '''    private void toggleTimedAbility(ServerPlayer player, PlayerState state, String id) {
        switch (id) {
            case RipperdocItems.ZANDEVISTAN -> {
                if (state.zandeTicks > 0) disableZande(player, state);
                else enableZande(player, state);
            }
            case RipperdocItems.BERSERK -> {
                if (state.berserkTicks > 0) disableBerserk(player, state);
                else enableBerserk(player, state);
            }
            default -> { }
        }
    }

    private void tickTimedAbilities''',
    "two ability toggle",
)

text = sub_once(
    text,
    r"    private void tickTimedAbilities\(ServerPlayer player, PlayerState state\) \{.*?\n    \}\n\n    private void enableZande",
    '''    private void tickTimedAbilities(ServerPlayer player, PlayerState state) {
        if (state.zandeTicks > 0 && --state.zandeTicks <= 0) disableZande(player, state);
        if (state.berserkTicks > 0 && --state.berserkTicks <= 0) disableBerserk(player, state);

        // The hotbar timer uses Minecraft's own durability bar. We only mark the inventory
        // dirty when one of the 13 visible bar steps changes, not every tick or every second.
        if (++state.timerBarTicker >= 20) {
            state.timerBarTicker = 0;
            int zandeStep = timerBarStep(state.zandeTicks);
            int berserkStep = timerBarStep(state.berserkTicks);
            if (zandeStep != state.zandeBarStep || berserkStep != state.berserkBarStep) {
                state.zandeBarStep = zandeStep;
                state.berserkBarStep = berserkStep;
                state.visualDirty = true;
            }
        }

        // Inventory ownership checks are event-biased: react to inventory changes immediately,
        // with only a two-second fallback for cursor/crafting edge cases.
        int inventoryChange = player.getInventory().getTimesChanged();
        boolean inventoryChanged = inventoryChange != state.lastOwnershipInventoryChange;
        if (++state.ownershipTicker < OWNERSHIP_CHECK_INTERVAL && !inventoryChanged) return;
        state.ownershipTicker = 0;
        state.lastOwnershipInventoryChange = inventoryChange;

        if (state.zandeTicks > 0) {
            state.zandeMissingChecks = RipperdocItems.hasPlayerOwned(player, RipperdocItems.ZANDEVISTAN) ? 0 : state.zandeMissingChecks + 1;
            if (state.zandeMissingChecks >= OWNERSHIP_GRACE_CHECKS) disableZande(player, state);
        }
        if (state.berserkTicks > 0) {
            state.berserkMissingChecks = RipperdocItems.hasPlayerOwned(player, RipperdocItems.BERSERK) ? 0 : state.berserkMissingChecks + 1;
            if (state.berserkMissingChecks >= OWNERSHIP_GRACE_CHECKS) disableBerserk(player, state);
        }
    }

    private static int timerBarStep(int ticks) {
        if (ticks <= 0) return 0;
        return Math.max(1, Math.min(13, (ticks * 13 + ABILITY_TICKS - 1) / ABILITY_TICKS));
    }

    private void enableZande''',
    "timed ability low-overhead replacement",
)

# AQUATIC disable helper sits between Berserk and Zande attribute code in v1.0.2.
text = re.sub(
    r"\n    private void disableAquatic\(ServerPlayer player, PlayerState state\) \{.*?\n    \}\n(?=\n    private void applyZande)",
    "",
    text,
    count=1,
    flags=re.S,
)

# Moontech is recharged only after four consecutive grounded ticks. This prevents transient
# onGround reports or rapid key tapping from granting unlimited air jumps.
text = sub_once(
    text,
    r"    private void tickMoontech\(ServerPlayer player, PlayerState state\) \{.*?\n    \}\n\n    private void updateMoontechEquip",
    '''    private void tickMoontech(ServerPlayer player, PlayerState state) {
        updateMoontechEquip(player, state);
        Input input = player.getLastClientInput();
        boolean jump = input.jump();
        boolean jumpEdge = jump && !state.previousJumpInput;
        state.previousJumpInput = jump;

        if (!state.moontechEquipped) return;

        if (player.onGround()) {
            state.moonGroundStableTicks = Math.min(4, state.moonGroundStableTicks + 1);
            state.airTicks = 0;
            if (state.moonGroundStableTicks >= 4) {
                if (state.moonFallSession) endMoontechFallSession(player, state);
                state.moonJumpReady = true;
                state.airJumpsUsed = 0;
            }
        } else {
            state.moonGroundStableTicks = 0;
            state.airTicks++;
        }

        boolean groundLaunch = jumpEdge
                && state.moonJumpReady
                && (player.onGround() || state.previousOnGround);

        if (groundLaunch) {
            // Consume the whole jump charge at takeoff. It cannot be restored until a real landing
            // has been confirmed for four consecutive server ticks.
            state.moonJumpReady = false;
            startMoontechFallSession(player, state);
            if (input.shift()) performMoontechBoostJump(player);
        } else if (jumpEdge
                && state.moonFallSession
                && !state.moonJumpReady
                && state.airJumpsUsed < 1
                && state.airTicks >= 2
                && canAirJump(player)) {
            performAirJump(player, state);
        }

        if (state.moonFallSession) {
            state.moonAge++;
            if (state.moonAge >= MOONTECH_SESSION_TIMEOUT || !canMaintainMoonSession(player)) {
                endMoontechFallSession(player, state);
                // Do not recharge here. Only confirmed ground contact can recharge the air jump.
                state.moonJumpReady = false;
            }
        }
    }

    private void updateMoontechEquip''',
    "Moontech anti-infinite state machine",
)

text = sub_once(
    text,
    r"    private void updateMoontechEquip\(ServerPlayer player, PlayerState state\) \{.*?\n    \}\n\n    private void startMoontechFallSession",
    '''    private void updateMoontechEquip(ServerPlayer player, PlayerState state) {
        boolean equipped = RipperdocItems.is(player.getItemBySlot(EquipmentSlot.FEET), RipperdocItems.MOONTECH);
        if (equipped == state.moontechEquipped) return;
        state.moontechEquipped = equipped;

        // Cleanup-only legacy modifier; normal SPACE remains vanilla.
        removeModifier(player, Attributes.JUMP_STRENGTH, MOONTECH_LEGACY_JUMP_MOD);
        state.moonGroundStableTicks = 0;
        state.moonJumpReady = false;
        if (!equipped) endMoontechFallSession(player, state);
    }

    private void startMoontechFallSession''',
    "Moontech equip recharge reset",
)

# Remove the entire AQUATIC state-machine section.
text = re.sub(
    r"\n    private void tickAquatic\(ServerPlayer player, PlayerState state\) \{.*?\n    private void cleanupLegacyPlayer",
    "\n    private void cleanupLegacyPlayer",
    text,
    count=1,
    flags=re.S,
)

# Remove now-obsolete AQUATIC modifier cleanup calls.
text = re.sub(r"^\s*removeModifier\(player, Attributes\.(?:GRAVITY|MOVEMENT_EFFICIENCY|WATER_MOVEMENT_EFFICIENCY), AQUATIC_[A-Z_]+\);\n", "", text, flags=re.M)
text = text.replace("        disableAquatic(player, state);\n", "")

# Replace PlayerState as one block to avoid leaving any AQUATIC/HUD state behind.
text = sub_once(
    text,
    r"    public static final class PlayerState \{.*?\n    \}\n\}",
    '''    public static final class PlayerState {
        public int zandeTicks;
        public int berserkTicks;
        int zandeMissingChecks;
        int berserkMissingChecks;
        int ownershipTicker;
        int lastOwnershipInventoryChange = -1;
        String useId = "";
        int useHoldTicks;
        boolean moontechEquipped;
        boolean moonFallSession;
        int airJumpsUsed;
        int moonGroundTicks;
        int moonGroundStableTicks;
        boolean moonJumpReady;
        int moonAge;
        int airTicks;
        boolean previousJumpInput;
        boolean previousOnGround;
        int timerBarTicker;
        int zandeBarStep;
        int berserkBarStep;
        int lastInventoryChange = -1;
        boolean visualDirty = true;

        void clearAbilities() {
            zandeTicks = berserkTicks = 0;
            zandeMissingChecks = berserkMissingChecks = 0;
            ownershipTicker = 0;
            lastOwnershipInventoryChange = -1;
            useId = "";
            useHoldTicks = 0;
            timerBarTicker = 0;
            zandeBarStep = berserkBarStep = 0;
            visualDirty = true;
            resetMovementSession();
        }

        void resetMovementSession() {
            moonFallSession = false;
            airJumpsUsed = 0;
            moonGroundTicks = 0;
            moonGroundStableTicks = 0;
            moonJumpReady = false;
            moonAge = 0;
            airTicks = 0;
            previousJumpInput = false;
        }
    }
}''',
    "PlayerState clean replacement",
)

runtime_path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Item rendering: use vanilla durability bar as a 13-step remaining-time meter.
# No HUD packets and no client mod are required.
# ---------------------------------------------------------------------------
items = items_path.read_text(encoding="utf-8")
items = items.replace('    public static final String AQUATIC = "aquatic";\n', "")
items = items.replace(
    "        return ZANDEVISTAN.equals(id) || BERSERK.equals(id) || AQUATIC.equals(id);",
    "        return ZANDEVISTAN.equals(id) || BERSERK.equals(id);",
)

items = sub_once(
    items,
    r"    public static boolean syncPlayerVisuals\(ServerPlayer player, RipperdocRuntime.PlayerState state\) \{.*?\n    \}\n\n    public static boolean normalizeDropped",
    '''    public static boolean syncPlayerVisuals(ServerPlayer player, RipperdocRuntime.PlayerState state) {
        boolean changed = false;
        for (int i = 0; i < player.getInventory().getContainerSize(); i++) {
            changed |= syncStack(player.getInventory().getItem(i), state);
        }
        Container craft = player.inventoryMenu.getCraftSlots();
        for (int i = 0; i < craft.getContainerSize(); i++) {
            changed |= syncStack(craft.getItem(i), state);
        }
        changed |= syncStack(player.containerMenu.getCarried(), state);

        if (changed) {
            player.getInventory().setChanged();
            player.inventoryMenu.broadcastChanges();
            if (player.containerMenu != player.inventoryMenu) player.containerMenu.broadcastChanges();
        }
        return changed;
    }

    private static boolean syncStack(ItemStack stack, RipperdocRuntime.PlayerState state) {
        String itemId = id(stack);
        return switch (itemId) {
            case ZANDEVISTAN -> syncImplantVisual(stack, state.zandeTicks > 0, state.zandeTicks);
            case BERSERK -> syncImplantVisual(stack, state.berserkTicks > 0, state.berserkTicks);
            default -> false;
        };
    }

    public static boolean normalizeDropped''',
    "timer bar inventory sync",
)

items = items.replace(
    "        if (!syncImplantVisual(copy, false)) return false;",
    "        if (!syncImplantVisual(copy, false, 0)) return false;",
)

# desiredState is no longer needed because the timer ticks are passed directly.
items = re.sub(
    r"\n    private static boolean desiredState\(String id, RipperdocRuntime.PlayerState state\) \{.*?\n    \}\n",
    "\n",
    items,
    count=1,
    flags=re.S,
)

items = sub_once(
    items,
    r"    public static boolean syncImplantVisual\(ItemStack stack, boolean active\) \{.*?\n    \}\n\}",
    '''    private static final int TIMER_BAR_MAX_DAMAGE = 1300;

    public static boolean syncImplantVisual(ItemStack stack, boolean active, int remainingTicks) {
        String itemId = id(stack);
        if (!(ZANDEVISTAN.equals(itemId) || BERSERK.equals(itemId))) return false;

        Identifier wantedModel = Identifier.parse("ripperdoc:" + itemId + (active ? "_active" : ""));
        CustomData custom = stack.getOrDefault(DataComponents.CUSTOM_DATA, CustomData.EMPTY);
        CompoundTag tag = custom.copyTag();
        boolean currentActive = tag.getBooleanOr("ripperdoc_active", false);
        Identifier currentModel = stack.get(DataComponents.ITEM_MODEL);
        Boolean glintOverride = stack.get(DataComponents.ENCHANTMENT_GLINT_OVERRIDE);

        Integer currentMaxDamage = stack.get(DataComponents.MAX_DAMAGE);
        Integer currentDamage = stack.get(DataComponents.DAMAGE);
        int wantedDamage = active ? timerDamage(remainingTicks) : 0;
        boolean barMatches = active
                ? Integer.valueOf(TIMER_BAR_MAX_DAMAGE).equals(currentMaxDamage)
                    && Integer.valueOf(wantedDamage).equals(currentDamage)
                : currentMaxDamage == null && currentDamage == null;

        boolean modelMatches = wantedModel.equals(currentModel);
        boolean glintClear = glintOverride == null;
        if (currentActive == active && modelMatches && glintClear && barMatches) return false;

        CustomData.update(DataComponents.CUSTOM_DATA, stack, nbt -> {
            if (active) nbt.putBoolean("ripperdoc_active", true);
            else nbt.remove("ripperdoc_active");
        });
        stack.set(DataComponents.ITEM_MODEL, wantedModel);
        stack.remove(DataComponents.ENCHANTMENT_GLINT_OVERRIDE);

        if (active) {
            // Damage=1 keeps the vanilla bar visible even at effectively 100% remaining.
            // 1300 max damage maps cleanly to Minecraft's 13-pixel item bar.
            stack.set(DataComponents.MAX_DAMAGE, TIMER_BAR_MAX_DAMAGE);
            stack.set(DataComponents.DAMAGE, wantedDamage);
        } else {
            stack.remove(DataComponents.DAMAGE);
            stack.remove(DataComponents.MAX_DAMAGE);
        }
        return true;
    }

    private static int timerDamage(int remainingTicks) {
        int ticks = Math.max(1, Math.min(RipperdocRuntime.ABILITY_TICKS, remainingTicks));
        int step = Math.max(1, Math.min(13,
                (ticks * 13 + RipperdocRuntime.ABILITY_TICKS - 1) / RipperdocRuntime.ABILITY_TICKS));
        return 1 + (13 - step) * 100;
    }
}''',
    "durability timer bar renderer",
)

items_path.write_text(items, encoding="utf-8")


# ---------------------------------------------------------------------------
# Commands: AQUATIC removed from status/give/all.
# ---------------------------------------------------------------------------
commands = commands_path.read_text(encoding="utf-8")
commands = commands.replace('                                .then(Commands.literal("aquatic").executes(ctx -> give(ctx.getSource(), "aquatic")))\n', "")
commands = commands.replace(
    '        source.sendSuccess(() -> Component.literal("ZANDEVISTAN: " + timer(state.zandeTicks)\n                + " | BERSERK: " + timer(state.berserkTicks)\n                + " | AQUATIC: " + timer(state.aquaticTicks)), false);',
    '        source.sendSuccess(() -> Component.literal("ZANDEVISTAN: " + timer(state.zandeTicks)\n                + " | BERSERK: " + timer(state.berserkTicks)), false);',
)
commands = commands.replace('        give(source, "aquatic");\n', "")
if "aquatic" in commands.lower():
    raise RuntimeError("AQUATIC command reference remains")
commands_path.write_text(commands, encoding="utf-8")


# The potion-proxy HUD is fully removed in v1.0.3.
if hud_path.exists():
    hud_path.unlink()

# Version.
mod = mod_path.read_text(encoding="utf-8")
mod = replace_once(mod, 'public static final String VERSION = "1.0.2";', 'public static final String VERSION = "1.0.3";', "mod version")
mod_path.write_text(mod, encoding="utf-8")

# Remove AQUATIC's static acquisition data. Existing old items remain ordinary stored ItemStacks,
# but the native v1.0.3 runtime no longer recognizes, grants, or activates them.
resource_root = ROOT / "src/main/resources/data/ripperdoc"
for rel in ["loot_table/items/aquatic.json", "recipe/aquatic.json"]:
    path = resource_root / rel
    if path.exists():
        path.unlink()

for path in (ROOT / "src/main/resources").rglob("*.json"):
    json.loads(path.read_text(encoding="utf-8"))

# Architecture assertions at patch time as an early CI failure.
final_runtime = runtime_path.read_text(encoding="utf-8")
final_items = items_path.read_text(encoding="utf-8")
for forbidden in ["tickAquatic(", "aquaticTicks", "RipperdocHud.tick", "AQUATIC_GRAVITY_MOD", "AQUATIC_MOVE_MOD"]:
    if forbidden in final_runtime:
        raise RuntimeError(f"obsolete AQUATIC runtime symbol remains: {forbidden}")
if "AQUATIC" in final_items:
    raise RuntimeError("obsolete AQUATIC item symbol remains")

print("Applied Ripperdoc native v1.0.3: timer bars, Aquatic removal, Moontech anti-infinite fix")
