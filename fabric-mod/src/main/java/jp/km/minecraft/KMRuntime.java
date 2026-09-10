package jp.km.minecraft;

import net.minecraft.server.MinecraftServer;

/** Java-owned runtime driver for bundled KM server data resources. */
public final class KMRuntime {
    private KMRuntime() {}

    public static void onServerStarted(MinecraftServer server) {
        run(server, "function km-minecraft:core/load");
    }

    public static void onServerTick(MinecraftServer server) {
        run(server, "function km-minecraft:core/tick");
    }

    private static void run(MinecraftServer server, String command) {
        server.getCommands().performPrefixedCommand(server.createCommandSourceStack(), command);
    }
}
