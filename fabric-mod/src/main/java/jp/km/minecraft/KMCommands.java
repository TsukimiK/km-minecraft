package jp.km.minecraft;

import com.mojang.brigadier.Command;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.server.level.ServerPlayer;

import java.util.List;

/** Operator/debug commands registered by the Fabric mod itself. */
public final class KMCommands {
    private KMCommands() {}

    private static final String SEEDS =
            "give %s minecraft:wheat_seeds[minecraft:custom_name={text:'大根の種',color:'green',italic:false},minecraft:lore=[{text:'耕地に植えることができます',color:'gray',italic:false},{text:'ごく稀に特別な作物へ育ちます',color:'dark_gray',italic:false}],minecraft:custom_data={km_minecraft:{item:'daikon_seeds'}},minecraft:item_model='km-minecraft:farming/daikon_seeds'] 16";

    private static final List<String> DAIKON_TOOLS = List.of(
            "give %s minecraft:iron_sword[minecraft:max_damage=220,!minecraft:repairable,minecraft:custom_name={text:'大根の剣',color:'white',italic:false},minecraft:lore=[{text:'右クリック長押しで食べる',color:'gray',italic:false},{text:'食事時：耐久 -25',color:'dark_gray',italic:false}],minecraft:custom_data={km_minecraft:{daikon_tool:true,eat_disabled:false}},minecraft:item_model='km-minecraft:tools/daikon_sword',minecraft:food={nutrition:1,saturation:0.6,can_always_eat:false},minecraft:consumable={consume_seconds:1.6,animation:'eat',sound:'minecraft:entity.generic.eat',has_consume_particles:false}] 1",
            "give %s minecraft:iron_pickaxe[minecraft:max_damage=220,!minecraft:repairable,minecraft:custom_name={text:'大根のツルハシ',color:'white',italic:false},minecraft:lore=[{text:'右クリック長押しで食べる',color:'gray',italic:false},{text:'食事時：耐久 -25',color:'dark_gray',italic:false}],minecraft:custom_data={km_minecraft:{daikon_tool:true,eat_disabled:false}},minecraft:item_model='km-minecraft:tools/daikon_pickaxe',minecraft:food={nutrition:1,saturation:0.6,can_always_eat:false},minecraft:consumable={consume_seconds:1.6,animation:'eat',sound:'minecraft:entity.generic.eat',has_consume_particles:false}] 1",
            "give %s minecraft:iron_axe[minecraft:max_damage=220,!minecraft:repairable,minecraft:custom_name={text:'大根の斧',color:'white',italic:false},minecraft:lore=[{text:'右クリック長押しで食べる',color:'gray',italic:false},{text:'食事時：耐久 -25',color:'dark_gray',italic:false}],minecraft:custom_data={km_minecraft:{daikon_tool:true,eat_disabled:false}},minecraft:item_model='km-minecraft:tools/daikon_axe',minecraft:food={nutrition:1,saturation:0.6,can_always_eat:false},minecraft:consumable={consume_seconds:1.6,animation:'eat',sound:'minecraft:entity.generic.eat',has_consume_particles:false}] 1",
            "give %s minecraft:iron_shovel[minecraft:max_damage=220,!minecraft:repairable,minecraft:custom_name={text:'大根のシャベル',color:'white',italic:false},minecraft:lore=[{text:'右クリック長押しで食べる',color:'gray',italic:false},{text:'食事時：耐久 -25',color:'dark_gray',italic:false}],minecraft:custom_data={km_minecraft:{daikon_tool:true,eat_disabled:false}},minecraft:item_model='km-minecraft:tools/daikon_shovel',minecraft:food={nutrition:1,saturation:0.6,can_always_eat:false},minecraft:consumable={consume_seconds:1.6,animation:'eat',sound:'minecraft:entity.generic.eat',has_consume_particles:false}] 1",
            "give %s minecraft:iron_hoe[minecraft:max_damage=220,!minecraft:repairable,minecraft:custom_name={text:'大根のクワ',color:'white',italic:false},minecraft:lore=[{text:'右クリック長押しで食べる',color:'gray',italic:false},{text:'食事時：耐久 -25',color:'dark_gray',italic:false}],minecraft:custom_data={km_minecraft:{daikon_tool:true,eat_disabled:false}},minecraft:item_model='km-minecraft:tools/daikon_hoe',minecraft:food={nutrition:1,saturation:0.6,can_always_eat:false},minecraft:consumable={consume_seconds:1.6,animation:'eat',sound:'minecraft:entity.generic.eat',has_consume_particles:false}] 1"
    );

    private static final List<String> ASAHATAMON_TOOLS = List.of(
            "give %s minecraft:diamond_sword[minecraft:custom_name={text:'あさはたもんの剣',color:'green',italic:false},minecraft:custom_data={km_minecraft:{asahatamon_tool:'sword'}},minecraft:item_model='km-minecraft:asahatamon/upgraded_sword'] 1",
            "give %s minecraft:diamond_pickaxe[minecraft:custom_name={text:'あさはたもんのツルハシ',color:'green',italic:false},minecraft:custom_data={km_minecraft:{asahatamon_tool:'pickaxe'}},minecraft:item_model='km-minecraft:asahatamon/upgraded_pickaxe'] 1",
            "give %s minecraft:diamond_axe[minecraft:custom_name={text:'あさはたもんの斧',color:'green',italic:false},minecraft:custom_data={km_minecraft:{asahatamon_tool:'axe'}},minecraft:item_model='km-minecraft:asahatamon/upgraded_axe'] 1",
            "give %s minecraft:diamond_shovel[minecraft:custom_name={text:'あさはたもんのシャベル',color:'green',italic:false},minecraft:custom_data={km_minecraft:{asahatamon_tool:'shovel'}},minecraft:item_model='km-minecraft:asahatamon/upgraded_shovel'] 1",
            "give %s minecraft:diamond_hoe[minecraft:custom_name={text:'あさはたもんのクワ',color:'green',italic:false},minecraft:custom_data={km_minecraft:{asahatamon_tool:'hoe'}},minecraft:item_model='km-minecraft:asahatamon/upgraded_hoe'] 1",
            "give %s minecraft:nether_star[minecraft:custom_name={text:'あさはたもんの結晶',color:'green',italic:false},minecraft:custom_data={km_minecraft:{asahatamon_crystal:true}},minecraft:item_model='km-minecraft:asahatamon/crystal'] 1",
            "give %s minecraft:netherite_axe[minecraft:custom_name={text:'あさはたもんの万能工具',color:'gold',italic:false},minecraft:lore=[{text:'採掘速度：20',color:'green',italic:false},{text:'スニーク＋左クリック：岩盤破壊',color:'dark_green',italic:false}],minecraft:custom_data={km_minecraft:{asahatamon_omnitool:true}},minecraft:item_model='km-minecraft:asahatamon/omnitool',minecraft:tool={rules:[{blocks:'#minecraft:mineable/pickaxe',speed:20.0,correct_for_drops:true},{blocks:'#minecraft:mineable/axe',speed:20.0,correct_for_drops:true},{blocks:'#minecraft:mineable/shovel',speed:20.0,correct_for_drops:true}],default_mining_speed:1.0,damage_per_block:1}] 1"
    );

    private static final List<String> ASAHATAMON_ARMOR = List.of(
            "give %s minecraft:netherite_helmet[minecraft:custom_name={text:'あさはたもんのヘルメット',color:'green',italic:false},minecraft:custom_data={km_minecraft:{asahatamon_armor:true,piece:'helmet'}},minecraft:item_model='km-minecraft:asahatamon/armor/helmet',minecraft:equippable={slot:'head',equip_sound:'minecraft:item.armor.equip_netherite',asset_id:'km-minecraft:asahatamon'}] 1",
            "give %s minecraft:netherite_chestplate[minecraft:custom_name={text:'あさはたもんのチェストプレート',color:'green',italic:false},minecraft:custom_data={km_minecraft:{asahatamon_armor:true,piece:'chestplate'}},minecraft:item_model='km-minecraft:asahatamon/armor/chestplate',minecraft:equippable={slot:'chest',equip_sound:'minecraft:item.armor.equip_netherite',asset_id:'km-minecraft:asahatamon'},minecraft:glider={},minecraft:lore=[{text:'ネザライト性能 + 滑空機能',color:'gray',italic:false},{text:'通常の防具エンチャント対応',color:'dark_gray',italic:false}]] 1",
            "give %s minecraft:netherite_leggings[minecraft:custom_name={text:'あさはたもんのレギンス',color:'green',italic:false},minecraft:custom_data={km_minecraft:{asahatamon_armor:true,piece:'leggings'}},minecraft:item_model='km-minecraft:asahatamon/armor/leggings',minecraft:equippable={slot:'legs',equip_sound:'minecraft:item.armor.equip_netherite',asset_id:'km-minecraft:asahatamon'}] 1",
            "give %s minecraft:netherite_boots[minecraft:custom_name={text:'あさはたもんのブーツ',color:'green',italic:false},minecraft:custom_data={km_minecraft:{asahatamon_armor:true,piece:'boots'}},minecraft:item_model='km-minecraft:asahatamon/armor/boots',minecraft:equippable={slot:'feet',equip_sound:'minecraft:item.armor.equip_netherite',asset_id:'km-minecraft:asahatamon'}] 1"
    );

    private static final String CIGARETTE_BOX =
            "give %s minecraft:paper[minecraft:custom_name={text:'Vegeter （BOX）',color:'green',italic:false},minecraft:lore=[{text:'右クリックで開封',color:'gray',italic:false},{text:'内容：Vegeter 10本',color:'dark_gray',italic:false}],minecraft:custom_data={km_cigarette_box:true},minecraft:item_model='km-minecraft:cigarette/box',minecraft:rarity='uncommon',minecraft:max_stack_size=16,minecraft:consumable={consume_seconds:0.0,animation:'none',sound:'minecraft:item.book.page_turn',has_consume_particles:false}] 1";

    public static void register() {
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> {
            dispatcher.register(Commands.literal("kmgive")
                    .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
                    .then(Commands.literal("seeds").executes(ctx -> giveOne(ctx.getSource(), SEEDS)))
                    .then(Commands.literal("daikon_tools").executes(ctx -> giveMany(ctx.getSource(), DAIKON_TOOLS)))
                    .then(Commands.literal("asahatamon_tools").executes(ctx -> giveMany(ctx.getSource(), ASAHATAMON_TOOLS)))
                    .then(Commands.literal("asahatamon_armor").executes(ctx -> giveMany(ctx.getSource(), ASAHATAMON_ARMOR)))
                    .then(Commands.literal("cigarette_box").executes(ctx -> giveOne(ctx.getSource(), CIGARETTE_BOX)))
                    .then(Commands.literal("all").executes(ctx -> {
                        int result = giveOne(ctx.getSource(), SEEDS);
                        if (result == 0) return 0;
                        giveMany(ctx.getSource(), DAIKON_TOOLS);
                        giveMany(ctx.getSource(), ASAHATAMON_TOOLS);
                        giveMany(ctx.getSource(), ASAHATAMON_ARMOR);
                        giveOne(ctx.getSource(), CIGARETTE_BOX);
                        return Command.SINGLE_SUCCESS;
                    })));

            dispatcher.register(Commands.literal("km")
                    .then(Commands.literal("status").executes(ctx -> {
                        ServerPlayer player = ctx.getSource().getPlayerOrException();
                        String name = player.getScoreboardName();
                        run(ctx.getSource(), "tellraw " + name + " {text:'[KM Minecraft] Fabric Java entrypoint v" + KMMinecraftMod.VERSION + " active',color:'green'}");
                        return Command.SINGLE_SUCCESS;
                    }))
                    .then(Commands.literal("functiontest")
                            .requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
                            .executes(ctx -> run(ctx.getSource(), "function km-minecraft:farming/give_seeds"))));
        });
    }

    private static int giveOne(CommandSourceStack source, String commandTemplate) throws CommandSyntaxException {
        ServerPlayer player = source.getPlayerOrException();
        return run(source, commandTemplate.formatted(player.getScoreboardName()));
    }

    private static int giveMany(CommandSourceStack source, List<String> templates) throws CommandSyntaxException {
        ServerPlayer player = source.getPlayerOrException();
        String name = player.getScoreboardName();
        int ok = 0;
        for (String template : templates) {
            if (run(source, template.formatted(name)) > 0) ok++;
        }
        return ok > 0 ? Command.SINGLE_SUCCESS : 0;
    }

    private static int run(CommandSourceStack source, String command) {
        return source.getServer().getCommands().performPrefixedCommand(source, command);
    }
}
