package jp.km.minecraft;

import net.minecraft.server.MinecraftServer;

/** Java-owned runtime driver for bundled KM server data resources. */
public final class KMRuntime {
    private KMRuntime() {}

    public static void onServerStarted(MinecraftServer server) {
        runSilent(server, "function km-minecraft:core/load");
    }

    public static void onServerTick(MinecraftServer server) {
        runSilent(server, "function km-minecraft:core/tick");
    }

    /**
     * Execute internal KM commands without sending command feedback to the server console.
     * The old implementation used the normal server command source and printed
     * "Running function km-minecraft:core/tick" every tick.
     */
    private static void runSilent(MinecraftServer server, String command) {
        server.getCommands().performPrefixedCommand(
                server.createCommandSourceStack().withSuppressedOutput(),
                command
        );
    }
}
