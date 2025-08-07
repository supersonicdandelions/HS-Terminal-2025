

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
        # First, place basic defenses
        self.build_defences(game_state)
        # Now build reactive defenses based on where the enemy scored
        #self.build_reactive_defense(game_state)


        if game_state.get_resource(MP,0)>10: #game_state.turn_number % 2 == 1:
            # To simplify we will just check sending them from back left and right
            scout_spawn_location_options = [[13, 0], [14, 0]]
            #scout_spawn_location_options = [[14, 0]]
            best_location,leastDamage,blocked = self.least_damage_spawn_location(game_state, scout_spawn_location_options)
            gamelib.debug_write("leastDamage= {} MP*ScoutHealth= {}".format(leastDamage, game_state.get_resource(MP,0)*SCOUT_HEALTH))
            gamelib.debug_write("normal damage " , TURRET_DAMAGE_NORMAL)
            gamelib.debug_write("upgraded damage " , TURRET_DAMAGE_UPGRADED)
            if blocked:
                leastDamage*=2
            if leastDamage >= game_state.get_resource(MP,0)*SCOUT_HEALTH and game_state.get_resource(MP,0)+1<game_state.project_future_MP(1,0):#the scout health number
                #build demolishers
                #O is you 1 is enemy
                if False: #game_state.get_resource(MP,0) >= 20:
                    game_state.attempt_spawn(DEMOLISHER, best_location, 1000)
            else:
                if blocked:
                    if False: #best_location==[13,0]:
                        game_state.attempt_spawn(SCOUT, [12, 1], int(game_state.get_resource(MP,0))//2)
                        game_state.attempt_spawn(SCOUT, [13,0],1000)
                    else:
                        game_state.attempt_spawn(SCOUT, [16, 2], int(game_state.get_resource(MP,0))//2)
                        game_state.attempt_spawn(SCOUT, [14,0],1000)
                else:
                    game_state.attempt_spawn(SCOUT, best_location, 1000)

        # Lastly, if we have spare SP, let's build some supports
        support_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
        #game_state.attempt_spawn(SUPPORT, support_locations)

    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        turret_locations = [
            [1,12],
            [26, 12],
            [3, 10],
            [24, 10],
            [25,11],
            [4, 10],
            [23, 10],
            [7, 10],
            [20, 10],
            [4, 9],
            [23, 9],
            [3, 11],
            [24, 11],
            [2, 12],
            [25, 12],
            [1, 13],
            [26, 13],
            [10, 10],
            [17, 10],
            [13, 10],
            [14, 10],
            [6, 10], [22,10], [8, 10], [21, 10], [9, 10], [19, 10],  [11, 10],[18, 10], [12, 10],
            [15, 10],[16, 10],
            [5,8],[6,8],[7,8],[8,8],[9,8],[10,8],[11,8],[12,8],[13,8],[14,8],[15,8],[16,8],[17,8],[18,8],[19,8],[21,9],
            #extra for later
            [22,9]
        ]

        wall_locations = [[0, 13], [27, 13]]
        # Place turrets that attack enemy units

        game_state.attempt_spawn(WALL, wall_locations)
        game_state.attempt_upgrade(wall_locations)

        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(TURRET, turret_locations)

        support_locations = [[2, 11]]
        game_state.attempt_spawn(SUPPORT, support_locations)

        destroyed=0
        for location in wall_locations:
            if game_state.get_resource(SP)+BASE_STRUCTURE_POINT_INCOME>destroyed:
                if game_state.contains_stationary_unit(location):
                    unit = game_state.game_map[location][0]
                    if 2*unit.health < unit.max_health:
                        game_state.attempt_remove(location)
                        destroyed+=WALL_COST+WALL_UPGRADE_COST

        for location in turret_locations:
            if game_state.get_resource(SP)+BASE_STRUCTURE_POINT_INCOME>destroyed:
                if game_state.contains_stationary_unit(location):
                    unit = game_state.game_map[location][0]
                    if 2*unit.health <= unit.max_health:
                        game_state.attempt_remove(location)
                        destroyed += TURRET_COST


        # upgrade walls so they soak more damage
        if destroyed<=BASE_STRUCTURE_POINT_INCOME:
            game_state.attempt_upgrade(turret_locations)

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1]+1]
            game_state.attempt_spawn(TURRET, build_location)

    def stall_with_interceptors(self, game_state):
        """
        Send out interceptors at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        # Remove locations that are blocked by our own structures 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        # While we have remaining MP to spend lets send out interceptors randomly.
        while game_state.get_resource(MP) >= game_state.type_cost(INTERCEPTOR)[MP] and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]
            
            game_state.attempt_spawn(INTERCEPTOR, deploy_location)
            """
            We don't have to remove the location since multiple mobile 
            units can occupy the same space.
            """

    def demolisher_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our demolisher can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [WALL, TURRET, SUPPORT]
        cheapest_unit = WALL
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost[game_state.MP] < gamelib.GameUnit(cheapest_unit, game_state.config).cost[game_state.MP]:
                cheapest_unit = unit
        cheapest_unit=TURRET  # BAD BAD BAD! We are hardcoding the cheapest unit to TURRET for this example.

        # Now let's build out a line of stationary units. This will prevent our demolisher from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn demolishers next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(DEMOLISHER, [22, 8], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        damages = []
        blocked=True
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            if path[-1][1]-path[-1][0]==14 or path[-1][1]+path[-1][0]==51:
                blocked=False
            for path_location in path:
                attackers = game_state.get_attackers(path_location, 0)
                for attacker in attackers:
                    if attacker.upgraded:
                        damage += TURRET_DAMAGE_UPGRADED
                    else:
                        damage += TURRET_DAMAGE_NORMAL
            damages.append(damage)
        leastDamage = min(damages)
        return (location_options[damages.index(min(damages))],leastDamage,blocked)
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
