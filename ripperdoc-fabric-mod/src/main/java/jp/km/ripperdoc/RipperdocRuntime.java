package jp.km.ripperdoc;

import net.minecraft.server.MinecraftServer;

/**
 * Java-owned runtime bridge for the legacy-compatible Ripperdoc function resources.
 * Internal execution is deliberately silent to avoid flooding the dedicated-server log.
 */
public final class RipperdocRuntime {
    private RipperdocRuntime() {}

    public static void onServerStarted(MinecraftServer server) {
        runSilent(server, "function ripperdoc:load");
    }

    public static void onServerTick(MinecraftServer server) {
        runSilent(server, "function ripperdoc:tick");
    }

    private static void runSilent(MinecraftServer server, String command) {
        server.getCommands().performPrefixedCommand(
                server.createCommandSourceStack().withSuppressedOutput(),
                command
        );
    }
}
