package jp.km.ripperdoc;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.item.ItemEntity;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public final class RipperdocMod implements ModInitializer {
    public static final String MOD_ID = "ripperdoc-server";
    public static final String VERSION = "1.0.0";
    public static final Logger LOGGER = LoggerFactory.getLogger("Ripperdoc Server");
    public static final RipperdocRuntime RUNTIME = new RipperdocRuntime();

    @Override
    public void onInitialize() {
        LOGGER.info("Ripperdoc native Fabric entrypoint active - v{}", VERSION);
        RipperdocCommands.register(RUNTIME);

        ServerLifecycleEvents.SERVER_STARTED.register(RUNTIME::onServerStarted);
        ServerLifecycleEvents.SERVER_STOPPING.register(RUNTIME::onServerStopping);
        ServerTickEvents.END_SERVER_TICK.register(RUNTIME::onTick);

        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> RUNTIME.onJoin(handler.getPlayer()));
        ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> RUNTIME.onDisconnect(handler.getPlayer()));

        ServerLivingEntityEvents.AFTER_DEATH.register((entity, source) -> {
            if (entity instanceof ServerPlayer player) RUNTIME.onDeath(player);
        });

        ServerEntityEvents.ENTITY_LOAD.register((entity, level) -> {
            if (entity instanceof ItemEntity itemEntity) {
                RipperdocItems.normalizeDropped(itemEntity);
            } else if (entity.entityTags().contains("rd_aq_platform")) {
                entity.discard();
            }
        });
    }
}
