package jp.km.ripperdoc;

import com.mojang.brigadier.Command;
import com.mojang.brigadier.arguments.DoubleArgumentType;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;

public final class RipperdocCommands {
    private RipperdocCommands() {}

    public static void register(RipperdocRuntime runtime) {
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> dispatcher.register(
                Commands.literal("ripperdoc")
                        .then(Commands.literal("status").executes(ctx -> status(ctx.getSource(), runtime)))
                        .then(Commands.literal("config")
                                .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
                                .then(Commands.literal("show").executes(ctx -> showConfig(ctx.getSource(), runtime)))
                                .then(Commands.literal("reset").executes(ctx -> resetConfig(ctx.getSource(), runtime)))
                                .then(Commands.literal("zande")
                                        .then(Commands.literal("speed")
                                                .then(Commands.argument("percent", IntegerArgumentType.integer(0, 300))
                                                        .executes(ctx -> setZande(ctx.getSource(), runtime, IntegerArgumentType.getInteger(ctx, "percent"))))))
                                .then(Commands.literal("berserk")
                                        .then(Commands.literal("attack")
                                                .then(Commands.argument("value", DoubleArgumentType.doubleArg(0.0, 100.0))
                                                        .executes(ctx -> setBerserkAttack(ctx.getSource(), runtime, DoubleArgumentType.getDouble(ctx, "value")))))
                                        .then(Commands.literal("mining")
                                                .then(Commands.argument("percent", IntegerArgumentType.integer(0, 500))
                                                        .executes(ctx -> setBerserkMining(ctx.getSource(), runtime, IntegerArgumentType.getInteger(ctx, "percent")))))))
                        .then(Commands.literal("give")
                                .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
                                .then(Commands.literal("zandevistan").executes(ctx -> give(ctx.getSource(), "zandevistan")))
                                .then(Commands.literal("berserk").executes(ctx -> give(ctx.getSource(), "berserk")))
                                .then(Commands.literal("aquatic").executes(ctx -> give(ctx.getSource(), "aquatic")))
                                .then(Commands.literal("moontech_core").executes(ctx -> give(ctx.getSource(), "moontech_core")))
                                .then(Commands.literal("moontech").executes(ctx -> give(ctx.getSource(), "moontech")))
                                .then(Commands.literal("all").executes(ctx -> giveAll(ctx.getSource()))))
        ));
    }

    private static int status(CommandSourceStack source, RipperdocRuntime runtime) throws CommandSyntaxException {
        ServerPlayer player = source.getPlayerOrException();
        RipperdocRuntime.PlayerState state = runtime.state(player);
        source.sendSuccess(() -> Component.literal("[Ripperdoc] Native Fabric v" + RipperdocMod.VERSION + " active"), false);
        source.sendSuccess(() -> Component.literal("ZANDEVISTAN: " + timer(state.zandeTicks)
                + " | BERSERK: " + timer(state.berserkTicks)
                + " | AQUATIC: " + timer(state.aquaticTicks)), false);
        return Command.SINGLE_SUCCESS;
    }

    private static String timer(int ticks) {
        return ticks <= 0 ? "OFF" : ((ticks + 19) / 20) + "s";
    }

    private static int showConfig(CommandSourceStack source, RipperdocRuntime runtime) {
        RipperdocConfig c = runtime.config();
        source.sendSuccess(() -> Component.literal("[Ripperdoc] ZANDEVISTAN speed +" + c.zandeSpeedPercent
                + "% | BERSERK attack +" + trim(c.berserkAttack)
                + " | mining +" + c.berserkMiningPercent + "%"), false);
        return Command.SINGLE_SUCCESS;
    }

    private static int setZande(CommandSourceStack source, RipperdocRuntime runtime, int value) {
        runtime.config().zandeSpeedPercent = value;
        runtime.config().save();
        runtime.refreshConfiguredAttributes(source.getServer());
        source.sendSuccess(() -> Component.literal("[Ripperdoc] ZANDEVISTAN speed = +" + value + "%"), true);
        return Command.SINGLE_SUCCESS;
    }

    private static int setBerserkAttack(CommandSourceStack source, RipperdocRuntime runtime, double value) {
        runtime.config().berserkAttack = value;
        runtime.config().save();
        runtime.refreshConfiguredAttributes(source.getServer());
        source.sendSuccess(() -> Component.literal("[Ripperdoc] BERSERK attack = +" + trim(value)), true);
        return Command.SINGLE_SUCCESS;
    }

    private static int setBerserkMining(CommandSourceStack source, RipperdocRuntime runtime, int value) {
        runtime.config().berserkMiningPercent = value;
        runtime.config().save();
        runtime.refreshConfiguredAttributes(source.getServer());
        source.sendSuccess(() -> Component.literal("[Ripperdoc] BERSERK mining = +" + value + "%"), true);
        return Command.SINGLE_SUCCESS;
    }

    private static int resetConfig(CommandSourceStack source, RipperdocRuntime runtime) {
        runtime.config().reset();
        runtime.refreshConfiguredAttributes(source.getServer());
        source.sendSuccess(() -> Component.literal("[Ripperdoc] Config reset: speed +50%, attack +6, mining +60%"), true);
        return Command.SINGLE_SUCCESS;
    }

    private static int give(CommandSourceStack source, String lootId) throws CommandSyntaxException {
        ServerPlayer player = source.getPlayerOrException();
        runSilent(source.getServer(), source, "loot give " + player.getScoreboardName() + " loot ripperdoc:items/" + lootId);
        return Command.SINGLE_SUCCESS;
    }

    private static int giveAll(CommandSourceStack source) throws CommandSyntaxException {
        give(source, "zandevistan");
        give(source, "berserk");
        give(source, "aquatic");
        give(source, "moontech_core");
        give(source, "moontech");
        return Command.SINGLE_SUCCESS;
    }

    private static void runSilent(MinecraftServer server, CommandSourceStack source, String command) {
        server.getCommands().performPrefixedCommand(source.withSuppressedOutput(), command);
    }

    private static String trim(double value) {
        return value == Math.rint(value) ? Long.toString(Math.round(value)) : Double.toString(value);
    }
}
