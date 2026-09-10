package jp.km.minecraft;

import com.mojang.brigadier.Command;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;

import java.util.List;

/** Operator maintenance commands registered by the Fabric mod. */
public final class KMCommands {
    private KMCommands() {}

    private static final String GIVE_SEEDS = "km-minecraft:farming/give_seeds";
    private static final String GIVE_DAIKON_TOOLS = "km-minecraft:tools/give_all";
    private static final String GIVE_ASAHATAMON_TOOLS = "km-minecraft:asahatamon/give_upgrade_set";
    private static final String GIVE_ASAHATAMON_ARMOR = "km-minecraft:asahatamon/give_armor_set";
    private static final String GIVE_CIGARETTE_BOX = "km-minecraft:cigarette/give_box";

    private static final List<String> GIVE_ALL = List.of(
            GIVE_SEEDS,
            GIVE_DAIKON_TOOLS,
            GIVE_ASAHATAMON_TOOLS,
            GIVE_ASAHATAMON_ARMOR,
            GIVE_CIGARETTE_BOX
    );

    public static void register() {
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> {
            dispatcher.register(Commands.literal("kmgive")
                    .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
                    .then(Commands.literal("seeds")
                            .executes(ctx -> runFunction(ctx.getSource(), GIVE_SEEDS)))
                    .then(Commands.literal("daikon_tools")
                            .executes(ctx -> runFunction(ctx.getSource(), GIVE_DAIKON_TOOLS)))
                    .then(Commands.literal("asahatamon_tools")
                            .executes(ctx -> runFunction(ctx.getSource(), GIVE_ASAHATAMON_TOOLS)))
                    .then(Commands.literal("asahatamon_armor")
                            .executes(ctx -> runFunction(ctx.getSource(), GIVE_ASAHATAMON_ARMOR)))
                    .then(Commands.literal("cigarette_box")
                            .executes(ctx -> runFunction(ctx.getSource(), GIVE_CIGARETTE_BOX)))
                    .then(Commands.literal("all")
                            .executes(ctx -> runFunctions(ctx.getSource(), GIVE_ALL))));

            dispatcher.register(Commands.literal("km")
                    .then(Commands.literal("status").executes(ctx -> {
                        ctx.getSource().sendSuccess(
                                () -> Component.literal("[KM Minecraft] Fabric Server Mod v" + KMMinecraftMod.VERSION + " active"),
                                false
                        );
                        return Command.SINGLE_SUCCESS;
                    })));
        });
    }

    private static int runFunction(CommandSourceStack source, String functionId) throws CommandSyntaxException {
        source.getPlayerOrException();
        runSilent(source, "function " + functionId);
        return Command.SINGLE_SUCCESS;
    }

    private static int runFunctions(CommandSourceStack source, List<String> functionIds) throws CommandSyntaxException {
        source.getPlayerOrException();
        for (String functionId : functionIds) {
            runSilent(source, "function " + functionId);
        }
        return Command.SINGLE_SUCCESS;
    }

    private static void runSilent(CommandSourceStack source, String command) {
        source.getServer().getCommands().performPrefixedCommand(source.withSuppressedOutput(), command);
    }
}
