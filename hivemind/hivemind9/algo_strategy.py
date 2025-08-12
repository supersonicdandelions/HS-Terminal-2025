
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
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global dont_spawn
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        global TURRET_COST, WALL_COST, WALL_UPGRADE_COST
        global SCOUT_HEALTH, TURRET_DAMAGE_NORMAL, TURRET_DAMAGE_UPGRADED, BASE_STRUCTURE_POINT_INCOME
        SCOUT_HEALTH= config["unitInformation"][3]["startHealth"]
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
        dont_spawn=False

        MP = 1
        SP = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []

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
        # Now build reactive defenses based on where the enemy scored
        #self.build_reactive_defense(game_state)
        global dont_spawn
        if game_state.get_resource(MP)<20:
            dont_spawn=False

        if True: #game_state.turn_number % 2 == 1:
            # To simplify we will just check sending them from back left and right
            go=False
            scout_spawn_location_options = [[13,14],[14,14],
                                            [11,14],  [16,14],
                                            [9,14],  [18,14],
                                            [7,14],[20,14],
                                            [5,14],  [22,14],
                                            [4,14],  [23,14],
                                            [2,14],  [25,14],
                                            [1,14],[26,14]
            ]
            best_location,left,leastDamage,blocked = self.least_damage_spawn_location(game_state, scout_spawn_location_options)

            if game_state.project_future_MP(1,0)>=20 and not dont_spawn:
                dont_spawn=[best_location[0],13]
                game_state.attempt_remove(dont_spawn)
                go=True
            if blocked:
                leastDamage*=2
            if game_state.get_resource(MP)>=20: #blocked:
                if dont_spawn[0] in [1,26]:
                    if dont_spawn[0]>13:
                        game_state.attempt_spawn(SCOUT, [17,3],5)
                        game_state.attempt_spawn(SCOUT, [13,0],1000)
                    else:
                        game_state.attempt_spawn(SCOUT, [10,3],5)
                        game_state.attempt_spawn(SCOUT, [14,0],1000)
                else:
                    if dont_spawn[0]>13:
                        #game_state.attempt_spawn(SCOUT, [14,0],5)
                        game_state.attempt_spawn(SCOUT, [13,0],1000)
                    else:
                        #game_state.attempt_spawn(SCOUT, [13,0],5)
                        game_state.attempt_spawn(SCOUT, [14,0],1000)
        toUpgrade=[]
        if game_state.turn_number>1:
            toUpgrade=self.get_upgrade_locations(game_state,dont_spawn)

        # First, place basic defenses
        self.build_defences(game_state,dont_spawn,toUpgrade)
        # Lastly, if we have spare SP, let's build some supports
        support_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
        #game_state.attempt_spawn(SUPPORT, support_locations)

    def build_defences(self, game_state,dont_spawn,toUpgrade):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        turret_locations = [[0, 13], [27, 13],[1,13],[2,13],[3,13],[4,13],[5,13],[6,13],[7,13],
                            [8,13],[9,13],[10,13],[11,13],[12,13],[13,13],[14,13],
                            [15,13],[16,13],[17,13],[18,13],[19,13],[20,13],[21,13],
                            [22,13],[23,13],[24,13],[25,13],[26,13]
        ]

        #wall_locations = [[0, 13], [27, 13]]
        # Place turrets that attack enemy units

        #game_state.attempt_spawn(WALL, wall_locations)
        #game_state.attempt_upgrade(wall_locations)

        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        for i in turret_locations:
            if i != dont_spawn:
                game_state.attempt_spawn(TURRET, i)
        all_upgraded=True
        for i in [[3,13],[24,13],[10,13],[17,13]]:
            if not game_state.contains_stationary_unit(i) or not game_state.game_map[i][0].upgraded:
                all_upgraded=False
        for i in toUpgrade:
            game_state.attempt_upgrade(i)

        if all_upgraded:
            for i in [[15,12],[12,12],[17,12],[10,12],[19,12],
                    [8,12],[21,12],[6,12],
                    [15,11],[12,11],[17,11],[10,11],[19,11],
                    [8,11],[21,11],[6,11]]:
                game_state.attempt_spawn(SUPPORT, i)
                game_state.attempt_upgrade(i)
        else:
            for i in [[15,12],[12,12],[17,12],[10,12],[19,12],
                      [8,12],[21,12],[6,12],
                      [15,11],[12,11],[17,11],[10,11],[19,11],
                      [8,11],[21,11],[6,11]]:
                if game_state.get_resource(SP)+BASE_STRUCTURE_POINT_INCOME>=8+4:
                    game_state.attempt_spawn(SUPPORT, i)
                if game_state.get_resource(SP)+BASE_STRUCTURE_POINT_INCOME>=8+4:
                    game_state.attempt_upgrade(i)

        destroyed=0
        """for location in wall_locations:
            if game_state.get_resource(SP)+BASE_STRUCTURE_POINT_INCOME>=destroyed+WALL_COST+WALL_UPGRADE_COST:
                if game_state.contains_stationary_unit(location):
                    unit = game_state.game_map[location][0]
                    if 2*unit.health < unit.max_health:
                        game_state.attempt_remove(location)
                        destroyed+=WALL_COST+WALL_UPGRADE_COST"""
        for location in turret_locations:
            if game_state.get_resource(SP)+BASE_STRUCTURE_POINT_INCOME>=destroyed+TURRET_COST:
                if game_state.contains_stationary_unit(location):
                    unit = game_state.game_map[location][0]
                    if 2*unit.health <= unit.max_health:
                        game_state.attempt_remove(location)
                        destroyed += TURRET_COST


        # upgrade walls so they soak more damage
        if destroyed<=BASE_STRUCTURE_POINT_INCOME:
            game_state.attempt_upgrade(turret_locations)
    def get_upgrade_locations(self,game_state,dont_spawn):
        d={}
        for i in range(0,7):
            d[i]=(3,13)
        for i in range(7,14):
            d[i]=(10,13)
        for i in range(14,21):
            d[i]=(17,13)
        for i in range(21,28):
            d[i]=(24,13)
        locations=set()
        for i in [[1,15],[2,16],[3,17],[4,18],[5,19],[6,20],[7,21],[8,22],
                  [9,23],[10,24],[11,25],[12,26],[13,27],[14,27],[15,26],
                  [16,25],[17,24],[18,23],[19,22],[20,21],[21,20],[22,19],
                  [23,18],[24,17],[25,16],[26,15]]:
            if not game_state.contains_stationary_unit(i):
                path=game_state.find_path_to_edge(i)
                if path[-1][1]==14:
                    locations.add(d[path[-1][0]])
                elif dont_spawn and dont_spawn in path:
                    locations.add(d[dont_spawn[0]])
        return list(locations)


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
    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered


    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
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
