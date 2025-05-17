# This is A Simi auto Lumberjacking Script
#  by Sparkin 5/2025
# Orignal Script was modified by Gork


# System Variables
from System.Collections.Generic import List
from System import Byte, Int32
import clr
clr.AddReference('System.Speech')
from System.Speech.Synthesis import SpeechSynthesizer
from math import sqrt

# Configuration  EDIT THIS SECTION
beetle = 0x070080D0 # S/N oy your packy
logsToBoards = True # If you want boards 
treeCooldown = 1200000  # 20 minutes NO NEED TO CHANGE THIS
alert = False # ON is Safe
scanRadius = 15 # Tiles
axeSerial = 0x640C2454 #Your Axe id here
logBag = 0x5A01E7ED # i use my backpack ID
otherResourceBag = 0x40191C19 # if you need  :P
weightLimit = Player.MaxWeight - 10 # this is stones under your max
dragDelay = 800

# Item IDs
logID = 0x1BDD
boardID = 0x1BD7
otherResourceID = [0x318F, 0x3199, 0x2F5F, 0x3190, 0x3191]
axeList = [0x0F49, 0x13FB, 0x0F47, 0x1443, 0x0F45, 0x0F4B, 0x0F43]
treeStaticIDs = [
    0x0C95, 0x0C96, 0x0C99, 0x0C9B, 0x0C9C, 0x0C9D, 0x0C8A, 0x0CA6,
    0x0CA8, 0x0CAA, 0x0CAB, 0x0CC3, 0x0CC4, 0x0CC8, 0x0CC9, 0x0CCA,
    0x0CCB, 0x0CCC, 0x0CCD, 0x0CD0, 0x0CD3, 0x0CD6, 0x0CD8, 0x0CDA,
    0x0CDD, 0x0CE0, 0x0CE3, 0x0CE6, 0x0CF8, 0x0CFB, 0x0CFE, 0x0D01,
    0x0D25, 0x0D27, 0x0D35, 0x0D37, 0x0D38, 0x0D42, 0x0D43, 0x0D59,
    0x0D70, 0x0D85, 0x0D94, 0x0D96, 0x0D98, 0x0D9A, 0x0D9C, 0x0D9E,
    0x0DA0, 0x0DA2, 0x0DA4, 0x0DA8,
]

# Adjust tree IDs for UoAlive shard
if Misc.ShardName() == 'UoAlive':
    treeStaticIDsToRemove = [0x0C99, 0x0C9A, 0x0C9B, 0x0C9C, 0x0C9D, 0x0CA6, 0x0CC4]
    for treeStaticIDToRemove in treeStaticIDsToRemove:
        if treeStaticIDToRemove in treeStaticIDs:
            treeStaticIDs.remove(treeStaticIDToRemove)

trees = []
onLoop = True
blockCount = 0

class Tree:
    def __init__(self, x, y, z, id):
        self.x = x
        self.y = y
        self.z = z
        self.id = id

def say(text):
    spk = SpeechSynthesizer()
    spk.Speak(text)

def MoveToBeetle():
    global beetle, logID, boardID, dragDelay, onLoop
    
    # Convert logs to boards if specified
    if logsToBoards:
        for item in Player.Backpack.Contains:
            if item.ItemID == logID:
                Items.UseItem(Player.GetItemOnLayer('LeftHand'))
                Target.WaitForTarget(1500, False)
                Target.TargetExecute(item)
                Misc.Pause(dragDelay)

    # Dismount if mounted
    if Player.Mount:
        Mobiles.UseMobile(Player.Serial)
        Misc.Pause(dragDelay)

    # Move items to beetle
    beetle_mobile = Mobiles.FindBySerial(beetle)
    if not beetle_mobile:
        Misc.SendMessage("Beetle not found!", 33)
        onLoop = False
        return

    for item in Player.Backpack.Contains:
        if (logsToBoards and item.ItemID == boardID) or (not logsToBoards and item.ItemID == logID):
            number_in_beetle = GetNumberOfBoardsInBeetle() if logsToBoards else GetNumberOfLogsInBeetle()
            if number_in_beetle + item.Amount < 1600:  # Beetle weight limit
                Items.Move(item.Serial, beetle, 0)
                Misc.Pause(dragDelay)
            else:
                Player.HeadMessage(33, 'BEETLE FULL STOPPING')
                say('Your beetle is full, stop and unload')
                onLoop = False
                return

    # Check for ground items
    groundItems = filterItem([boardID, logID], range=2, movable=True)
    for item in groundItems:
        if (logsToBoards and item.ItemID == boardID) or (not logsToBoards and item.ItemID == logID):
            number_in_beetle = GetNumberOfBoardsInBeetle() if logsToBoards else GetNumberOfLogsInBeetle()
            if number_in_beetle + item.Amount < 1600:
                Items.Move(item.Serial, beetle, 0)
                Misc.Pause(dragDelay)
            else:
                Player.HeadMessage(33, 'MULE FULL STOPPING')
                say('Your Mule is full, stop and unload')
                onLoop = False
                return

    # Remount
    if not Player.Mount:
        Mobiles.UseMobile(beetle)
        Misc.Pause(dragDelay)

def GetNumberOfBoardsInBeetle():
    beetle_mobile = Mobiles.FindBySerial(beetle)
    if not beetle_mobile:
        return 0
    
    number = 0
    for item in beetle_mobile.Backpack.Contains:
        if item.ItemID == boardID:
            number += item.Amount
    return number

def GetNumberOfLogsInBeetle():
    beetle_mobile = Mobiles.FindBySerial(beetle)
    if not beetle_mobile:
        return 0
    
    number = 0
    for item in beetle_mobile.Backpack.Contains:
        if item.ItemID == logID:
            number += item.Amount
    return number

def filterItem(id, range=2, movable=True):
    fil = Items.Filter()
    fil.Movable = movable
    fil.RangeMax = range
    # Convert Python list to List[Int32]
    graphics_list = List[Int32]()
    for item_id in id:
        graphics_list.Add(item_id)
    fil.Graphics = graphics_list
    return Items.ApplyFilter(fil)

def EquipAxe():
    global axeSerial, onLoop
    leftHand = Player.CheckLayer('LeftHand')
    if not leftHand:
        for item in Player.Backpack.Contains:
            if item.ItemID in axeList:
                Player.EquipItem(item.Serial)
                Misc.Pause(600)
                axeSerial = Player.GetItemOnLayer('LeftHand').Serial
                return
        Player.HeadMessage(35, 'You must have an axe to chop trees!')
        Misc.Pause(1000)
        onLoop = False
    elif Player.GetItemOnLayer('LeftHand').ItemID in axeList:
        axeSerial = Player.GetItemOnLayer('LeftHand').Serial
    else:
        Player.HeadMessage(35, 'You must have an axe to chop trees!')
        Misc.Pause(1000)
        onLoop = False

def ScanStatic():
    global trees
    Misc.SendMessage('--> Scan Tile Started', 77)
    minX = Player.Position.X - scanRadius
    maxX = Player.Position.X + scanRadius
    minY = Player.Position.Y - scanRadius
    maxY = Player.Position.Y + scanRadius
    x = minX
    y = minY
    while x <= maxX:
        while y <= maxY:
            staticsTileInfo = Statics.GetStaticsTileInfo(x, y, Player.Map)
            if staticsTileInfo.Count > 0:
                for tile in staticsTileInfo:
                    for staticid in treeStaticIDs:
                        if staticid == tile.StaticID and not Timer.Check('%i,%i' % (x, y)):
                            trees.append(Tree(x, y, tile.StaticZ, tile.StaticID))
            y = y + 1
        y = minY
        x = x + 1
    trees = sorted(trees, key=lambda tree: sqrt(pow((tree.x - Player.Position.X), 2) + pow((tree.y - Player.Position.Y), 2)))
    Misc.SendMessage('--> Total Trees: %i' % len(trees), 77)

def RangeTree():
    playerX = Player.Position.X
    playerY = Player.Position.Y
    treeX = trees[0].x
    treeY = trees[0].y
    return (treeX >= playerX - 1 and treeX <= playerX + 1) and (treeY >= playerY - 1 and treeY <= playerY + 1)

def MoveToTree():
    global trees
    if not trees:
        return
    pathlock = 0
    Misc.SendMessage('--> Moving to TreeSpot: %i, %i' % (trees[0].x, trees[0].y), 77)
    Misc.Resync()
    treeCoords = PathFinding.Route()
    treeCoords.MaxRetry = 5
    treeCoords.StopIfStuck = False
    treeCoords.X = trees[0].x
    treeCoords.Y = trees[0].y + 1
    
    if PathFinding.Go(treeCoords):
        Misc.Pause(1000)
    else:
        Misc.Resync()
        treeCoords.X = trees[0].x + 1
        treeCoords.Y = trees[0].y
        if PathFinding.Go(treeCoords):
            Misc.SendMessage('Second Try')
        else:
            treeCoords.X = trees[0].x - 1
            treeCoords.Y = trees[0].y
            if PathFinding.Go(treeCoords):
                Misc.SendMessage('Third Try')
            else:
                treeCoords.X = trees[0].x
                treeCoords.Y = trees[0].y - 1
                Misc.SendMessage('Final Try')
                if not PathFinding.Go(treeCoords):
                    return
    
    Misc.Resync()
    while not RangeTree():
        Misc.Pause(100)
        pathlock += 1
        if pathlock > 350:
            Misc.Resync()
            treeCoords = PathFinding.Route()
            treeCoords.MaxRetry = 5
            treeCoords.StopIfStuck = False
            treeCoords.X = trees[0].x
            treeCoords.Y = trees[0].y + 1
            if PathFinding.Go(treeCoords):
                Misc.Pause(1000)
            else:
                treeCoords.X = trees[0].x + 1
                treeCoords.Y = trees[0].y
                if PathFinding.Go(treeCoords):
                    Misc.SendMessage('Second Try')
                else:
                    treeCoords.X = trees[0].x - 1
                    treeCoords.Y = trees[0].y
                    if PathFinding.Go(treeCoords):
                        Misc.SendMessage('Third Try')
                    else:
                        treeCoords.X = trees[0].x
                        treeCoords.Y = trees[0].y - 1
                        Misc.SendMessage('Final Try')
                        if not PathFinding.Go(treeCoords):
                            return
            pathlock = 0
    Misc.SendMessage('--> Reached TreeSpot: %i, %i' % (trees[0].x, trees[0].y), 77)

def CutTree():
    global blockCount, trees
    if not trees:
        return
    if Target.HasTarget():
        Misc.SendMessage('--> Detected block, canceling target!', 77)
        Target.Cancel()
        Misc.Pause(500)

    if Player.Weight >= weightLimit:
        MoveToBeetle()
        MoveToTree()

    Journal.Clear()
    Items.UseItem(Player.GetItemOnLayer('LeftHand'))
    Target.WaitForTarget(2000, True)
    Target.TargetExecute(trees[0].x, trees[0].y, trees[0].z, trees[0].id)
    Timer.Create('chopTimer', 10000)
    while not (Journal.SearchByType('You hack at the tree for a while, but fail to produce any useable wood.', 'System') or 
               Journal.SearchByType('You chop some', 'System') or 
               Journal.SearchByType('There\'s not enough wood here to harvest.', 'System') or
               not Timer.Check('chopTimer')):
        Misc.Pause(100)

    if Journal.SearchByType('There\'s not enough wood here to harvest.', 'System'):
        Misc.SendMessage('--> Tree change', 77)
        Timer.Create('%i,%i' % (trees[0].x, trees[0].y), treeCooldown)
    elif Journal.Search('That is too far away'):
        blockCount += 1
        Journal.Clear()
        if blockCount > 3:
            blockCount = 0
            Misc.SendMessage('--> Possible block detected tree change', 77)
            Timer.Create('%i,%i' % (trees[0].x, trees[0].y), treeCooldown)
        else:
            CutTree()
    elif Journal.Search('bloodwood'):
        Player.HeadMessage(1194, 'BLOODWOOD!')
        Timer.Create('chopTimer', 10000)
        CutTree()
    elif Journal.Search('heartwood'):
        Player.HeadMessage(1193, 'HEARTWOOD!')
        Timer.Create('chopTimer', 10000)
        CutTree()
    elif Journal.Search('frostwood'):
        Player.HeadMessage(1151, 'FROSTWOOD!')
        Timer.Create('chopTimer', 10000)
        CutTree()
    elif not Timer.Check('chopTimer'):
        Misc.SendMessage('--> Tree change', 77)
        Timer.Create('%i,%i' % (trees[0].x, trees[0].y), treeCooldown)
    else:
        CutTree()

toonFilter = Mobiles.Filter()
toonFilter.Enabled = True
toonFilter.RangeMin = -1
toonFilter.RangeMax = -1
toonFilter.IsHuman = True 
toonFilter.Friend = False
toonFilter.Notorieties = List[Byte](bytes([1,2,3,4,5,6,7]))

invulFilter = Mobiles.Filter()
invulFilter.Enabled = True
invulFilter.RangeMin = -1
invulFilter.RangeMax = -1
invulFilter.Friend = False
invulFilter.Notorieties = List[Byte](bytes([7]))

def safteyNet():
    if alert:
        toon = Mobiles.ApplyFilter(toonFilter)
        invul = Mobiles.ApplyFilter(invulFilter)
        if toon:
            Misc.FocusUOWindow()
            say("Hey, someone is here. You should tab over and take a look At The Screen")
            toonName = Mobiles.Select(toon, 'Nearest')
            if toonName:
                Misc.SendMessage('Toon Near: ' + toonName.Name, 33)
        elif invul:
            say("Hey, something invulnerable here. You should tab over and take a look")
            invulName = Mobiles.Select(invul, 'Nearest')
            if invulName:
                Misc.SendMessage('ALERT: Invul! Who the Hell is ' + invulName.Name, 33)
        else:
            Misc.NoOperation()

# Main execution block
Friend.ChangeList('lj')
Misc.SendMessage('--> Start up Woods', 77)



if onLoop:
    EquipAxe()
    while onLoop:
        ScanStatic()
        if not trees:
            Misc.SendMessage('--> No trees found in range, stopping script. Move to a new location and restart.', 33)
            onLoop = False
            break
        while trees:
            safteyNet()
            MoveToTree()
            CutTree()
            trees.pop(0)
            trees = sorted(trees, key=lambda tree: sqrt(pow((tree.x - Player.Position.X), 2) + pow((tree.y - Player.Position.Y), 2)))
        trees = []
        Misc.Pause(100)