package jp.km.ripperdoc;

import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.Container;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;

public final class RipperdocItems {
    public static final String ZANDEVISTAN = "zandevistan";
    public static final String BERSERK = "berserk";
    public static final String AQUATIC = "aquatic";
    public static final String MOONTECH_CORE = "moontech_core";
    public static final String MOONTECH = "moontech";

    private RipperdocItems() {}

    public static String id(ItemStack stack) {
        if (stack == null || stack.isEmpty()) return "";
        CustomData data = stack.get(DataComponents.CUSTOM_DATA);
        if (data == null) return "";
        return data.copyTag().getStringOr("ripperdoc_id", "");
    }

    public static boolean is(ItemStack stack, String id) {
        return id.equals(id(stack));
    }

    public static boolean isTimedImplant(ItemStack stack) {
        String id = id(stack);
        return ZANDEVISTAN.equals(id) || BERSERK.equals(id) || AQUATIC.equals(id);
    }

    public static boolean hasPlayerOwned(ServerPlayer player, String wanted) {
        if (player.getInventory().contains(stack -> is(stack, wanted))) return true;
        if (is(player.containerMenu.getCarried(), wanted)) return true;
        Container craft = player.inventoryMenu.getCraftSlots();
        for (int i = 0; i < craft.getContainerSize(); i++) {
            if (is(craft.getItem(i), wanted)) return true;
        }
        return false;
    }

    public static boolean syncPlayerVisuals(ServerPlayer player, RipperdocRuntime.PlayerState state) {
        boolean changed = false;
        for (int i = 0; i < player.getInventory().getContainerSize(); i++) {
            ItemStack stack = player.getInventory().getItem(i);
            changed |= syncImplantVisual(stack, desiredState(id(stack), state));
        }
        Container craft = player.inventoryMenu.getCraftSlots();
        for (int i = 0; i < craft.getContainerSize(); i++) {
            ItemStack stack = craft.getItem(i);
            changed |= syncImplantVisual(stack, desiredState(id(stack), state));
        }
        ItemStack carried = player.containerMenu.getCarried();
        changed |= syncImplantVisual(carried, desiredState(id(carried), state));

        if (changed) {
            player.getInventory().setChanged();
            player.inventoryMenu.broadcastChanges();
            if (player.containerMenu != player.inventoryMenu) player.containerMenu.broadcastChanges();
        }
        return changed;
    }

    public static boolean normalizeDropped(ItemEntity entity) {
        ItemStack original = entity.getItem();
        if (!isTimedImplant(original)) return false;
        ItemStack copy = original.copy();
        if (!syncImplantVisual(copy, false)) return false;
        entity.setItem(copy);
        return true;
    }

    private static boolean desiredState(String id, RipperdocRuntime.PlayerState state) {
        return switch (id) {
            case ZANDEVISTAN -> state.zandeTicks > 0;
            case BERSERK -> state.berserkTicks > 0;
            case AQUATIC -> state.aquaticTicks > 0;
            default -> false;
        };
    }

    public static boolean syncImplantVisual(ItemStack stack, boolean active) {
        String id = id(stack);
        if (!(ZANDEVISTAN.equals(id) || BERSERK.equals(id) || AQUATIC.equals(id))) return false;

        Identifier wantedModel = Identifier.parse("ripperdoc:" + id + (active ? "_active" : ""));
        CustomData custom = stack.getOrDefault(DataComponents.CUSTOM_DATA, CustomData.EMPTY);
        CompoundTag tag = custom.copyTag();
        boolean currentActive = tag.getBooleanOr("ripperdoc_active", false);
        Identifier currentModel = stack.get(DataComponents.ITEM_MODEL);
        Boolean glint = stack.get(DataComponents.ENCHANTMENT_GLINT_OVERRIDE);
        boolean modelMatches = wantedModel.equals(currentModel);
        boolean glintMatches = Boolean.valueOf(active).equals(glint);
        if (currentActive == active && modelMatches && glintMatches) return false;

        CustomData.update(DataComponents.CUSTOM_DATA, stack, nbt -> {
            if (active) nbt.putBoolean("ripperdoc_active", true);
            else nbt.remove("ripperdoc_active");
        });
        stack.set(DataComponents.ITEM_MODEL, wantedModel);
        stack.set(DataComponents.ENCHANTMENT_GLINT_OVERRIDE, active);
        return true;
    }
}
