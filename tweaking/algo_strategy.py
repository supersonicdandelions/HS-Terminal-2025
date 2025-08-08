import gamelib
import random
import math
import warnings
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""




class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        import time
        seed = int(time.time() * 1000000) % maxsize
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))
    

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []
        self.time = 0
        self.last_enemy_hp = 30
        self.interval = 4
        self.sinceDamage = 0
        self.isWallTactic = False
        self.isStaggerTurret = False
        self.turret_locations = []
        for x in range(2, 7):
            self.turret_locations.append([x, 13])
        for x in range(11, 27):
            self.turret_locations.append([x, 12])
        self.turret_locations.append([7, 12])
        self.turret_locations.append([8, 11])
        self.turret_locations.append([9, 10])
        self.turret_locations.append([10, 11])
        self.turret_locations.append([24, 13])
        self.turret_locations.append([25, 13])
        self.turret_locations.append([26, 13])
        


    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """

        
        game_state = gamelib.GameState(self.config, turn_state)
        
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        # game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)

        game_state.submit_turn()
        # if (game_state.enemy_health >= self.last_enemy_hp and self.time == 0):
        #     self.interval += 1
        self.time += 1
        if (game_state.enemy_health == self.last_enemy_hp):
            self.sinceDamage += 1
        else:
            self.sinceDamage = 0
        self.last_enemy_hp = game_state.enemy_health


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """
    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some interceptors early on.
        We will place turrets near locations the opponent managed to score on.
        For offense we will use long range demolishers if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Scouts to try and score quickly.
        """
        # First, place basic defenses
        self.build_defences(game_state)
        # Now build reactive defenses based on where the enemy scored
        # self.build_reactive_defense(game_state) erm stop doing that
        if (self.time % self.interval == 0) and game_state.turn_number > 0:
            self.decide_tower(game_state)

    def determine_interval(self, game_state, up_front, behindTurrets, hasWall, spent=True):
        self.time = 0
        points_per_turn = 5 + game_state.turn_number//10
        rounds = 0
        futureMP = game_state.get_resource(MP) % 1
        if not spent:
            futureMP = game_state.get_resource(MP)
        minMP = min(19.99, 14.99 + math.floor(up_front*1.5) + (behindTurrets + 1) // 2)
        if (not self.isWallTactic and hasWall):
            minMP = 16.99
        if game_state.enemy_health <= 15:
            minMP = math.max(minMP, game_state.enemy_health + 2)
            if hasWall:
                minMP = math.max(minMP, 4 + up_front + game_state.enemy_health + 2)
        if self.isStaggerTurret:
            minMP = max(minMP, 15 + 2 * up_front + (behindTurrets + 1) // 2)
        while (futureMP < minMP):
            futureMP *= 0.75
            futureMP += points_per_turn
            rounds += 1
            points_per_turn = 5 + (game_state.turn_number + rounds)//10
            futureMP = round(futureMP*10) / 10
        self.interval = max(1, rounds)
    def decide_tower(self, game_state):
        numSpawnable = int(game_state.get_resource(MP));
        hasWall = False
        # check for upgraded turrets from the enemy
        behindTurrets = 0
        up_front = 0
        defaultValue = 3
        if game_state.turn_number <= 5:
            defaultValue = 4
        if numSpawnable <= 15.99:
            defaultValue = 4
        for x in range(0, 5):
            for y in range(14, 16):
                if game_state.contains_stationary_unit([x, y]):
                    unit = game_state.game_map[[x, y]]
                    if unit[0].unit_type == TURRET and unit[0].upgraded:
                        if y == 14:
                            up_front += 1
                        else:
                            behindTurrets += 1
        if game_state.contains_stationary_unit([0, 14]):
            unit1 = game_state.game_map[[0, 14]]
            if unit1[0].unit_type == WALL:
                hasWall = True
                defaultValue = 5
        initSpawn = up_front + defaultValue
        if not self.isWallTactic and numSpawnable - initSpawn < 10.99:
            self.determine_interval(game_state, up_front, behindTurrets, hasWall, False)
            return
        
        if self.isStaggerTurret:
            initSpawn = 3
            game_state.attempt_spawn(SCOUT, [3, 10], initSpawn)
            game_state.attempt_spawn(SCOUT, [14, 0], 999)
        elif self.isWallTactic:
            game_state.attempt_spawn(SCOUT, [12, 1], initSpawn)
            game_state.attempt_spawn(SCOUT, [14, 0], 999)
        else:
            game_state.attempt_spawn(SCOUT, [14, 0], 999)

        self.determine_interval(game_state, up_front, behindTurrets, hasWall)


    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download
        # Sort turret locations by health remaining (lowest health first)
        def get_turret_health(location):
            if game_state.contains_stationary_unit(location):
                units = game_state.game_map[location]
                for unit in units:
                    if unit.unit_type == TURRET and unit.player_index == 0:  # our turret
                        return unit.health
            return float('inf')  # No turret at location, put at end
        
        def has_turret(location):
            if game_state.contains_stationary_unit(location):
                units = game_state.game_map[location]
                for unit in units:
                    if unit.unit_type == TURRET and unit.player_index == 0:  # our turret
                        return True
            return False
        wall_locations = [
            [0, 13], [27, 13]
        ]

        # game_state.turn_number % self.interval != 0 and 
        blockage_locations = [
            [1, 13], [1, 12], [2, 12]
        ]
        if ((self.time % self.interval != 0 and self.time % self.interval != self.interval - 1) or game_state.turn_number == 0):
            game_state.attempt_spawn(TURRET, blockage_locations)
        else:
            game_state.attempt_remove(blockage_locations)
        support_locations = [
            [10, 9], [6, 10], [6, 11], [6, 12],
            [7, 10], [7, 11],
            [10, 10],
            [11, 10], [11, 11],
            [12, 10], [12, 11],
            [13, 10], [13, 11]
        ]
        if game_state.turn_number == 5:
            self.turret_locations.append([3, 12])
            self.turret_locations.append([4, 12])
            self.turret_locations.append([5, 12])
            self.turret_locations.append([24, 11])
            self.turret_locations.append([25, 11])

        temp = self.turret_locations.copy()
        for location in self.turret_locations:
            if not has_turret(location) or get_turret_health(location) < 30:
                game_state.attempt_spawn(TURRET, location)
                if game_state.game_map.in_arena_bounds([location[0], location[1]-3]) and game_state.turn_number > 0 and game_state.get_resource(SP) >= 1:
                    game_state.attempt_spawn(TURRET, [location[0], location[1] - 1])
                    temp.append([location[0], location[1] - 1])
        self.turret_locations = temp.copy()
        for location in wall_locations:
            if not game_state.contains_stationary_unit(location):
                game_state.attempt_spawn(WALL, location)
                game_state.attempt_upgrade(location)
                continue
            game_state.attempt_upgrade(location)
            unit = game_state.game_map[location]
            if unit[0].health < 90 and unit[0].health != 60:
                game_state.attempt_remove(location)
        # if has_turret([25, 13]):
        #     if random.random() < 0.05:
        #         game_state.attempt_remove([26, 13])
        # else:
        #     if random.random() < 0.1:
        #         game_state.attempt_spawn(TURRET, [26, 13])
    
        for i in range(4):
            location = support_locations[i]
            game_state.attempt_spawn(SUPPORT, location)
            game_state.attempt_upgrade(location)
        turret_upgrade_locations = [
            [24, 13], [3, 13], [25, 12], [24, 12], [2, 13]
        ]
        game_state.attempt_upgrade(turret_upgrade_locations)


        
        turret_update_order_with_turrets = self.turret_locations.copy()
        turret_update_order_with_turrets.sort(key=get_turret_health)
        
        for location in turret_update_order_with_turrets:
            if (game_state.get_resource(SP) >= 15):
                if get_turret_health(location) < 30:
                    game_state.attempt_remove(location)
            else:
                if get_turret_health(location) < 10:
                    game_state.attempt_remove(location)
        for location in support_locations:
            if (game_state.get_resource(SP) >= 8):
                # Attempt to upgrade the support at the location
                game_state.attempt_spawn(SUPPORT, [location[0], location[1]])
                game_state.attempt_upgrade(location)
            else:
                break
        
    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """

        state = json.loads(turn_string)

        # Check if anything is being built/spawned on (1, 14)
        events = state["events"]
        spawns = events.get("spawn", [])
        for spawn in spawns:
            location = spawn[0]           # [x, y] location where unit is spawned
            unit_type = spawn[1]          # Unit type being spawned
            unit_id = spawn[2]            # ID of spawned unit
            player_owner = spawn[3]       # Player that owns the spawned unit (1 or 2)
            
            if location == [1, 14]:
                self.isWallTactic = True
                self.isStaggerTurret = False
        for spawn in spawns:
            location = spawn[0]
            unit_type = spawn[1]
            if location == [2, 14] and not self.isWallTactic:
                self.isStaggerTurret = True
        return
        # Let's record at what position we get scored on
        # Check if opponent placed any units
        state = json.loads(turn_string)
        events = state["events"]
        spawns = events.get("spawn", [])
        for spawn in spawns:
            location = spawn[0]
            unit_type = spawn[1]
            unit_owner_self = True if spawn[3] == 1 else False
            if not unit_owner_self:
                gamelib.debug_write("Opponent placed {} at: {}".format(unit_type, location))
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
