package jp.km.ripperdoc;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;

/**
 * Fabric server entrypoint for Ripperdoc Cyberware.
 *
 * <p>The original datapack resources are bundled in the final mod JAR. Java owns
 * startup, ticking and debug/admin command registration so no external Ripperdoc
 * datapack is required.</p>
 */
public final class RipperdocMod implements ModInitializer {
    public static final String MOD_ID = "ripperdoc-servermod";
    public static final String VERSION = "1.1.0";

    @Override
    public void onInitialize() {
        System.out.println("[Ripperdoc] Fabric server entrypoint active - v" + VERSION);

        RipperdocCommands.register();

        ServerLifecycleEvents.SERVER_STARTED.register(server -> {
            System.out.println("[Ripperdoc] Server started; initializing compatible Ripperdoc runtime.");
            RipperdocRuntime.onServerStarted(server);
        });

        ServerTickEvents.END_SERVER_TICK.register(RipperdocRuntime::onServerTick);
    }
}
