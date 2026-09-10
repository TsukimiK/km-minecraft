#!/usr/bin/env python3
from pathlib import Path
import json, shutil, sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'fabric-mod/src/main/resources/data')
km = root / 'km-minecraft'

daikon_ing = {'fabric:type':'fabric:custom_data','base':'minecraft:poisonous_potato','nbt':{'km_minecraft':{'item':'daikon'}}}
asahatamon_ing = {'fabric:type':'fabric:custom_data','base':'minecraft:echo_shard','nbt':{'km_minecraft':{'item':'asahatamon'}}}

def replace_proxy(v):
    if isinstance(v, dict): return {k: replace_proxy(x) for k,x in v.items()}
    if isinstance(v, list): return [replace_proxy(x) for x in v]
    if v == 'minecraft:poisonous_potato': return daikon_ing
    if v == 'minecraft:echo_shard': return asahatamon_ing
    return v

for p in (km/'recipe').rglob('*.json'):
    obj=json.loads(p.read_text(encoding='utf-8'))
    p.write_text(json.dumps(replace_proxy(obj), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def write_json(rel, obj):
    p=km/rel; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def write_text(rel, text):
    p=km/rel; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(text.rstrip('\n')+'\n', encoding='utf-8')

for rel, ids in {
    'advancement/farming/unlock_daikon_recipes.json':['km-minecraft:tools/daikon_hoe'],
    'advancement/farming/unlock_asahatamon_recipes.json':['km-minecraft:asahatamon/upgraded_hoe','km-minecraft:asahatamon/armor/helmet','km-minecraft:asahatamon/armor/chestplate','km-minecraft:asahatamon/armor/leggings','km-minecraft:asahatamon/armor/boots']
}.items():
    p=km/rel; obj=json.loads(p.read_text(encoding='utf-8'))
    recipes=obj['rewards']['recipes']
    for rid in ids:
        if rid not in recipes: recipes.append(rid)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

daikon_hoe={
 'type':'minecraft:crafting_shaped','category':'equipment','pattern':['DD',' S',' S'],
 'key':{'D':daikon_ing,'S':'minecraft:stick'},
 'result':{'id':'minecraft:iron_hoe','count':1,'components':{
   'minecraft:max_damage':220,'!minecraft:repairable':{},
   'minecraft:custom_name':{'text':'大根のクワ','color':'white','italic':False},
   'minecraft:lore':[{'text':'右クリック長押しで食べる','color':'gray','italic':False},{'text':'食事時：耐久 -25','color':'dark_gray','italic':False}],
   'minecraft:custom_data':{'km_minecraft':{'daikon_tool':True,'eat_disabled':False}},
   'minecraft:item_model':'km-minecraft:tools/daikon_hoe',
   'minecraft:food':{'nutrition':1,'saturation':0.6,'can_always_eat':False},
   'minecraft:consumable':{'consume_seconds':1.6,'animation':'eat','sound':'minecraft:entity.generic.eat','has_consume_particles':False}
 }}}
write_json('recipe/tools/daikon_hoe.json', daikon_hoe)

asaha_hoe={
 'type':'minecraft:crafting_shaped','category':'equipment','pattern':['AA',' S',' S'],
 'key':{'A':asahatamon_ing,'S':'minecraft:stick'},
 'result':{'id':'minecraft:diamond_hoe','count':1,'components':{
   'minecraft:custom_name':{'text':'あさはたもんのクワ','color':'green','italic':False},
   'minecraft:custom_data':{'km_minecraft':{'asahatamon_tool':'hoe'}},
   'minecraft:item_model':'km-minecraft:asahatamon/upgraded_hoe'}}}
write_json('recipe/asahatamon/upgraded_hoe.json', asaha_hoe)

armor_specs={
 'helmet':('minecraft:netherite_helmet',['AAA','A A'],'head','あさはたもんのヘルメット'),
 'chestplate':('minecraft:netherite_chestplate',['A A','AAA','AAA'],'chest','あさはたもんのチェストプレート'),
 'leggings':('minecraft:netherite_leggings',['AAA','A A','A A'],'legs','あさはたもんのレギンス'),
 'boots':('minecraft:netherite_boots',['A A','A A'],'feet','あさはたもんのブーツ')}
for piece,(item,pattern,slot,name) in armor_specs.items():
    comp={
      'minecraft:custom_name':{'text':name,'color':'green','italic':False},
      'minecraft:custom_data':{'km_minecraft':{'asahatamon_armor':True,'piece':piece}},
      'minecraft:item_model':f'km-minecraft:asahatamon/armor/{piece}',
      'minecraft:equippable':{'slot':slot,'equip_sound':'minecraft:item.armor.equip_netherite','asset_id':'km-minecraft:asahatamon'}
    }
    if piece=='chestplate':
        comp['minecraft:glider']={}
        comp['minecraft:lore']=[{'text':'ネザライト性能 + 滑空機能','color':'gray','italic':False},{'text':'通常の防具エンチャント対応','color':'dark_gray','italic':False}]
    write_json(f'recipe/asahatamon/armor/{piece}.json',{'type':'minecraft:crafting_shaped','category':'equipment','pattern':pattern,'key':{'A':asahatamon_ing},'result':{'id':item,'count':1,'components':comp}})

write_text('function/farming/plant/create.mcfunction','''setblock ~ ~ ~ minecraft:air
execute if entity @e[type=minecraft:interaction,tag=km_farm_crop,distance=..0.20,limit=1] run return run function km-minecraft:farming/plant/occupied
execute if entity @s[tag=km_force_rare_crop] run return run function km-minecraft:farming/plant/create_rare
function km-minecraft:farming/plant/create_normal''')
write_text('function/farming/plant/create_normal.mcfunction','''summon minecraft:interaction ~ ~ ~ {Tags:["km_farm_crop","km_daikon","km_unresolved","km_stage0"],width:1.20f,height:1.35f,response:1b}
execute as @e[type=minecraft:interaction,tag=km_farm_crop,tag=km_unresolved,tag=km_stage0,distance=..0.10,limit=1,sort=nearest] at @s run function km-minecraft:farming/crop/refresh_visual''')
write_text('function/farming/plant/create_rare.mcfunction','''summon minecraft:interaction ~ ~ ~ {Tags:["km_farm_crop","km_daikon","km_rare","km_forced_rare","km_stage0"],width:1.20f,height:1.35f,response:1b}
execute as @e[type=minecraft:interaction,tag=km_farm_crop,tag=km_forced_rare,tag=km_stage0,distance=..0.10,limit=1,sort=nearest] at @s run function km-minecraft:farming/crop/refresh_visual''')
write_text('function/farming/crop/stage1_to_2.mcfunction','''tag @s remove km_stage1
tag @s add km_stage2
execute if entity @s[tag=km_unresolved] store result score #plant kmfarm_rng run random value 1..100
execute if entity @s[tag=km_unresolved] if score #plant kmfarm_rng matches 1 run tag @s add km_rare
execute if entity @s[tag=km_unresolved] unless score #plant kmfarm_rng matches 1 run tag @s add km_normal
tag @s remove km_unresolved
function km-minecraft:farming/crop/refresh_visual''')
write_text('function/farming/crop/refresh_visual.mcfunction','''# Remove the previous crop visuals at this crop position.
kill @e[type=minecraft:item_display,tag=km_farm_visual,distance=..0.08]

# Stage 0/1 intentionally use the SAME appearance for every crop type.
# The 1% rare roll is resolved only when a normal-seed crop reaches stage 2.
execute if entity @s[tag=km_stage0] run summon minecraft:item_display ~ ~ ~ {Tags:["km_farm_visual","km_daikon_visual"],billboard:"fixed",view_range:0.85f,shadow_radius:0.0f,shadow_strength:0.0f,item_display:"fixed",transformation:{translation:[0.0f,0.10f,0.0f],left_rotation:[0.0f,0.0f,0.0f,1.0f],scale:[0.90f,0.90f,0.90f],right_rotation:[0.0f,0.0f,0.0f,1.0f]},item:{id:"minecraft:paper",count:1,components:{"minecraft:item_model":"km-minecraft:farming/crop/normal_stage_0"}}}
execute if entity @s[tag=km_stage1] run summon minecraft:item_display ~ ~ ~ {Tags:["km_farm_visual","km_daikon_visual"],billboard:"fixed",view_range:0.85f,shadow_radius:0.0f,shadow_strength:0.0f,item_display:"fixed",transformation:{translation:[0.0f,0.28f,0.0f],left_rotation:[0.0f,0.0f,0.0f,1.0f],scale:[0.90f,0.90f,0.90f],right_rotation:[0.0f,0.0f,0.0f,1.0f]},item:{id:"minecraft:paper",count:1,components:{"minecraft:item_model":"km-minecraft:farming/crop/normal_stage_1"}}}
execute if entity @s[tag=km_normal,tag=km_stage2] run summon minecraft:item_display ~ ~ ~ {Tags:["km_farm_visual","km_daikon_visual"],billboard:"fixed",view_range:0.85f,shadow_radius:0.0f,shadow_strength:0.0f,item_display:"fixed",transformation:{translation:[0.0f,0.28f,0.0f],left_rotation:[0.0f,0.0f,0.0f,1.0f],scale:[0.90f,0.90f,0.90f],right_rotation:[0.0f,0.0f,0.0f,1.0f]},item:{id:"minecraft:paper",count:1,components:{"minecraft:item_model":"km-minecraft:farming/crop/normal_stage_2"}}}
execute if entity @s[tag=km_rare,tag=km_stage2] run summon minecraft:item_display ~ ~ ~ {Tags:["km_farm_visual","km_daikon_visual"],billboard:"fixed",view_range:0.85f,shadow_radius:0.0f,shadow_strength:0.0f,item_display:"fixed",transformation:{translation:[0.0f,0.28f,0.0f],left_rotation:[0.0f,0.0f,0.0f,1.0f],scale:[0.90f,0.90f,0.90f],right_rotation:[0.0f,0.0f,0.0f,1.0f]},item:{id:"minecraft:paper",count:1,components:{"minecraft:item_model":"km-minecraft:farming/crop/rare_stage_2"}}}''')

write_text('function/tools/give/daikon_hoe.mcfunction','''give @s minecraft:iron_hoe[minecraft:max_damage=220,!minecraft:repairable,minecraft:custom_name={text:"大根のクワ",color:"white",italic:false},minecraft:lore=[{text:"右クリック長押しで食べる",color:"gray",italic:false},{text:"食事時：耐久 -25",color:"dark_gray",italic:false}],minecraft:custom_data={km_minecraft:{daikon_tool:true,eat_disabled:false}},minecraft:item_model="km-minecraft:tools/daikon_hoe",minecraft:food={nutrition:1,saturation:0.6,can_always_eat:false},minecraft:consumable={consume_seconds:1.6,animation:"eat",sound:"minecraft:entity.generic.eat",has_consume_particles:false}] 1''')
p=km/'function/tools/give_all.mcfunction'; s=p.read_text(encoding='utf-8')
if 'daikon_hoe' not in s: s=s.rstrip()+'\nfunction km-minecraft:tools/give/daikon_hoe\n'
p.write_text(s,encoding='utf-8')

write_text('function/asahatamon/give/upgraded_hoe.mcfunction','''give @s minecraft:diamond_hoe[minecraft:custom_name={text:"あさはたもんのクワ",color:"green",italic:false},minecraft:custom_data={km_minecraft:{asahatamon_tool:"hoe"}},minecraft:item_model="km-minecraft:asahatamon/upgraded_hoe"] 1''')
p=km/'function/asahatamon/give_upgrade_set.mcfunction'; s=p.read_text(encoding='utf-8')
needle='give @s minecraft:nether_star'
if 'give/upgraded_hoe' not in s: s=s.replace(needle,'function km-minecraft:asahatamon/give/upgraded_hoe\n'+needle)
p.write_text(s,encoding='utf-8')

armor_give={
 'helmet':'give @s minecraft:netherite_helmet[minecraft:custom_name={text:"あさはたもんのヘルメット",color:"green",italic:false},minecraft:custom_data={km_minecraft:{asahatamon_armor:true,piece:"helmet"}},minecraft:item_model="km-minecraft:asahatamon/armor/helmet",minecraft:equippable={slot:"head",equip_sound:"minecraft:item.armor.equip_netherite",asset_id:"km-minecraft:asahatamon"}] 1',
 'chestplate':'give @s minecraft:netherite_chestplate[minecraft:custom_name={text:"あさはたもんのチェストプレート",color:"green",italic:false},minecraft:custom_data={km_minecraft:{asahatamon_armor:true,piece:"chestplate"}},minecraft:item_model="km-minecraft:asahatamon/armor/chestplate",minecraft:equippable={slot:"chest",equip_sound:"minecraft:item.armor.equip_netherite",asset_id:"km-minecraft:asahatamon"},minecraft:glider={},minecraft:lore=[{text:"ネザライト性能 + 滑空機能",color:"gray",italic:false},{text:"通常の防具エンチャント対応",color:"dark_gray",italic:false}]] 1',
 'leggings':'give @s minecraft:netherite_leggings[minecraft:custom_name={text:"あさはたもんのレギンス",color:"green",italic:false},minecraft:custom_data={km_minecraft:{asahatamon_armor:true,piece:"leggings"}},minecraft:item_model="km-minecraft:asahatamon/armor/leggings",minecraft:equippable={slot:"legs",equip_sound:"minecraft:item.armor.equip_netherite",asset_id:"km-minecraft:asahatamon"}] 1',
 'boots':'give @s minecraft:netherite_boots[minecraft:custom_name={text:"あさはたもんのブーツ",color:"green",italic:false},minecraft:custom_data={km_minecraft:{asahatamon_armor:true,piece:"boots"}},minecraft:item_model="km-minecraft:asahatamon/armor/boots",minecraft:equippable={slot:"feet",equip_sound:"minecraft:item.armor.equip_netherite",asset_id:"km-minecraft:asahatamon"}] 1'}
for piece,text in armor_give.items(): write_text(f'function/asahatamon/give/armor_{piece}.mcfunction',text)
write_text('function/asahatamon/give_armor_set.mcfunction','\n'.join(f'function km-minecraft:asahatamon/give/armor_{p}' for p in ['helmet','chestplate','leggings','boots']))

shutil.rmtree(root/'minecraft'/'tags'/'function', ignore_errors=True)
print('KM Fabric v2 data transformation complete')
