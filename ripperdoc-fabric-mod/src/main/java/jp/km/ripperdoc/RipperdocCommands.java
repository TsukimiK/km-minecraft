package jp.km.ripperdoc;

import com.mojang.brigadier.Command;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;

import java.util.List;

/** Production-safe status and operator give commands. */
public final class RipperdocCommands {
    private RipperdocCommands() {}

    private static final List<String> ALL_LOOT = List.of(
            "ripperdoc:items/zandevistan",
            "ripperdoc:items/berserk",
            "ripperdoc:items/aquatic",
            "ripperdoc:items/moontech_core",
            "ripperdoc:items/moontech"
    );

    public static void register() {
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> {
            dispatcher.register(Commands.literal("ripperdoc")
                    .then(Commands.literal("status").executes(ctx -> {
                        ctx.getSource().sendSuccess(
                                () -> Component.literal("[Ripperdoc] Fabric server mod v" + RipperdocMod.VERSION + " active"),
                                false
                        );
                        return Command.SINGLE_SUCCESS;
                    })));

            dispatcher.register(Commands.literal("rdgive")
                    .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
                    .then(Commands.literal("zandevistan").executes(ctx -> give(ctx.getSource(), "ripperdoc:items/zandevistan")))
                    .then(Commands.literal("berserk").executes(ctx -> give(ctx.getSource(), "ripperdoc:items/berserk")))
                    .then(Commands.literal("aquatic").executes(ctx -> give(ctx.getSource(), "ripperdoc:items/aquatic")))
                    .then(Commands.literal("moontech_core").executes(ctx -> give(ctx.getSource(), "ripperdoc:items/moontech_core")))
                    .then(Commands.literal("moontech").executes(ctx -> give(ctx.getSource(), "ripperdoc:items/moontech")))
                    .then(Commands.literal("all").executes(ctx -> giveAll(ctx.getSource()))));
        });
    }

    private static int give(CommandSourceStack source, String lootTable) throws CommandSyntaxException {
        ServerPlayer player = source.getPlayerOrException();
        run(source, "loot give " + player.getScoreboardName() + " loot " + lootTable);
        return Command.SINGLE_SUCCESS;
    }

    private static int giveAll(CommandSourceStack source) throws CommandSyntaxException {
        ServerPlayer player = source.getPlayerOrException();
        String name = player.getScoreboardName();
        for (String lootTable : ALL_LOOT) {
            run(source, "loot give " + name + " loot " + lootTable);
        }
        return Command.SINGLE_SUCCESS;
    }

    private static void run(CommandSourceStack source, String command) {
        source.getServer().getCommands().performPrefixedCommand(source, command);
    }
}
