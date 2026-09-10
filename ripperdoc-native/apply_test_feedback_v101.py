from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parent
runtime_path = ROOT / "src/main/java/jp/km/ripperdoc/RipperdocRuntime.java"
mod_path = ROOT / "src/main/java/jp/km/ripperdoc/RipperdocMod.java"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 match, found {count}")
    return text.replace(old, new, 1)


# ---- Java runtime feedback fixes ----
text = runtime_path.read_text(encoding="utf-8")
text = replace_once(text,
    "import net.minecraft.network.protocol.game.ClientboundSetEntityMotionPacket;",
    "import net.minecraft.network.chat.Component;\nimport net.minecraft.network.protocol.game.ClientboundSetActionBarTextPacket;\nimport net.minecraft.network.protocol.game.ClientboundSetEntityMotionPacket;",
    "actionbar imports")
text = replace_once(text,
    "private static final int USE_HOLD_TICKS = 32;",
    "private static final int USE_HOLD_TICKS = 20;\n    private static final int USE_PROGRESS_SEGMENTS = 10;",
    "use duration")
text = replace_once(text,
    "private static final Identifier AQUATIC_GRAVITY_MOD = Identifier.parse(\"ripperdoc:aquatic_surface_gravity\");",
    "private static final Identifier AQUATIC_GRAVITY_MOD = Identifier.parse(\"ripperdoc:aquatic_surface_gravity\");\n    private static final Identifier AQUATIC_MOVE_MOD = Identifier.parse(\"ripperdoc:aquatic_surface_movement\");",
    "aquatic movement id")

text = replace_once(text,
'''        if (currentId.isEmpty()) {
            state.useId = "";
            state.useHoldTicks = 0;
            return;
        }''',
'''        if (currentId.isEmpty()) {
            if (!state.useId.isEmpty()) clearUseProgress(player);
            state.useId = "";
            state.useHoldTicks = 0;
            return;
        }''',
    "use release cleanup")

text = replace_once(text,
'''        if (state.useHoldTicks < USE_HOLD_TICKS) return;

        // Legacy items deliberately have a 60-second consumable. Stop at 32 ticks, before vanilla can consume them.
        player.stopUsingItem();
        toggleTimedAbility(player, state, currentId);
        state.useId = "";
        state.useHoldTicks = 0;
        state.visualDirty = true;''',
'''        showUseProgress(player, state.useHoldTicks);
        if (state.useHoldTicks < USE_HOLD_TICKS) return;

        // Toggle after roughly one second of the vanilla drink animation, then stop before the item is consumed.
        player.stopUsingItem();
        toggleTimedAbility(player, state, currentId);
        clearUseProgress(player);
        state.useId = "";
        state.useHoldTicks = 0;
        state.visualDirty = true;''',
    "one second activation")

# Triple jump = initial ground jump + two additional air jumps.
text = text.replace("!state.secondJumpUsed", "state.airJumpsUsed < 2")
text = text.replace("performSecondJump(player, state)", "performAirJump(player, state)")
text = text.replace("state.secondJumpUsed = false;", "state.airJumpsUsed = 0;")
text = text.replace("state.secondJumpUsed = true;", "state.airJumpsUsed++;")
text = text.replace("private void performSecondJump(ServerPlayer player, PlayerState state)", "private void performAirJump(ServerPlayer player, PlayerState state)")
text = text.replace("boolean secondJumpUsed;", "int airJumpsUsed;")
text = text.replace("secondJumpUsed = false;", "airJumpsUsed = 0;")
if "secondJumpUsed" in text:
    raise RuntimeError("triple jump patch left secondJumpUsed references")

# AQUATIC: stop forcing a velocity packet every tick; keep vanilla horizontal acceleration/sprint.
text = replace_once(text,
'''        player.setDeltaMovement(velocity.x, 0.0, velocity.z);
        player.resetFallDistance();
        player.setOnGround(true);
        player.connection.send(new ClientboundSetEntityMotionPacket(player));''',
'''        player.setDeltaMovement(velocity.x, 0.0, velocity.z);
        player.resetFallDistance();
        player.setOnGround(true);''',
    "aquatic packet spam")

text = replace_once(text,
'''        AttributeInstance gravity = player.getAttribute(Attributes.GRAVITY);
        if (gravity != null && !gravity.hasModifier(AQUATIC_GRAVITY_MOD)) {
            gravity.addTransientModifier(new AttributeModifier(AQUATIC_GRAVITY_MOD, -1.0, AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL));
        }''',
'''        AttributeInstance gravity = player.getAttribute(Attributes.GRAVITY);
        if (gravity != null && !gravity.hasModifier(AQUATIC_GRAVITY_MOD)) {
            gravity.addTransientModifier(new AttributeModifier(AQUATIC_GRAVITY_MOD, -1.0, AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL));
        }
        // Water is not a real supporting block. Force block movement efficiency to 1 while standing on the synthetic surface
        // so sprinting/strafe speed stays close to normal land movement without spawning helper entities.
        AttributeInstance movementEfficiency = player.getAttribute(Attributes.MOVEMENT_EFFICIENCY);
        if (movementEfficiency != null && !movementEfficiency.hasModifier(AQUATIC_MOVE_MOD)) {
            movementEfficiency.addTransientModifier(new AttributeModifier(AQUATIC_MOVE_MOD, 1.0, AttributeModifier.Operation.ADD_VALUE));
        }''',
    "aquatic movement efficiency")

text = replace_once(text,
'''        state.aquaticOnSurface = false;
        removeModifier(player, Attributes.GRAVITY, AQUATIC_GRAVITY_MOD);''',
'''        state.aquaticOnSurface = false;
        removeModifier(player, Attributes.GRAVITY, AQUATIC_GRAVITY_MOD);
        removeModifier(player, Attributes.MOVEMENT_EFFICIENCY, AQUATIC_MOVE_MOD);''',
    "aquatic modifier cleanup")

text = replace_once(text,
'''        removeModifier(player, Attributes.FALL_DAMAGE_MULTIPLIER, MOONTECH_FALL_MOD);
        removeModifier(player, Attributes.GRAVITY, AQUATIC_GRAVITY_MOD);''',
'''        removeModifier(player, Attributes.FALL_DAMAGE_MULTIPLIER, MOONTECH_FALL_MOD);
        removeModifier(player, Attributes.GRAVITY, AQUATIC_GRAVITY_MOD);
        removeModifier(player, Attributes.MOVEMENT_EFFICIENCY, AQUATIC_MOVE_MOD);''',
    "global modifier cleanup")

# Small actionbar progress bar. Vanilla clients do not expose a stable right-bottom HUD anchor;
# actionbar is used so no client mod is required and every GUI scale remains readable.
insert_before = "    private static void removeModifier(ServerPlayer player, net.minecraft.core.Holder<net.minecraft.world.entity.ai.attributes.Attribute> attribute, Identifier id) {"
helper = '''    private void showUseProgress(ServerPlayer player, int ticks) {
        int filled = Math.min(USE_PROGRESS_SEGMENTS,
                Math.max(0, (ticks * USE_PROGRESS_SEGMENTS + USE_HOLD_TICKS - 1) / USE_HOLD_TICKS));
        int empty = USE_PROGRESS_SEGMENTS - filled;
        int percent = Math.min(100, Math.max(0, ticks * 100 / USE_HOLD_TICKS));
        String bar = "█".repeat(filled) + "░".repeat(empty);
        player.connection.send(new ClientboundSetActionBarTextPacket(Component.literal("[" + bar + "] " + percent + "%")));
    }

    private void clearUseProgress(ServerPlayer player) {
        player.connection.send(new ClientboundSetActionBarTextPacket(Component.empty()));
    }

'''
text = replace_once(text, insert_before, helper + insert_before, "progress helper")
runtime_path.write_text(text, encoding="utf-8")

mod_text = mod_path.read_text(encoding="utf-8")
mod_text = replace_once(mod_text, 'public static final String VERSION = "1.0.0";', 'public static final String VERSION = "1.0.1";', "mod version")
mod_path.write_text(mod_text, encoding="utf-8")

# ---- Static item/recipe cleanup ----
resource_root = ROOT / "src/main/resources/data/ripperdoc"
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
    raw = json.dumps(data, ensure_ascii=False)
    raw = raw.replace("（サーバー設定値）", "")
    data = json.loads(raw)

    # New items retain the drink animation but the Java runtime toggles at ~1 second.
    def visit(obj):
        if isinstance(obj, dict):
            if "minecraft:consumable" in obj and isinstance(obj["minecraft:consumable"], dict):
                obj["minecraft:consumable"]["consume_seconds"] = 2.0
                obj["minecraft:consumable"]["animation"] = "drink"
                obj["minecraft:consumable"]["sound"] = "minecraft:entity.generic.drink"
            for value in obj.values():
                visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)
    visit(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Moontech lore now documents a three-stage jump.
for rel in ["loot_table/items/moontech.json", "recipe/moontech_upgrade.json"]:
    path = resource_root / rel
    raw = path.read_text(encoding="utf-8")
    raw = raw.replace("空中でSPACE：強化2段ジャンプ", "空中でSPACE：追加2回ジャンプ（合計3段）")
    raw = raw.replace("空中でSPACE：2段ジャンプ", "空中でSPACE：追加2回ジャンプ（合計3段）")
    path.write_text(raw, encoding="utf-8")

# Obsolete datapack-only impulse enchantments are no longer used by the native implementation.
obsolete = resource_root / "enchantment"
if obsolete.exists():
    shutil.rmtree(obsolete)

# Final JSON validation.
for path in (ROOT / "src/main/resources").rglob("*.json"):
    json.loads(path.read_text(encoding="utf-8"))

print("Applied Ripperdoc native v1.0.1 feedback patch")
