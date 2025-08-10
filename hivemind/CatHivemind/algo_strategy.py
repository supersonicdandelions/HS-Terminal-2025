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
        global TURRET_COST, WALL_COST, WALL_UPGRADE_COST
        global SCOUT_HEALTH, TURRET_DAMAGE_NORMAL, TURRET_DAMAGE_UPGRADED, BASE_STRUCTURE_POINT_INCOME
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        TURRET_COST=1
        WALL_COST=3
        WALL_UPGRADE_COST=3
        TURRET_DAMAGE_NORMAL= 3
        TURRET_DAMAGE_UPGRADED=20
        BASE_STRUCTURE_POINT_INCOME=5
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
        self.sideWall = False
        self.goalMP = 9999

        self.leftHit = False
        self.rightHit = False
        self.hit = False

        self.turret_locations = []
        for x in range(2, 26):
            self.turret_locations.append([x, 13])
        self.turret_locations.append([24, 12])

        self.isLeft = True
        self.isRight = False
        self.centerHole = False
        self.dont_spawn = False



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
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)

        game_state.submit_turn()
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
        trapped = True
        if self.isLeft:
            trapped = game_state.contains_stationary_unit([1, 13]) or game_state.contains_stationary_unit([1, 12])
        elif self.isRight:
            trapped = game_state.contains_stationary_unit([26, 13]) or game_state.contains_stationary_unit([26, 12])
        elif self.centerHole and self.dont_spawn != False:
            trapped = game_state.contains_stationary_unit(self.dont_spawn)
        if game_state.get_resource(MP) >= self.goalMP and not trapped:
            self.decide_tower(game_state)
            

    def calculate_attack_parameters(self, game_state):
        """Calculate and store attack parameters as instance variables"""
        numSpawnable = int(game_state.get_resource(MP))
        self.hasWall = False
        self.behindTurrets = 0
        self.up_front = 0
        self.defaultValue = 4
        
        if game_state.turn_number <= 5:
            self.defaultValue = 5
        if numSpawnable <= 15.99:
            self.defaultValue = 5
        # Check for upgraded turrets from the enemy
        for x in range(0, 5):
            for y in range(14, 16):
                check_x = x if self.isLeft else 27 - x
                if game_state.contains_stationary_unit([check_x, y]):
                    unit = game_state.game_map[[check_x, y]]
                    if unit[0].unit_type == TURRET and unit[0].upgraded:
                        if y == 14:
                            self.up_front += 1
                        else:
                            self.behindTurrets += 1
        wall_x = 0 if self.isLeft else 27
        if game_state.contains_stationary_unit([wall_x, 14]):
            unit1 = game_state.game_map[[wall_x, 14]]
            if unit1[0].unit_type == WALL:
                self.hasWall = True
                self.defaultValue = 5
        if self.isStaggerTurret:
            self.defaultValue += 2 * self.up_front + self.behindTurrets
            check_x = 3 if self.isLeft else 27 - 3
            if not game_state.contains_stationary_unit([check_x, 14]):
                self.defaultValue = min(self.defaultValue, 5)
        else:
            self.defaultValue += 2 * self.up_front + (self.behindTurrets + 1) // 2
        
    def determine_interval(self, game_state):
        scout_spawn_location_options = [[13,14], [14,14], [11,14], [16,14], 
                        [9,14], [18,14], [7,14], [20,14],
                        [5,14], [22,14], [23,14],
                        [1,14], [26,14]]
        best_location,left,leastDamage,blocked = self.least_damage_spawn_location(game_state, scout_spawn_location_options)
        if best_location != [1, 14] and best_location != [26, 14]:
            if self.dont_spawn == False:
                self.dont_spawn = [best_location[0], 13]
            self.isLeft = False
            self.isRight = False
            self.centerHole = True
            self.goalMP = 17
            return
        self.dont_spawn = False
        self.centerHole = False
        if self.isLeft == False and self.isRight == False:
            self.isLeft = random.choice([True, False])
            if self.isLeft:
                self.isRight = False
            else:
                self.isRight = True
        self.calculate_attack_parameters(game_state)
        minMP = min(19.99, 8.99 + self.defaultValue)
        if (not self.isWallTactic and self.hasWall):
            minMP = 16.99
        if game_state.enemy_health <= 12:
            minMP = max(minMP, game_state.enemy_health + 2 + self.defaultValue)
        else:
            minMP = max(minMP, math.ceil(game_state.enemy_health / 2) + 2 + self.defaultValue)
        if self.isStaggerTurret:
            minMP = max(minMP, 15 + self.up_front + self.behindTurrets // 2)
        minMP += self.up_front + (self.behindTurrets + 1) // 2
        if minMP > 20:
            minMP = self.defaultValue + 12
        self.goalMP = minMP
        
    def decide_tower(self, game_state):
        # Calculate attack parameters
        if self.centerHole:
            if self.dont_spawn[0] <= 13:
                game_state.attempt_spawn(SCOUT, [13, 0], 5)
                game_state.attempt_spawn(SCOUT, [14, 0], 999)
            else:
                game_state.attempt_spawn(SCOUT, [14, 0], 5)
                game_state.attempt_spawn(SCOUT, [13, 0], 999)
            return
        self.calculate_attack_parameters(game_state)
        center_value = 14 if self.isLeft else 13
        initSpawn = self.defaultValue
        if not self.isWallTactic and not self.isStaggerTurret:
            self.defaultValue = 0 # one rush
        if self.isStaggerTurret:
            spawn_x = 8 if self.isLeft else 27 - 8
            game_state.attempt_spawn(SCOUT, [spawn_x, 5], initSpawn)
            game_state.attempt_spawn(SCOUT, [center_value, 0], 999)
        elif self.isWallTactic:
            spawn_x = 12 if self.isLeft else 27 - 12
            game_state.attempt_spawn(SCOUT, [spawn_x, 1], initSpawn)
            game_state.attempt_spawn(SCOUT, [center_value, 0], 999)
        else:
            game_state.attempt_spawn(SCOUT, [center_value, 0], 999)
        self.isLeft = random.choice([True, False])


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
        
        
        gamelib.debug_write("Goal MP: {}".format(self.goalMP))
        gamelib.debug_write("Attack state: {}, {}, {}".format(self.isLeft, self.centerHole, self.isRight))
        gamelib.debug_write("Goal break {}".format(self.dont_spawn))
        if game_state.turn_number >= 2:
            self.determine_interval(game_state)
        wall_locations = [
            [0, 13], [27, 13]
        ]

        # game_state.turn_number % self.interval != 0 and 
        blockage_locations = [
            [1, 13], [1, 12], [2, 12]
        ]
        flipped_blockage_locations = [
            [26, 13], [26, 12], [25, 12]
        ]
        if (game_state.project_future_MP() < self.goalMP):
            game_state.attempt_spawn(TURRET, blockage_locations)
            game_state.attempt_spawn(TURRET, flipped_blockage_locations)
        else:
            if self.isLeft:
                game_state.attempt_remove(blockage_locations)
                game_state.attempt_spawn(TURRET, flipped_blockage_locations)
            elif self.isRight:
                game_state.attempt_remove(flipped_blockage_locations)
                game_state.attempt_spawn(TURRET, blockage_locations)
            elif self.centerHole:
                for i in range(14):
                    game_state.attempt_remove([self.dont_spawn[0], i])
                game_state.attempt_spawn(TURRET, blockage_locations)
                game_state.attempt_spawn(TURRET, flipped_blockage_locations)
        support_locations = []
        for x in range(8, 24, 2):
            support_locations.append([x, 12])
        if game_state.turn_number == 5:
            self.turret_locations.append([3, 12])
            self.turret_locations.append([4, 12])

        temp = self.turret_locations.copy()
        for location in self.turret_locations:
            if not has_turret(location) or get_turret_health(location) < 30:
                if game_state.project_future_MP() >= self.goalMP and self.dont_spawn != False and self.dont_spawn[0] == location[0]:
                    continue # skip
                game_state.attempt_spawn(TURRET, location)
                if location[1] <= 11: 
                    continue # too low
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
    
        for i in range(2):
            location = support_locations[i]
            game_state.attempt_spawn(SUPPORT, location)
            game_state.attempt_upgrade(location)
        left_turret = [[3, 13], [2, 13], [3, 12]]
        right_turret = [[24, 13], [25, 13], [24, 12]]

        if not self.hit or (self.leftHit and self.rightHit):
            game_state.attempt_upgrade(right_turret[0])
            game_state.attempt_upgrade(left_turret[0])
        if self.leftHit:
            game_state.attempt_upgrade(left_turret[0])
        if self.rightHit:
            game_state.attempt_upgrade(right_turret[0])
        
        
        for i in range(4):
            if game_state.get_resource(SP) < 8:
                break
            location = support_locations[i]
            game_state.attempt_spawn(SUPPORT, location)
            game_state.attempt_upgrade(location)

        if not self.hit or (self.leftHit and self.rightHit):
            game_state.attempt_upgrade(left_turret)
            game_state.attempt_upgrade(right_turret)
        if self.leftHit:
            game_state.attempt_upgrade(left_turret)
        if self.rightHit:
            game_state.attempt_upgrade(right_turret)
        turret_update_order_with_turrets = self.turret_locations.copy()
        turret_update_order_with_turrets.sort(key=get_turret_health)
        
        for location in turret_update_order_with_turrets:
            if (game_state.get_resource(SP) >= 15):
                if get_turret_health(location) < 30:
                    game_state.attempt_remove(location)
            else:
                if get_turret_health(location) < 20:
                    game_state.attempt_remove(location)
        for location in support_locations:
            if (game_state.get_resource(SP) >= 8):
                # Attempt to upgrade the support at the location
                game_state.attempt_spawn(SUPPORT, [location[0], location[1]])
                if game_state.contains_stationary_unit(location):
                    unit = game_state.game_map[location]
                    if unit[0].unit_type == SUPPORT:
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
        # Let's record at what position we get scored on
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                self.hit = True
                if location[0] <= 13:
                    self.leftHit = True
                else:
                    self.rightHit = True
    def least_damage_spawn_location(self, game_state, location_options):
        damages = []
        left = []
        blocked=True
        for location in location_options:
            path1 = game_state.find_path_to_edge(location,game_state.game_map.TOP_LEFT)
            damage1 = 0
            if path1[-1][1]-path1[-1][0]==14 or path1[-1][1]+path1[-1][0]==51:
                blocked=False
                if location[0]>2 and location[0]<25:
                    damage1-=50
            elif location[0] not in [1,26]:
                damage1=10000
            for path_location in path1:
                attackers = game_state.get_attackers(path_location, 0)
                for attacker in attackers:
                    if attacker.upgraded:
                        damage1 += TURRET_DAMAGE_UPGRADED
                    else:
                        damage1 += TURRET_DAMAGE_NORMAL
            path2=game_state.find_path_to_edge(location,game_state.game_map.TOP_RIGHT)
            damage2=0
            if path2[-1][1]-path2[-1][0]==14 or path2[-1][1]+path2[-1][0]==51:
                blocked=False
                if location[0]>2 and location[0]<25:
                    damage2-=50
            elif location[0] not in [1,26]:
                damage2=10000
            for path_location in path2:
                attackers = game_state.get_attackers(path_location, 0)
                for attacker in attackers:
                    if attacker.upgraded:
                        damage2 += TURRET_DAMAGE_UPGRADED
                    else:
                        damage2 += TURRET_DAMAGE_NORMAL
            if damage1<damage2:
                damages.append(damage1)
                left.append(False)
                gamelib.debug_write(path1)
            else:
                gamelib.debug_write(path2)
                damages.append(damage2)
                left.append(True)
            gamelib.debug_write(location,"value",min(damage1,damage2))
        leastDamage = min(damages)
        return (location_options[damages.index(min(damages))],left[damages.index(min(damages))],leastDamage,blocked)
if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
