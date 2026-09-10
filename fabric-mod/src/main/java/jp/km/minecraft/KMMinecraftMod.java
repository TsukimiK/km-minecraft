package jp.km.minecraft;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;

/**
 * KM Minecraft Fabric server mod bootstrap.
 *
 * <p>The former external datapack is replaced by resources bundled in this mod JAR.
 * Existing KM item data, resource identifiers and placed crop entity tags are kept
 * compatible so an existing world can be migrated without recreating KM content.</p>
 */
public final class KMMinecraftMod implements ModInitializer {
    public static final String MOD_ID = "km-minecraft";
    public static final String VERSION = "2.1.0";

    @Override
    public void onInitialize() {
        System.out.println("[KM Minecraft] Fabric entrypoint active - v" + VERSION);

        KMCommands.register();

        ServerLifecycleEvents.SERVER_STARTED.register(server -> {
            System.out.println("[KM Minecraft] Server started; initializing KM runtime.");
            KMRuntime.onServerStarted(server);
        });

        ServerTickEvents.END_SERVER_TICK.register(KMRuntime::onServerTick);
    }
}
