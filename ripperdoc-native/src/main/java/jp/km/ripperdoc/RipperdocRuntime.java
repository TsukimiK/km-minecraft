package jp.km.ripperdoc;

import net.minecraft.core.BlockPos;
import net.minecraft.network.protocol.game.ClientboundSetEntityMotionPacket;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.tags.FluidTags;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.Vec3;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

public final class RipperdocRuntime {
    public static final int ABILITY_TICKS = 20 * 60 * 5;
    private static final int USE_HOLD_TICKS = 32;
    private static final int OWNERSHIP_GRACE_CHECKS = 2;
    private static final int OWNERSHIP_CHECK_INTERVAL = 10;
    private static final int VISUAL_FALLBACK_INTERVAL = 40;
    private static final int MOONTECH_SESSION_TIMEOUT = 20 * 60;
    private static final double MOONTECH_JUMP_ADD = 0.265;
    private static final double MOONTECH_SECOND_JUMP_Y = 0.685;
    private static final double NORMAL_JUMP_Y = 0.42;

    private static final Identifier ZANDE_MOD = Identifier.parse("ripperdoc:zandevistan");
    private static final Identifier BERSERK_DAMAGE_MOD = Identifier.parse("ripperdoc:berserk_damage");
    private static final Identifier BERSERK_MINING_MOD = Identifier.parse("ripperdoc:berserk_mining");
    private static final Identifier MOONTECH_JUMP_MOD = Identifier.parse("ripperdoc:moontech_jump");
    private static final Identifier MOONTECH_FALL_MOD = Identifier.parse("ripperdoc:moontech_fall");
    private static final Identifier AQUATIC_GRAVITY_MOD = Identifier.parse("ripperdoc:aquatic_surface_gravity");

    private static final Set<String> LEGACY_TAGS = Set.of(
            "rd_zande", "rd_berserk", "rd_aqua", "rd_moontech", "rd_moon_fall", "rd_jump_held",
            "rd_aqsurf", "rd_aq_onwater", "rd_aq_landing", "rd_toggle_off", "rd_use_offhand"
    );

    private final Map<UUID, PlayerState> states = new HashMap<>();
    private RipperdocConfig config;
    private int visualFallbackTicker;

    public void onServerStarted(MinecraftServer server) {
        states.clear();
        config = RipperdocConfig.loadOrMigrate(server);
        // Remove any helper platforms left by the old datapack. The native implementation never creates them.
        runSilent(server, "kill @e[type=minecraft:shulker,tag=rd_aq_platform]");
        for (ServerPlayer player : server.getPlayerList().getPlayers()) onJoin(player);
        RipperdocMod.LOGGER.info("Native runtime ready. No datapack tick/function runtime is used.");
    }

    public void onServerStopping(MinecraftServer server) {
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            PlayerState state = states.get(player.getUUID());
            if (state != null) {
                disableAll(player, state);
                cleanupAttributeModifiers(player);
                RipperdocItems.syncPlayerVisuals(player, state);
            }
        }
    }

    public void onJoin(ServerPlayer player) {
        PlayerState existing = states.get(player.getUUID());
        if (existing != null) {
            cleanupAttributeModifiers(player);

            // A disconnected player's transient modifiers no longer exist on the new player instance.
            // Re-evaluate boots and re-apply only the native modifiers represented by in-memory state.
            existing.moontechEquipped = false;
            existing.aquaticOnSurface = false;
            updateMoontechEquip(player, existing);
            reapplyFromState(player, existing);
            existing.visualDirty = true;
            syncVisualsIfNeeded(player, existing, true);
            return;
        }

        PlayerState state = new PlayerState();
        states.put(player.getUUID(), state);
        cleanupLegacyPlayer(player);
        updateMoontechEquip(player, state);
        state.visualDirty = true;
        syncVisualsIfNeeded(player, state, true);
    }

    public void onDisconnect(ServerPlayer player) {
        // Timers remain in memory and therefore pause while the player is offline, matching the datapack behavior.
        PlayerState state = states.get(player.getUUID());
        if (state != null) state.aquaticOnSurface = false;
        cleanupAttributeModifiers(player);
    }

    public void onDeath(ServerPlayer player) {
        PlayerState state = states.computeIfAbsent(player.getUUID(), id -> new PlayerState());
        disableAll(player, state);
        state.resetMovementSession();
        state.visualDirty = true;
        syncVisualsIfNeeded(player, state, true);
    }

    public void onTick(MinecraftServer server) {
        visualFallbackTicker++;
        boolean fallbackVisualPass = visualFallbackTicker >= VISUAL_FALLBACK_INTERVAL;
        if (fallbackVisualPass) visualFallbackTicker = 0;

        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            PlayerState state = states.computeIfAbsent(player.getUUID(), id -> new PlayerState());
            tickUse(player, state);
            tickTimedAbilities(player, state);
            tickMoontech(player, state);
            tickAquatic(player, state);
            syncVisualsIfNeeded(player, state, fallbackVisualPass);
            state.previousOnGround = player.onGround();
        }
    }

    private void tickUse(ServerPlayer player, PlayerState state) {
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

        // Legacy items deliberately have a 60-second consumable. Stop at 32 ticks, before vanilla can consume them.
        player.stopUsingItem();
        toggleTimedAbility(player, state, currentId);
        state.useId = "";
        state.useHoldTicks = 0;
        state.visualDirty = true;
    }

    private void toggleTimedAbility(ServerPlayer player, PlayerState state, String id) {
        switch (id) {
            case RipperdocItems.ZANDEVISTAN -> {
                if (state.zandeTicks > 0) disableZande(player, state);
                else enableZande(player, state);
            }
            case RipperdocItems.BERSERK -> {
                if (state.berserkTicks > 0) disableBerserk(player, state);
                else enableBerserk(player, state);
            }
            case RipperdocItems.AQUATIC -> {
                if (state.aquaticTicks > 0) disableAquatic(player, state);
                else {
                    state.aquaticTicks = ABILITY_TICKS;
                    state.aquaticMissingChecks = 0;
                    state.visualDirty = true;
                }
            }
            default -> { }
        }
    }

    private void tickTimedAbilities(ServerPlayer player, PlayerState state) {
        if (state.zandeTicks > 0 && --state.zandeTicks <= 0) disableZande(player, state);
        if (state.berserkTicks > 0 && --state.berserkTicks <= 0) disableBerserk(player, state);
        if (state.aquaticTicks > 0 && --state.aquaticTicks <= 0) disableAquatic(player, state);

        state.ownershipTicker++;
        if (state.ownershipTicker < OWNERSHIP_CHECK_INTERVAL) return;
        state.ownershipTicker = 0;

        if (state.zandeTicks > 0) {
            state.zandeMissingChecks = RipperdocItems.hasPlayerOwned(player, RipperdocItems.ZANDEVISTAN) ? 0 : state.zandeMissingChecks + 1;
            if (state.zandeMissingChecks >= OWNERSHIP_GRACE_CHECKS) disableZande(player, state);
        }
        if (state.berserkTicks > 0) {
            state.berserkMissingChecks = RipperdocItems.hasPlayerOwned(player, RipperdocItems.BERSERK) ? 0 : state.berserkMissingChecks + 1;
            if (state.berserkMissingChecks >= OWNERSHIP_GRACE_CHECKS) disableBerserk(player, state);
        }
        if (state.aquaticTicks > 0) {
            state.aquaticMissingChecks = RipperdocItems.hasPlayerOwned(player, RipperdocItems.AQUATIC) ? 0 : state.aquaticMissingChecks + 1;
            if (state.aquaticMissingChecks >= OWNERSHIP_GRACE_CHECKS) disableAquatic(player, state);
        }
    }

    private void enableZande(ServerPlayer player, PlayerState state) {
        state.zandeTicks = ABILITY_TICKS;
        state.zandeMissingChecks = 0;
        state.visualDirty = true;
        applyZande(player);
    }

    private void disableZande(ServerPlayer player, PlayerState state) {
        state.zandeTicks = 0;
        state.zandeMissingChecks = 0;
        state.visualDirty = true;
        removeModifier(player, Attributes.MOVEMENT_SPEED, ZANDE_MOD);
    }

    private void enableBerserk(ServerPlayer player, PlayerState state) {
        state.berserkTicks = ABILITY_TICKS;
        state.berserkMissingChecks = 0;
        state.visualDirty = true;
        applyBerserk(player);
    }

    private void disableBerserk(ServerPlayer player, PlayerState state) {
        state.berserkTicks = 0;
        state.berserkMissingChecks = 0;
        state.visualDirty = true;
        removeModifier(player, Attributes.ATTACK_DAMAGE, BERSERK_DAMAGE_MOD);
        removeModifier(player, Attributes.BLOCK_BREAK_SPEED, BERSERK_MINING_MOD);
    }

    private void disableAquatic(ServerPlayer player, PlayerState state) {
        state.aquaticTicks = 0;
        state.aquaticMissingChecks = 0;
        state.visualDirty = true;
        disableAquaticSurface(player, state);
    }

    private void applyZande(ServerPlayer player) {
        AttributeInstance speed = player.getAttribute(Attributes.MOVEMENT_SPEED);
        if (speed == null) return;
        speed.removeModifier(ZANDE_MOD);
        speed.addTransientModifier(new AttributeModifier(ZANDE_MOD, config.zandeMultiplier(), AttributeModifier.Operation.ADD_MULTIPLIED_BASE));
    }

    private void applyBerserk(ServerPlayer player) {
        AttributeInstance attack = player.getAttribute(Attributes.ATTACK_DAMAGE);
        AttributeInstance mining = player.getAttribute(Attributes.BLOCK_BREAK_SPEED);
        if (attack != null) {
            attack.removeModifier(BERSERK_DAMAGE_MOD);
            attack.addTransientModifier(new AttributeModifier(BERSERK_DAMAGE_MOD, config.berserkAttack, AttributeModifier.Operation.ADD_VALUE));
        }
        if (mining != null) {
            mining.removeModifier(BERSERK_MINING_MOD);
            mining.addTransientModifier(new AttributeModifier(BERSERK_MINING_MOD, config.berserkMiningMultiplier(), AttributeModifier.Operation.ADD_MULTIPLIED_BASE));
        }
    }

    private void tickMoontech(ServerPlayer player, PlayerState state) {
        updateMoontechEquip(player, state);
        boolean jump = player.getLastClientInput().jump();
        if (!state.moontechEquipped) {
            state.previousJumpInput = jump;
            return;
        }

        boolean jumpEdge = jump && !state.previousJumpInput;
        state.previousJumpInput = jump;
        if (player.onGround()) state.airTicks = 0;
        else state.airTicks++;

        if (jumpEdge && (player.onGround() || state.previousOnGround)) {
            startMoontechFallSession(player, state);
        } else if (jumpEdge && state.moonFallSession && !state.secondJumpUsed && state.airTicks >= 2 && canAirJump(player)) {
            performSecondJump(player, state);
        }

        if (state.moonFallSession) {
            state.moonAge++;
            if (player.onGround()) state.moonGroundTicks++;
            else state.moonGroundTicks = 0;
            if (state.moonGroundTicks >= 3 || state.moonAge >= MOONTECH_SESSION_TIMEOUT || !canMaintainMoonSession(player)) {
                endMoontechFallSession(player, state);
            }
        }
    }

    private void updateMoontechEquip(ServerPlayer player, PlayerState state) {
        boolean equipped = RipperdocItems.is(player.getItemBySlot(EquipmentSlot.FEET), RipperdocItems.MOONTECH);
        if (equipped == state.moontechEquipped) return;
        state.moontechEquipped = equipped;
        AttributeInstance jump = player.getAttribute(Attributes.JUMP_STRENGTH);
        if (jump != null) {
            jump.removeModifier(MOONTECH_JUMP_MOD);
            if (equipped) {
                jump.addTransientModifier(new AttributeModifier(MOONTECH_JUMP_MOD, MOONTECH_JUMP_ADD, AttributeModifier.Operation.ADD_VALUE));
            }
        }
        if (!equipped) endMoontechFallSession(player, state);
    }

    private void startMoontechFallSession(ServerPlayer player, PlayerState state) {
        state.moonFallSession = true;
        state.secondJumpUsed = false;
        state.moonGroundTicks = 0;
        state.moonAge = 0;
        applyMoontechFallProtection(player);
    }

    private void applyMoontechFallProtection(ServerPlayer player) {
        AttributeInstance fall = player.getAttribute(Attributes.FALL_DAMAGE_MULTIPLIER);
        if (fall == null) return;
        fall.removeModifier(MOONTECH_FALL_MOD);
        fall.addTransientModifier(new AttributeModifier(MOONTECH_FALL_MOD, -1.0, AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL));
    }

    private void endMoontechFallSession(ServerPlayer player, PlayerState state) {
        state.moonFallSession = false;
        state.secondJumpUsed = false;
        state.moonGroundTicks = 0;
        state.moonAge = 0;
        state.airTicks = 0;
        removeModifier(player, Attributes.FALL_DAMAGE_MULTIPLIER, MOONTECH_FALL_MOD);
    }

    private void performSecondJump(ServerPlayer player, PlayerState state) {
        Vec3 velocity = player.getDeltaMovement();
        player.setDeltaMovement(velocity.x, MOONTECH_SECOND_JUMP_Y, velocity.z);
        player.resetFallDistance();
        player.setOnGround(false);
        player.connection.send(new ClientboundSetEntityMotionPacket(player));
        state.secondJumpUsed = true;
    }

    private boolean canAirJump(ServerPlayer player) {
        return !player.isInWater() && !player.isInLava() && !player.onClimbable() && !player.isPassenger() && !player.isFallFlying();
    }

    private boolean canMaintainMoonSession(ServerPlayer player) {
        return !player.isInWater() && !player.isInLava() && !player.onClimbable() && !player.isPassenger() && !player.isFallFlying();
    }

    private void tickAquatic(ServerPlayer player, PlayerState state) {
        boolean jump = player.getLastClientInput().jump();
        if (state.aquaticTicks <= 0 || player.isPassenger() || player.isFallFlying() || player.isInLava()) {
            disableAquaticSurface(player, state);
            state.previousAquaticJump = jump;
            return;
        }

        Double surfaceY = findWaterSurface(player);
        if (surfaceY == null) {
            disableAquaticSurface(player, state);
            state.previousAquaticJump = jump;
            return;
        }

        Vec3 velocity = player.getDeltaMovement();
        double nextY = player.getY() + velocity.y;
        boolean directSurface = player.getY() >= surfaceY - 0.15 && player.getY() <= surfaceY + 0.35;
        boolean landingCrossesSurface = velocity.y <= 0.0 && player.getY() > surfaceY && nextY <= surfaceY + 0.15;
        if (!(directSurface || landingCrossesSurface)) {
            disableAquaticSurface(player, state);
            state.previousAquaticJump = jump;
            return;
        }

        enableAquaticSurface(player, state);
        if (player.getY() < surfaceY - 0.08 || landingCrossesSurface) {
            player.setPos(player.getX(), surfaceY + 0.001, player.getZ());
        }
        player.setDeltaMovement(velocity.x, 0.0, velocity.z);
        player.resetFallDistance();
        player.setOnGround(true);
        player.connection.send(new ClientboundSetEntityMotionPacket(player));

        boolean jumpEdge = jump && !state.previousAquaticJump;
        state.previousAquaticJump = jump;
        if (jumpEdge) {
            disableAquaticSurface(player, state);
            double jumpY = state.moontechEquipped ? MOONTECH_SECOND_JUMP_Y : NORMAL_JUMP_Y;
            player.setDeltaMovement(velocity.x, jumpY, velocity.z);
            player.setOnGround(false);
            player.connection.send(new ClientboundSetEntityMotionPacket(player));
            if (state.moontechEquipped) startMoontechFallSession(player, state);
        }
    }

    private Double findWaterSurface(ServerPlayer player) {
        ServerLevel level = player.level();
        BlockPos feet = BlockPos.containing(player.getX(), player.getY() + 0.05, player.getZ());
        // If feet are already inside water, let vanilla swimming take over instead of snapping upward.
        if (level.getFluidState(feet).is(FluidTags.WATER)) return null;

        for (int i = 0; i <= 4; i++) {
            BlockPos water = BlockPos.containing(player.getX(), player.getY() - 0.08 - i, player.getZ());
            if (!level.getFluidState(water).is(FluidTags.WATER)) continue;
            if (level.getFluidState(water.above()).is(FluidTags.WATER)) continue;
            return water.getY() + 1.0;
        }
        return null;
    }

    private void enableAquaticSurface(ServerPlayer player, PlayerState state) {
        state.aquaticOnSurface = true;
        AttributeInstance gravity = player.getAttribute(Attributes.GRAVITY);
        if (gravity != null && !gravity.hasModifier(AQUATIC_GRAVITY_MOD)) {
            gravity.addTransientModifier(new AttributeModifier(AQUATIC_GRAVITY_MOD, -1.0, AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL));
        }
    }

    private void disableAquaticSurface(ServerPlayer player, PlayerState state) {
        if (!state.aquaticOnSurface) return;
        state.aquaticOnSurface = false;
        removeModifier(player, Attributes.GRAVITY, AQUATIC_GRAVITY_MOD);
    }

    private void cleanupLegacyPlayer(ServerPlayer player) {
        cleanupAttributeModifiers(player);
        for (String tag : LEGACY_TAGS) player.removeTag(tag);
        PlayerState state = states.get(player.getUUID());
        if (state != null) state.clearAbilities();
    }

    private void cleanupAttributeModifiers(ServerPlayer player) {
        removeModifier(player, Attributes.MOVEMENT_SPEED, ZANDE_MOD);
        removeModifier(player, Attributes.ATTACK_DAMAGE, BERSERK_DAMAGE_MOD);
        removeModifier(player, Attributes.BLOCK_BREAK_SPEED, BERSERK_MINING_MOD);
        removeModifier(player, Attributes.JUMP_STRENGTH, MOONTECH_JUMP_MOD);
        removeModifier(player, Attributes.FALL_DAMAGE_MULTIPLIER, MOONTECH_FALL_MOD);
        removeModifier(player, Attributes.GRAVITY, AQUATIC_GRAVITY_MOD);
    }

    private void reapplyFromState(ServerPlayer player, PlayerState state) {
        if (state.zandeTicks > 0) applyZande(player);
        if (state.berserkTicks > 0) applyBerserk(player);
        if (state.moonFallSession && state.moontechEquipped) applyMoontechFallProtection(player);
    }

    private void disableAll(ServerPlayer player, PlayerState state) {
        disableZande(player, state);
        disableBerserk(player, state);
        disableAquatic(player, state);
        endMoontechFallSession(player, state);
    }

    private void syncVisualsIfNeeded(ServerPlayer player, PlayerState state, boolean fallback) {
        int inventoryChange = player.getInventory().getTimesChanged();
        if (!state.visualDirty && !fallback && inventoryChange == state.lastInventoryChange) return;
        RipperdocItems.syncPlayerVisuals(player, state);
        state.lastInventoryChange = player.getInventory().getTimesChanged();
        state.visualDirty = false;
    }

    private static void removeModifier(ServerPlayer player, net.minecraft.core.Holder<net.minecraft.world.entity.ai.attributes.Attribute> attribute, Identifier id) {
        AttributeInstance instance = player.getAttribute(attribute);
        if (instance != null) instance.removeModifier(id);
    }

    private static void runSilent(MinecraftServer server, String command) {
        server.getCommands().performPrefixedCommand(server.createCommandSourceStack().withSuppressedOutput(), command);
    }

    public void refreshConfiguredAttributes(MinecraftServer server) {
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            PlayerState state = states.get(player.getUUID());
            if (state == null) continue;
            if (state.zandeTicks > 0) applyZande(player);
            if (state.berserkTicks > 0) applyBerserk(player);
        }
    }

    public RipperdocConfig config() { return config; }
    public PlayerState state(ServerPlayer player) { return states.computeIfAbsent(player.getUUID(), id -> new PlayerState()); }

    public static final class PlayerState {
        public int zandeTicks;
        public int berserkTicks;
        public int aquaticTicks;
        int zandeMissingChecks;
        int berserkMissingChecks;
        int aquaticMissingChecks;
        int ownershipTicker;
        String useId = "";
        int useHoldTicks;
        boolean moontechEquipped;
        boolean moonFallSession;
        boolean secondJumpUsed;
        int moonGroundTicks;
        int moonAge;
        int airTicks;
        boolean previousJumpInput;
        boolean previousAquaticJump;
        boolean previousOnGround;
        boolean aquaticOnSurface;
        int lastInventoryChange = -1;
        boolean visualDirty = true;

        void clearAbilities() {
            zandeTicks = berserkTicks = aquaticTicks = 0;
            zandeMissingChecks = berserkMissingChecks = aquaticMissingChecks = 0;
            ownershipTicker = 0;
            useId = "";
            useHoldTicks = 0;
            visualDirty = true;
            resetMovementSession();
        }

        void resetMovementSession() {
            moonFallSession = false;
            secondJumpUsed = false;
            moonGroundTicks = 0;
            moonAge = 0;
            airTicks = 0;
            previousJumpInput = false;
            previousAquaticJump = false;
            aquaticOnSurface = false;
        }
    }
}
