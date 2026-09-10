package jp.km.minecraft;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;

/**
 * KM Minecraft Fabric server mod bootstrap.
 *
 * <p>The old external datapack is not required. Gameplay data is bundled in the mod JAR,
 * while Java owns initialization, command registration and tick dispatch.</p>
 */
public final class KMMinecraftMod implements ModInitializer {
    public static final String MOD_ID = "km-minecraft";
    public static final String VERSION = "2.0.2";

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
