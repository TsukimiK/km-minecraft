from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
items_path = ROOT / "src/main/java/jp/km/ripperdoc/RipperdocItems.java"
mod_path = ROOT / "src/main/java/jp/km/ripperdoc/RipperdocMod.java"
resource_root = ROOT / "src/main/resources/data/ripperdoc"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 match, found {count}")
    return text.replace(old, new, 1)


# ---------------------------------------------------------------------------
# Normalize MOONTECH lore on existing items as well as newly-created items.
# This is intentionally folded into the existing low-frequency visual sync path,
# so there is no new per-tick inventory scan or packet loop.
# ---------------------------------------------------------------------------
items = items_path.read_text(encoding="utf-8")

if "import net.minecraft.ChatFormatting;" not in items:
    items = replace_once(
        items,
        "import net.minecraft.core.component.DataComponents;",
        "import net.minecraft.ChatFormatting;\nimport net.minecraft.core.component.DataComponents;",
        "ChatFormatting import",
    )
if "import net.minecraft.network.chat.Component;" not in items:
    items = replace_once(
        items,
        "import net.minecraft.nbt.CompoundTag;",
        "import net.minecraft.nbt.CompoundTag;\nimport net.minecraft.network.chat.Component;",
        "Component import",
    )
if "import net.minecraft.world.item.component.ItemLore;" not in items:
    items = replace_once(
        items,
        "import net.minecraft.world.item.component.CustomData;",
        "import net.minecraft.world.item.component.CustomData;\nimport net.minecraft.world.item.component.ItemLore;\n\nimport java.util.List;",
        "ItemLore import",
    )

items = replace_once(
    items,
    "            case BERSERK -> syncImplantVisual(stack, state.berserkTicks > 0, state.berserkTicks);\n            default -> false;",
    "            case BERSERK -> syncImplantVisual(stack, state.berserkTicks > 0, state.berserkTicks);\n            case MOONTECH -> syncMoontechLore(stack);\n            default -> false;",
    "Moontech sync switch",
)

marker = "    public static boolean normalizeDropped(ItemEntity entity) {"
helper = '''    private static final ItemLore MOONTECH_RELEASE_LORE = new ItemLore(List.of(
            Component.literal("SPACE：通常ジャンプ").withStyle(style -> style.withColor(ChatFormatting.GRAY).withItalic(false)),
            Component.literal("SHIFT + SPACE：高ジャンプ（約3ブロック）").withStyle(style -> style.withColor(ChatFormatting.GRAY).withItalic(false)),
            Component.literal("空中でSPACE：2段目ジャンプ（1回のみ）").withStyle(style -> style.withColor(ChatFormatting.GRAY).withItalic(false)),
            Component.literal("MOONTECHジャンプ後：落下ダメージ無効").withStyle(style -> style.withColor(ChatFormatting.GRAY).withItalic(false))
    ));

    private static boolean syncMoontechLore(ItemStack stack) {
        ItemLore current = stack.get(DataComponents.LORE);
        if (MOONTECH_RELEASE_LORE.equals(current)) return false;
        stack.set(DataComponents.LORE, MOONTECH_RELEASE_LORE);
        return true;
    }

'''
items = replace_once(items, marker, helper + marker, "Moontech lore helper")
items_path.write_text(items, encoding="utf-8")


# ---------------------------------------------------------------------------
# Static loot/recipe outputs use the same final release wording.
# ---------------------------------------------------------------------------
moon_lore = [
    {"text": "SPACE：通常ジャンプ", "italic": False, "color": "gray"},
    {"text": "SHIFT + SPACE：高ジャンプ（約3ブロック）", "italic": False, "color": "gray"},
    {"text": "空中でSPACE：2段目ジャンプ（1回のみ）", "italic": False, "color": "gray"},
    {"text": "MOONTECHジャンプ後：落下ダメージ無効", "italic": False, "color": "gray"},
]

for rel in ["loot_table/items/moontech.json", "recipe/moontech_upgrade.json"]:
    path = resource_root / rel
    data = json.loads(path.read_text(encoding="utf-8"))

    def patch(obj):
        if isinstance(obj, dict):
            custom = obj.get("minecraft:custom_data")
            if isinstance(custom, dict) and custom.get("ripperdoc_id") == "moontech" and "minecraft:lore" in obj:
                obj["minecraft:lore"] = moon_lore
            for child in obj.values():
                patch(child)
        elif isinstance(obj, list):
            for child in obj:
                patch(child)

    patch(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Release version label.
mod = mod_path.read_text(encoding="utf-8")
mod = replace_once(mod, 'public static final String VERSION = "1.0.3";', 'public static final String VERSION = "1.0.4";', "release version")
mod_path.write_text(mod, encoding="utf-8")

# Validate generated JSON.
for path in (ROOT / "src/main/resources").rglob("*.json"):
    json.loads(path.read_text(encoding="utf-8"))

print("Applied Ripperdoc native v1.0.4 release patch")
