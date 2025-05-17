# Auto-Mining Script with Auto-Walk to Next Mining Spot
# Original by Sparkin, modified 5/2025
# Mines ores and sand, moves to next spot, crafts tools, smelts ores (not 0x1779 or sand) if total >= 10, moves granite, sand, and ingots to blue beetle.
# Fixed journal reading, spot progression, and crash prevention for UOAlive with Razor Enhanced 0.8.2.242.
# Logging removed for silent operation.

from AutoComplete import *
from System.Collections.Generic import List
from System import Int32
from math import sqrt

### CONFIG ###
try:
    fire_beetle = Target.PromptTarget('Target your fire beetle', 43)
    blue_beetle = Target.PromptTarget('Target your blue beetle', 161)
    if fire_beetle == blue_beetle:
        raise Exception('Duplicate beetle serials')
except Exception:
    fire_beetle = blue_beetle = -1

tool_kits_to_keep = 2
shovels_to_keep = 5
min_ingots_for_crafting = 10
TINKERING_GUMP = 0x3cd35884

prospect = True
sturdy = False

scan_radius = 12  # Increased to 12 for broader scanning
mining_cooldown = 1200000  # 20 minutes
beetle_weight_limit = 1600
smelt_weight_threshold = 100
resource_move_threshold = 100
granite_amount_threshold = 25
sand_amount_threshold = 25
ore_amount_threshold = 10
batch_size = 100
search_subcontainers = False
pause_duration = 800
max_moves_per_cycle = 3
max_stack_weight = 25
smelt_cooldown = 10000  # 10s smelting cooldown
max_attempts = 3  # Max mining attempts before forcing spot removal

GRANITE_TYPES = [0x1779]
ORE_TYPES = [0x19B7, 0x19B8, 0x19B9, 0x19BA]
SAND = 0x19B7
### CONFIG ###

SHOVEL = 0x0F39
TOOL_KIT = 0x1EB8
INGOT = 0x1BF2
PROSPECT_TOOL = 0x0FB4

mining_static_ids = [
    # Ore tiles
    0x053B, 0x053C, 0x053D, 0x053E, 0x053F, 0x0540, 0x0541, 0x0542,
    0x0543, 0x0544, 0x0545, 0x0546, 0x0547, 0x0548, 0x0549, 0x054A,
    0x054B, 0x054C, 0x054D, 0x054E, 0x054F, 0x0550, 0x0551, 0x0552,
    0x053, 0x0554, 0x0555, 0x0556, 0x0557, 0x0558, 0x0559, 0x055A,
    # Sand tiles
    0x0016, 0x0017, 0x0018, 0x0019, 0x001A, 0x001B, 0x001C, 0x001D,
    0x0010, 0x0011, 0x0012, 0x0013, 0x0014, 0x0015,
    0x00B1, 0x00B2, 0x00B3, 0x00B4
]

ore_filter = Items.Filter()
ore_filter.Graphics.AddRange(ORE_TYPES)
granite_filter = Items.Filter()
granite_filter.Graphics.AddRange(GRANITE_TYPES)
granite_filter.Enabled = True
granite_filter.OnGround = False
granite_filter.Movable = True

class MiningSpot:
    def __init__(self, x, y, z, id):
        self.x = x
        self.y = y
        self.z = z
        self.id = id

mining_spots = []
prospected = False
last_mining_success = False
attempts = 0

def get_tool_kits():
    try:
        return Items.FindAllByID(TOOL_KIT, 0, Player.Backpack.Serial, True)
    except Exception:
        return []

def get_shovels():
    try:
        return Items.FindAllByID(SHOVEL, -1 if sturdy else 0, Player.Backpack.Serial, True)
    except Exception:
        return []

def gump_check():
    tool_kits = get_tool_kits()
    if not tool_kits:
        return False
    try:
        Items.UseItem(tool_kits[0])
        Misc.Pause(1000)
        if not Gumps.WaitForGump(TINKERING_GUMP, 10000):
            return False
        return True
    except Exception:
        return False

def make_tool_kit():
    if not gump_check():
        return False
    Journal.Clear()
    try:
        Gumps.SendAction(TINKERING_GUMP, 23)
        Misc.Pause(7000)
        if Journal.SearchByType('You create', 'System') or Journal.SearchByType('You have created', 'System'):
            return True
        return False
    except Exception:
        return False

def make_shovel():
    if not gump_check():
        return False
    Journal.Clear()
    try:
        Gumps.SendAction(TINKERING_GUMP, 202)
        Misc.Pause(7000)
        if Journal.SearchByType('You create', 'System') or Journal.SearchByType('You have created', 'System'):
            return True
        return False
    except Exception:
        return False

def make_tools():
    kits = len(get_tool_kits())
    shovels = len(get_shovels())
    ingots = Items.FindByID(INGOT, 0, Player.Backpack.Serial)
    ingot_count = ingots.Amount if ingots else 0
    if ingot_count < min_ingots_for_crafting:
        return False
    while shovels < shovels_to_keep and ingot_count >= 4:
        if make_shovel():
            shovels += 1
            ingot_count -= 4
        else:
            return False
        Misc.Pause(1000)
    while kits < tool_kits_to_keep and ingot_count >= 2:
        if make_tool_kit():
            kits += 1
            ingot_count -= 2
        else:
            return False
        Misc.Pause(1000)
    return True

def get_beetle_weight():
    beetle_mobile = Mobiles.FindBySerial(blue_beetle)
    if not beetle_mobile or not beetle_mobile.Backpack:
        return 0
    total = 0
    try:
        for item in beetle_mobile.Backpack.Contains:
            if not item or item.Amount <= 0:
                continue
            weight = item.Amount * 0.1
            try:
                props = Items.GetPropValue(item.Serial, "Weight")
                if props is not None:
                    weight = props
                elif item.ItemID == INGOT:
                    weight = item.Amount * 0.1
                elif item.ItemID == 0x1779:
                    weight = item.Amount * 0.5
                elif item.ItemID == SAND and "sand" in (Items.GetPropStringByIndex(item.Serial, 0) or "Unknown").lower():
                    weight = item.Amount * 0.1
            except:
                pass
            total += weight
    except Exception:
        pass
    return total

def move_all_granite_to_beetle():
    beetle_mobile = Mobiles.FindBySerial(blue_beetle)
    if not beetle_mobile:
        return False
    distance = sqrt((Player.Position.X - beetle_mobile.Position.X)**2 + (Player.Position.Y - beetle_mobile.Position.Y)**2)
    if distance > 3:
        return False
    
    try:
        granite_items = Items.FindAllByID(0x1779, -1, Player.Backpack.Serial, False)
        if not granite_items:
            granite_items = Items.ApplyFilter(granite_filter)
            granite_items = [g for g in granite_items if g.Container == Player.Backpack.Serial]
        
        if not granite_items:
            return False
        
        total_amount = sum(g.Amount for g in granite_items)
        if total_amount <= granite_amount_threshold:
            return False
        
        Misc.Resync()
        moved_any = False
        for g in granite_items:
            amount = g.Amount
            while amount > 0:
                batch = min(amount, 1)
                try:
                    Items.Move(g, blue_beetle, batch)
                    Misc.Pause(1000)
                    moved_any = True
                except Exception:
                    break
                amount -= batch
        
        return moved_any
    except Exception:
        return False

def move_resources():
    beetle_mobile = Mobiles.FindBySerial(blue_beetle)
    if not beetle_mobile:
        return False
    if not beetle_mobile.Backpack:
        return False
    
    distance = sqrt((Player.Position.X - beetle_mobile.Position.X)**2 + (Player.Position.Y - beetle_mobile.Position.Y)**2)
    if distance > 3:
        return False
    
    try:
        total_weight = get_beetle_weight()
        moved_any = False
        ingot_weight_per_unit = 0.1
        sand_weight_per_unit = 0.1
        move_count = 0
        
        Misc.Resync()
        ingots = Items.FindAllByID(INGOT, -1, Player.Backpack.Serial, search_subcontainers)
        sand_items = Items.FindAllByID(SAND, -1, Player.Backpack.Serial, search_subcontainers)
        sand_items = [s for s in sand_items if "sand" in (Items.GetPropStringByIndex(s.Serial, 0) or "Unknown").lower()]
        
        total_sand_amount = sum(s.Amount for s in sand_items)
        
        for i in ingots:
            if move_count >= max_moves_per_cycle:
                break
            Misc.Resync()
            item = Items.FindBySerial(i.Serial)
            if not item or item.Amount < 1 or (not search_subcontainers and item.Container != Player.Backpack.Serial):
                continue
            current_batch = min(batch_size, item.Amount)
            batch_weight = current_batch * ingot_weight_per_unit
            if total_weight + batch_weight > beetle_weight_limit:
                return moved_any
            try:
                Misc.Resync()
                Misc.Pause(1500)
                Misc.Resync()
                Items.Move(i.Serial, blue_beetle, current_batch)
                Misc.Pause(pause_duration)
                total_weight += batch_weight
                move_count += 1
                moved_any = True
            except Exception:
                continue
            Misc.Pause(500)
        
        if total_sand_amount > sand_amount_threshold:
            for s in sand_items:
                if move_count >= max_moves_per_cycle:
                    break
                Misc.Resync()
                item = Items.FindBySerial(s.Serial)
                if not item or item.Amount < 1 or (not search_subcontainers and item.Container != Player.Backpack.Serial):
                    continue
                current_batch = min(batch_size, item.Amount)
                batch_weight = current_batch * sand_weight_per_unit
                if total_weight + batch_weight > beetle_weight_limit:
                    return moved_any
                try:
                    Misc.Resync()
                    Misc.Pause(1500)
                    Misc.Resync()
                    Items.Move(s.Serial, blue_beetle, current_batch)
                    Misc.Pause(pause_duration)
                    total_weight += batch_weight
                    move_count += 1
                    moved_any = True
                except Exception:
                    continue
                Misc.Pause(500)
        
        return moved_any
    except Exception:
        return False

def scan_mining_spots():
    global mining_spots
    mining_spots = []
    min_x = Player.Position.X - scan_radius
    max_x = Player.Position.X + scan_radius
    min_y = Player.Position.Y - scan_radius
    max_y = Player.Position.Y + scan_radius
    step = 1
    all_tiles = []
    try:
        for x in range(min_x, max_x + 1, step):
            for y in range(min_y, max_y + 1, step):
                statics = Statics.GetStaticsTileInfo(x, y, Player.Map)
                if statics:
                    for tile in statics:
                        all_tiles.append((tile.StaticID, x, y, tile.StaticZ))
                        if tile.StaticID in mining_static_ids and not Timer.Check(f'{x},{y}'):
                            mining_spots.append(MiningSpot(x, y, tile.StaticZ, tile.StaticID))
                else:
                    mining_spots.append(MiningSpot(x, y, Player.Position.Z, 0x0000))
    except Exception:
        pass
    
    try:
        target = Target.PromptGroundTarget('Target a sand tile', 33)
        if target:
            statics = Statics.GetStaticsTileInfo(target.X, target.Y, Player.Map)
            if statics:
                for tile in statics:
                    if tile.StaticID not in mining_static_ids:
                        mining_static_ids.append(tile.StaticID)
            else:
                mining_spots.append(MiningSpot(target.X, target.Y, Player.Position.Z, 0x0000))
    except Exception:
        pass
    
    mining_spots.sort(key=lambda spot: sqrt((spot.x - Player.Position.X)**2 + (spot.y - Player.Position.Y)**2))

def move_to_mining_spot():
    global mining_spots, prospected
    if not mining_spots:
        Misc.Pause(5000)
        scan_mining_spots()
        if not mining_spots:
            return False
    spot = mining_spots[0]
    try:
        Misc.Resync()
        coords = PathFinding.Route()
        coords.MaxRetry = 10
        coords.StopIfStuck = False
        coords.X = spot.x
        coords.Y = spot.y
        path_attempts = [
            (spot.x, spot.y),
            (spot.x, spot.y + 1),
            (spot.x + 1, spot.y),
            (spot.x - 1, spot.y),
            (spot.x, spot.y - 1)
        ]
        for x, y in path_attempts:
            coords.X = x
            coords.Y = y
            if PathFinding.Go(coords):
                Misc.Pause(1000)
                if abs(Player.Position.X - spot.x) <= 1 and abs(Player.Position.Y - spot.y) <= 1:
                    prospected = False
                    return True
                break
        return False
    except Exception:
        return False

def main():
    global prospected, mining_spots, last_mining_success, attempts
    try:
        Journal.Clear()
        if not Mobiles.FindBySerial(fire_beetle):
            return
        if not Mobiles.FindBySerial(blue_beetle):
            return
        
        while not Player.IsGhost:
            max_weight = Player.MaxWeight
            smelt_weight = max_weight - smelt_weight_threshold
            resource_weight = max_weight - resource_move_threshold
            
            shovels = get_shovels()
            if not shovels:
                return
            if len(shovels) < shovels_to_keep:
                make_tools()
            tool = shovels[0]
            
            if not mining_spots:
                scan_mining_spots()
                if not mining_spots:
                    Misc.Pause(5000)
                    continue
            
            if not move_to_mining_spot():
                mining_spots.pop(0)
                attempts = 0
                continue
            
            spot = mining_spots[0]
            resource = 'sand' if spot.id in [0x0016, 0x0017, 0x0018, 0x0019, 0x001A, 0x001B, 0x001C, 0x001D, 0x0010, 0x0011, 0x0012, 0x0013, 0x0014, 0x0015, 0x00B1, 0x00B2, 0x00B3, 0x00B4] or spot.id == 0x0000 else 'ore'
            
            if prospect and not prospected and resource == 'ore':
                prospect_tool = Items.FindByID(PROSPECT_TOOL, -1, Player.Backpack.Serial)
                if prospect_tool:
                    Items.UseItem(prospect_tool)
                    Target.WaitForTarget(2000)
                    Target.TargetExecute(spot.x, spot.y, spot.z, spot.id)
                    Misc.Pause(500)
                    prospected = True
            
            if tool:
                Journal.Clear()
                last_mining_success = False
                try:
                    Target.TargetResource(tool, resource)
                    Target.TargetExecute(spot.x, spot.y, spot.z, spot.id)
                    Misc.Pause(5000)
                    journal_lines = Journal.GetTextBySerial(Player.Serial)
                    
                    if any('you put' in line.lower() or 'sand in your' in line.lower() for line in journal_lines):
                        last_mining_success = True
                        m = next((line for line in journal_lines if 'you put' in line.lower() or 'sand in your' in line.lower()), 'Mining success')
                        Journal.Clear(m)
                        attempts = 0
                    
                    if any('there is no sand here to mine' in line.lower() for line in journal_lines):
                        Timer.Create(f'{spot.x},{spot.y}', mining_cooldown)
                        mining_spots.pop(0)
                        attempts = 0
                        continue
                except Exception:
                    pass
                
                attempts += 1
                if attempts >= max_attempts:
                    Timer.Create(f'{spot.x},{spot.y}', mining_cooldown)
                    mining_spots.pop(0)
                    attempts = 0
            
            if last_mining_success and Player.Weight >= smelt_weight and not Timer.Check('smelt_cooldown'):
                Timer.Create('smelt_cooldown', smelt_cooldown)
                fire_beetle_mobile = Mobiles.FindBySerial(fire_beetle)
                if not fire_beetle_mobile:
                    continue
                distance = sqrt((Player.Position.X - fire_beetle_mobile.Position.X)**2 + (Player.Position.Y - fire_beetle_mobile.Position.Y)**2)
                if distance > 3:
                    continue
                try:
                    ores = Items.ApplyFilter(ore_filter)
                    total_ore_amount = sum(o.Amount for o in ores if o.ItemID in ORE_TYPES and o.ItemID != 0x1779 and "sand" not in (Items.GetPropStringByIndex(o.Serial, 0) or "Unknown").lower())
                    if total_ore_amount >= ore_amount_threshold:
                        for ore in ores:
                            if ore.ItemID == 0x1779 or "sand" in (Items.GetPropStringByIndex(ore.Serial, 0) or "Unknown").lower():
                                continue
                            Items.UseItem(ore)
                            if Target.WaitForTarget(1000):
                                Target.TargetExecute(fire_beetle)
                                Misc.Pause(500)
                                if Journal.SearchByType('You smelt the ore', 'System') or Journal.SearchByType('You burn away impurities', 'System'):
                                    pass
                        Misc.Pause(1000)
                except Exception:
                    pass
            
            if last_mining_success and Player.Weight >= resource_weight:
                move_all_granite_to_beetle()
                move_resources()
    except Exception:
        pass

if __name__ == '__main__':
    try:
        main()
    except Exception:
        pass