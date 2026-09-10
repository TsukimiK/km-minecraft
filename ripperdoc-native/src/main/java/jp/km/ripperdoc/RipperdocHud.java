package jp.km.ripperdoc;

import net.minecraft.core.Holder;
import net.minecraft.network.protocol.game.ClientboundRemoveMobEffectPacket;
import net.minecraft.network.protocol.game.ClientboundUpdateMobEffectPacket;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;

/**
 * Lightweight server-only HUD bridge.
 *
 * The vanilla client cannot render a brand-new custom status-effect icon without a client mod.
 * Instead we send three display-only vanilla effect packets. The effects are NOT added to the
 * server-side player, so they never grant gameplay benefits. The client counts the duration down
 * by itself; we only resync occasionally or when an ability changes state.
 */
public final class RipperdocHud {
    private static final int RESYNC_INTERVAL_TICKS = 20 * 30;

    // Chosen because these do not affect client movement/physics. They are display proxies only.
    private static final Holder<MobEffect> ZANDE_ICON = MobEffects.LUCK;
    private static final Holder<MobEffect> BERSERK_ICON = MobEffects.UNLUCK;
    private static final Holder<MobEffect> AQUATIC_ICON = MobEffects.HERO_OF_THE_VILLAGE;

    private RipperdocHud() {}

    public static void tick(ServerPlayer player, RipperdocRuntime.PlayerState state) {
        boolean force = ++state.hudResyncTicker >= RESYNC_INTERVAL_TICKS;
        if (force) state.hudResyncTicker = 0;

        boolean zande = state.zandeTicks > 0;
        boolean berserk = state.berserkTicks > 0;
        boolean aquatic = state.aquaticTicks > 0;

        if (force || zande != state.hudZandeVisible) {
            syncOne(player, ZANDE_ICON, zande, state.zandeTicks);
            state.hudZandeVisible = zande;
        }
        if (force || berserk != state.hudBerserkVisible) {
            syncOne(player, BERSERK_ICON, berserk, state.berserkTicks);
            state.hudBerserkVisible = berserk;
        }
        if (force || aquatic != state.hudAquaticVisible) {
            syncOne(player, AQUATIC_ICON, aquatic, state.aquaticTicks);
            state.hudAquaticVisible = aquatic;
        }
    }

    public static void forceSync(ServerPlayer player, RipperdocRuntime.PlayerState state) {
        state.hudResyncTicker = 0;
        syncOne(player, ZANDE_ICON, state.zandeTicks > 0, state.zandeTicks);
        syncOne(player, BERSERK_ICON, state.berserkTicks > 0, state.berserkTicks);
        syncOne(player, AQUATIC_ICON, state.aquaticTicks > 0, state.aquaticTicks);
        state.hudZandeVisible = state.zandeTicks > 0;
        state.hudBerserkVisible = state.berserkTicks > 0;
        state.hudAquaticVisible = state.aquaticTicks > 0;
    }

    private static void syncOne(ServerPlayer player, Holder<MobEffect> effect, boolean active, int ticks) {
        if (active) {
            // No particles, icon visible. Duration is handled locally by the vanilla client.
            MobEffectInstance display = new MobEffectInstance(effect, Math.max(20, ticks), 0, false, false, true);
            player.connection.send(new ClientboundUpdateMobEffectPacket(player.getId(), display, false));
            return;
        }

        // If the player genuinely has the vanilla effect we borrowed as an icon, restore its
        // real server state instead of hiding it on the client.
        MobEffectInstance real = player.getEffect(effect);
        if (real != null) {
            player.connection.send(new ClientboundUpdateMobEffectPacket(player.getId(), real, false));
        } else {
            player.connection.send(new ClientboundRemoveMobEffectPacket(player.getId(), effect));
        }
    }
}
