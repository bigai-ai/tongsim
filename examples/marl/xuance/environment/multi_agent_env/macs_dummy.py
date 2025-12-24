"""
Multi-Agent Cooperative Survival & Rivalry (MACS) Environment

This module implements a sophisticated multi-agent reinforcement learning environment
built on top of TongSim and Unreal Engine. The environment simulates multiple parallel
arenas where pursuing agents must learn to cooperate in capturing "food" (coins) while
avoiding "poison" entities.

Key Features:
    - Multiple fully independent parallel environment instances (arenas)
    - Ray-based sensor perception system for environmental awareness
    - Complex reward mechanism including cooperative capture, avoidance penalties, and movement costs
    - High-performance async API calls for maximum simulation throughput
    - Configurable cooperation requirements and agent capabilities

The environment is designed for studying emergent cooperative behaviors and multi-agent
learning in competitive survival scenarios.
"""

import asyncio
from collections import defaultdict
from typing import Any

import gymnasium as gym
import numpy as np
import tongsim as ts
from gymnasium import spaces
from gymnasium.utils import seeding
from tongsim.type.rl_demo import CollisionObjectType, RLDemoOrientationMode

from xuance.environment.multi_agent_env.utils import (
    DEFAULT_CONFIG,
    calculate_bounce_velocity_sample,
    convert_bytes_le_to_guid_string,
    generate_circular_rays,
    generate_safe_random_location,
    get_actor_transform_safe,
    get_grid_anchor,
    run_and_time_task,
    spawn_actors_concurrently,
)


class MACS(gym.Env):
    """
    Multi-Agent Cooperative Survival & Rivalry (MACS) environment.

    This is a complex multi-agent environment based on TongSim and Unreal Engine.
    In multiple parallel arenas, pursuing agents (Pursuers) must learn to cooperate
    in capturing "food" entities (Coins) while avoiding "poison" entities.

    Key Features:
        - Multiple fully independent parallel environment instances (Arenas)
        - Ray-based sensor perception for environmental awareness
        - Complex reward mechanism with cooperative capture, avoidance penalties, and movement costs
        - High-performance async API calls for maximum simulation throughput

    Attributes:
        num_arenas (int): Number of parallel arenas running simultaneously.
        n_rescuers (int): Number of pursuing agents per arena.
        n_supplies (int): Number of food entities (coins) per arena.
        n_hazards (int): Number of poison entities per arena.
        n_coop (int): Minimum number of agents required to cooperatively capture food.
        n_sensors (int): Number of ray sensors per agent.
        sensor_range (float): Maximum detection range of ray sensors.
        agents (List[str]): List of agent identifiers.
        observation_space (Dict): Gymnasium observation space definition.
        action_space (Dict): Gymnasium action space definition.
    """

    metadata = {"render_modes": ["human"]}

    # Entity type constants for improved code readability and maintainability
    ENTITY_COIN = "coin"
    ENTITY_POISON = "poison"
    ENTITY_AGENT = "agent"

    # TongSim actor tag constants for collision detection
    TAG_COIN = "RL_Coin"
    TAG_POISON = "RL_Poison"
    TAG_AGENT = "RL_Agent"
    TAG_WALL = "RL_Wall"
    TAG_BLOCK = "RL_Block"

    def __init__(
        self,
        config=None,
        num_arenas: int = 4,
        n_rescuers=5,
        n_supplies=10,
        n_hazards=5,
        n_coop=2,
        n_sensors=30,
        sensor_range=500.0,
        pursuer_max_accel=0.5,
        supply_speed=0.15,
        hazard_speed=0.15,
        hazard_reward=-1.0,
        supply_reward=10.0,
        encounter_reward=0.01,
        thrust_penalty=-0.01,
        local_ratio=0.9,
        speed_features=True,
        max_cycles=500,
        render_mode=None,
        env_seed=0,
        steering_strength=0.1,
    ):
        """
        Initialize the MACS environment.

        Args:
            config: Optional configuration dictionary (currently unused).
            num_arenas (int): Number of parallel arenas to simulate.
            n_rescuers (int): Number of pursuing agents per arena.
            n_supplies (int): Number of food entities (coins) per arena.
            n_hazards (int): Number of poison entities per arena.
            n_coop (int): Minimum number of agents required to cooperatively capture one food entity.
            n_sensors (int): Number of ray sensors per agent for perception.
            sensor_range (float): Maximum detection range of ray sensors (in Unreal units).
            pursuer_max_accel (float): Maximum acceleration of pursuing agents (currently unused).
            supply_speed (float): Movement speed of supply entities.
            hazard_speed (float): Movement speed of poison entities.
            hazard_reward (float): Base reward value for colliding with poison (typically negative).
            supply_reward (float): Base reward value for successfully capturing supply.
            encounter_reward (float): Reward value for encountering food without successful capture.
            thrust_penalty (float): Penalty coefficient for agent movement (energy cost).
            local_ratio (float): Ratio of individual reward in final mixed reward calculation.
            speed_features (bool): Whether to include velocity features in observations.
            max_cycles (int): Maximum number of steps per episode.
            render_mode (str, optional): Rendering mode (currently unused).
            env_seed (int): Random seed for environment initialization.
            steering_strength (float): Strength of random steering for food and poison entities.

        Note:
            The environment automatically establishes connection to TongSim server
            using the endpoint specified in DEFAULT_CONFIG.
        """
        super().__init__()

        # --- TongSim Connection & Configuration ---
        self.ue = ts.TongSim(grpc_endpoint=DEFAULT_CONFIG["grpc_endpoint"])
        self.context = self.ue.context
        self.conn = self.context.conn

        # --- Environment Parameters ---
        self.num_arenas = num_arenas
        self.n_rescuers = n_rescuers
        self.n_supplies = n_supplies
        self.n_hazards = n_hazards
        self.n_coop = n_coop
        self.n_sensors = n_sensors
        self.sensor_range = sensor_range
        self.pursuer_max_accel = pursuer_max_accel
        self.supply_speed = supply_speed
        self.hazard_speed = hazard_speed
        self.hazard_reward_num = hazard_reward
        self.supply_reward_num = supply_reward
        self.encounter_reward_num = encounter_reward
        self.thrust_penalty = thrust_penalty
        self.local_ratio = local_ratio
        self.speed_features = speed_features
        self.max_cycles = max_cycles
        self.render_mode = render_mode
        self.steering_strength = steering_strength
        self.env_seed = env_seed
        self.actors_per_arena = self.n_rescuers + self.n_supplies + self.n_hazards

        # --- State Variables ---
        self.agents = [f"pursuer_{i}" for i in range(self.n_rescuers)]
        self.num_agents = self.n_rescuers
        self.agent_ids_map = [{} for _ in range(self.num_arenas)]
        self.arena_ids: list[str] = []
        self.arena_anchors: dict[str, ts.Transform] = {}
        self.arenas_data: list[dict[str, Any]] = []

        # --- Observation Space Definition ---
        # Define feature sizes for each entity type in observation vector
        self.obs_feature_sizes = {
            self.ENTITY_AGENT: 3,  # [distance, orientation_x, orientation_y]
            self.ENTITY_COIN: 2,  # [distance, velocity_projection]
            self.ENTITY_POISON: 2,  # [distance, velocity_projection]
            "wall": 1,  # [distance]
            "obstacle": 1,  # [distance]
        }
        self.obs_feature_order = [self.ENTITY_AGENT, self.ENTITY_COIN, self.ENTITY_POISON, "wall", "obstacle"]

        # Calculate indices for accessing features in the observation vector
        self.obs_indices = {}
        current_index = 0
        for feature_name in self.obs_feature_order:
            self.obs_indices[feature_name] = current_index
            current_index += self.obs_feature_sizes[feature_name]
        self.single_sensor_dim = current_index

        # --- Gymnasium Interface Initialization ---
        self.get_spaces()
        self._seed(self.env_seed)

    def get_spaces(self):
        """
        Define and configure observation and action spaces for the environment.

        Observation Space:
            Box space with dimension [single_sensor_dim * n_sensors + 2]
            - First (single_sensor_dim * n_sensors) dimensions: Ray sensor readings
            - Last 2 dimensions: Collision flags for coin and poison

        Action Space:
            Continuous Box space with dimension [2]
            - [0]: X-axis movement command (range: -1.0 to 1.0)
            - [1]: Y-axis movement command (range: -1.0 to 1.0)
        """
        obs_dim = self.single_sensor_dim * self.n_sensors + 2  # +2 for collision flags
        self.obs_dim = obs_dim

        self.observation_space = {
            agent: spaces.Box(low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32) for agent in self.agents
        }
        self.action_space = {
            agent: spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32) for agent in self.agents
        }

    def _seed(self, seed=None):
        """
        Set the random seed for the environment.

        Args:
            seed (int, optional): Random seed value. If None, a random seed is generated.

        Returns:
            List containing the actual seed value used.
        """
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def render(self):
        """
        Render the environment (currently not implemented).

        This method is provided for Gymnasium API compatibility but does not
        perform any rendering operations. Visualization is handled by Unreal Engine.
        """
        pass

    def _init_arenas_data(self):
        """
        Initialize or reset state containers for all arenas.

        Creates fresh data structures to track:
            - Actor positions (agents, coins, poisons)
            - Actor IDs for each entity type
            - Orientations and velocities
            - Step counter
            - Collision flags

        This method is called during full environment reset to clear all state.
        """
        self.arenas_data = []
        for _i in range(self.num_arenas):
            self.arenas_data.append(
                {
                    "pos": {"coins": {}, "poisons": {}, "agents": {}},
                    "ids_of_coins": [],
                    "ids_of_poisons": [],
                    "ids_of_agents": [],
                    "orientation": {},
                    "velocities": {},
                    "count_step": 0,
                    "hit_coin": {},
                    "hit_poison": {},
                }
            )

    async def _respawn_entity(self, arena_idx: int, entity_id: str, entity_type: str):
        """
        Respawn an entity at a random safe location within the specified arena.

        This method is called when an entity (coin or poison) needs to be relocated,
        typically after being captured or consumed. The entity is moved to a new
        random position that avoids obstacles, and its velocity is randomized.

        Args:
            arena_idx (int): Index of the arena where respawning occurs.
            entity_id (str): Unique identifier of the entity to respawn.
            entity_type (str): Type of entity ('coin' or 'poison').

        Raises:
            ValueError: If entity_type is not recognized.
            RuntimeError: If the entity transform cannot be set in TongSim.

        Note:
            The respawn location is guaranteed to be safe (not inside obstacles)
            through the generate_safe_random_location utility function.
        """
        arena_id = self.arena_ids[arena_idx]
        arena_data = self.arenas_data[arena_idx]
        anchor_loc = self.arena_anchors[arena_id].location

        # Configuration mapping for different entity types
        entity_configs = {
            self.ENTITY_COIN: {
                "scale": DEFAULT_CONFIG["coin_scale"],
                "speed": self.supply_speed,
                "pos_map_key": "coins",
            },
            self.ENTITY_POISON: {
                "scale": DEFAULT_CONFIG["default_scale"],
                "speed": self.hazard_speed,
                "pos_map_key": "poisons",
            },
        }

        if entity_type not in entity_configs:
            raise ValueError(f"Unknown entity type: {entity_type}")

        config = entity_configs[entity_type]

        # Generate safe random location and calculate world coordinates
        rand_x, rand_y = generate_safe_random_location(
            DEFAULT_CONFIG["x_bounds"], DEFAULT_CONFIG["y_bounds"], DEFAULT_CONFIG["block_ranges"]
        )
        world_loc = ts.Vector3(anchor_loc.x + rand_x, anchor_loc.y + rand_y, DEFAULT_CONFIG["spawn_z"])

        # Move entity to new location in TongSim
        set_ok = await ts.UnaryAPI.set_actor_transform(
            self.conn, entity_id, ts.Transform(location=world_loc, scale=config["scale"])
        )
        if not set_ok:
            raise RuntimeError(f"Failed to reset position for entity {entity_id}.")

        # Update internal state: position and velocity
        arena_data["pos"][config["pos_map_key"]][entity_id] = (world_loc.x, world_loc.y, world_loc.z)

        # Randomize movement direction
        random_dir = self.np_random.standard_normal(2)
        random_dir /= np.linalg.norm(random_dir) + 1e-8
        arena_data["velocities"][entity_id] = random_dir * config["speed"]

    def reset(self, *, seed=None, options=None):
        """
        Perform a complete reset of all parallel environments to their initial state.

        This method is typically called only once at the beginning of training.
        It destroys and rebuilds all arenas and actors in Unreal Engine, providing
        a clean slate for a new training session.

        Args:
            seed (int, optional): Random seed for reproducibility.
            options (dict, optional): Additional reset options (currently unused).

        Returns:
            Tuple[List[Dict[str, np.ndarray]], List[Dict]]:
                - Initial observations for all environments (one dict per arena).
                - Initial info dictionaries for all environments.

        Note:
            This is a heavyweight operation that involves:
            1. Resetting the UE level
            2. Loading new arenas
            3. Spawning all actors
            4. Initializing states
            5. Computing initial observations

            For episode-level resets during training, use reset_one_env() instead.
        """
        super().reset(seed=seed)
        print("\n================== [ENV FULL RESET] ==================")

        print("[1] Clearing and rebuilding internal state containers...")
        self._init_arenas_data()

        print("[2] Running async full reset logic for all arenas...")
        initial_observations = self.context.sync_run(self._async_full_reset())

        print("================== [FULL RESET DONE] ==================\n")
        infos = [{} for _ in range(self.num_arenas)]
        return initial_observations, infos

    async def _async_full_reset(self):
        """
        Execute the complete asynchronous reset logic for all environments.

        This method orchestrates the full reset process:
        1. Reset UE level and destroy all existing arenas
        2. Load new arenas concurrently
        3. Spawn all actors (agents, coins, poisons) in parallel
        4. Initialize actor states (positions, velocities, orientations)
        5. Generate initial observations

        Returns:
            List[Dict[str, np.ndarray]]: Initial observations for all arenas.

        Note:
            This method uses asyncio.gather extensively for maximum parallelism
            and minimal reset time.
        """
        print("  - [Async] Starting full async reset for all arenas...")

        # Step 1: Reset UE level and destroy all old arenas
        print("  - [Async] 1. Resetting UE main level...")
        await ts.UnaryAPI.reset_level(self.conn)
        self.arena_ids = []
        self.arena_anchors = {}

        # Step 2: Concurrently load multiple new arenas
        print(f"  - [Async] 2. Loading {self.num_arenas} new arenas concurrently...")
        load_tasks = []

        for i in range(self.num_arenas):
            anchor = get_grid_anchor(arena_index=i, num_arenas=self.num_arenas, spacing=DEFAULT_CONFIG["arena_spacing"])
            load_tasks.append(
                ts.UnaryAPI.load_arena(
                    self.conn, level_asset_path=DEFAULT_CONFIG["level_asset_path"], anchor=anchor, make_visible=True
                )
            )
        loaded_arena_ids = await asyncio.gather(*load_tasks)

        # Store successfully loaded arenas
        for i, aid in enumerate(loaded_arena_ids):
            if aid:
                self.arena_ids.append(aid)
                self.arena_anchors[aid] = get_grid_anchor(
                    arena_index=i, num_arenas=self.num_arenas, spacing=DEFAULT_CONFIG["arena_spacing"]
                )

        if len(self.arena_ids) != self.num_arenas:
            print(f"[WARNING] Expected {self.num_arenas} arenas, successfully loaded {len(self.arena_ids)}.")
        print(f"  - [Async] Successfully loaded arenas: {self.arena_ids}")

        # Step 3: Spawn all actor types for each arena concurrently
        print("  - [Async] 3. Spawning actors for all arenas concurrently...")
        all_spawn_tasks = []
        for arena_id in self.arena_ids:
            # Spawn coins
            all_spawn_tasks.append(
                spawn_actors_concurrently(
                    self.context,
                    arena_id,
                    self.n_supplies,
                    DEFAULT_CONFIG["coin_bp_path"],
                    self.TAG_COIN,
                    DEFAULT_CONFIG["spawn_z"],
                )
            )
            # Spawn poisons
            all_spawn_tasks.append(
                spawn_actors_concurrently(
                    self.context,
                    arena_id,
                    self.n_hazards,
                    DEFAULT_CONFIG["poison_bp_path"],
                    self.TAG_POISON,
                    DEFAULT_CONFIG["spawn_z"],
                )
            )
            # Spawn agents
            all_spawn_tasks.append(
                spawn_actors_concurrently(
                    self.context,
                    arena_id,
                    self.n_rescuers,
                    DEFAULT_CONFIG["agent_bp_path"],
                    self.TAG_AGENT,
                    DEFAULT_CONFIG["spawn_z"],
                )
            )
        all_spawn_results = await asyncio.gather(*all_spawn_tasks)

        # Step 4: Initialize state for all arenas
        print("  - [Async] 4. Initializing state for all arenas...")
        for i, arena_id in enumerate(self.arena_ids):
            arena_data = self.arenas_data[i]
            # Extract spawn results for this arena (3 tasks per arena: coins, poisons, agents)
            coin_results = all_spawn_results[i * 3]
            poison_results = all_spawn_results[i * 3 + 1]
            agent_results = all_spawn_results[i * 3 + 2]

            # Store actor IDs
            arena_data["ids_of_coins"] = [r["id"] for r in coin_results]
            arena_data["ids_of_poisons"] = [r["id"] for r in poison_results]
            arena_data["ids_of_agents"] = [r["id"] for r in agent_results]

            # Create agent name to ID mapping
            self.agent_ids_map[i] = {self.agents[j]: agent_id for j, agent_id in enumerate(arena_data["ids_of_agents"])}

            # Initialize actor positions and velocities
            await self._async_initialize_arena_actors(i, arena_id)

        # Step 5: Build and return initial observations for all arenas
        print("  - [Async] 5. Building initial observations for all arenas...")
        jobs, rays_directions_map = self.build_observation_rays()
        if not jobs:
            return [{} for _ in self.arena_ids]

        ray_results = await ts.UnaryAPI.multi_line_trace_by_object(self.conn, jobs=jobs, enable_debug_draw=True)
        observations = self.process_ray_results(ray_results, rays_directions_map)

        print("  - [Async] Full async reset completed for all arenas.")
        return observations

    async def _async_initialize_arena_actors(self, arena_idx: int, arena_id: str):
        """
        Initialize all actors in a single arena with random positions and velocities.

        This method performs three main tasks:
        1. Set random safe positions for all actors with appropriate scaling
        2. Retrieve final positions from TongSim
        3. Initialize velocities and orientations based on actor type

        Args:
            arena_idx (int): Index of the arena to initialize.
            arena_id (str): Unique identifier of the arena.

        Note:
            Agents receive zero initial velocity and default forward orientation.
            Coins and poisons receive random movement directions at specified speeds.
        """
        arena_data = self.arenas_data[arena_idx]
        anchor_loc = self.arena_anchors[arena_id].location

        all_actor_ids = arena_data["ids_of_agents"] + arena_data["ids_of_coins"] + arena_data["ids_of_poisons"]

        # Step 1: Concurrently set random positions with proper scaling for all actors
        move_tasks = []
        for actor_id in all_actor_ids:
            # Generate safe random location
            rand_x, rand_y = generate_safe_random_location(
                DEFAULT_CONFIG["x_bounds"], DEFAULT_CONFIG["y_bounds"], DEFAULT_CONFIG["block_ranges"]
            )
            target_location = ts.Vector3(anchor_loc.x + rand_x, anchor_loc.y + rand_y, DEFAULT_CONFIG["spawn_z"])
            # Apply appropriate scale based on actor type
            scale = (
                DEFAULT_CONFIG["coin_scale"]
                if actor_id in arena_data["ids_of_coins"]
                else DEFAULT_CONFIG["default_scale"]
            )
            move_tasks.append(
                ts.UnaryAPI.set_actor_transform(
                    self.conn, actor_id, ts.Transform(location=target_location, scale=scale)
                )
            )
        await asyncio.gather(*move_tasks, return_exceptions=True)

        # Step 2: Retrieve final positions for all actors
        id_to_transform = await get_actor_transform_safe(self.conn, all_actor_ids)

        # Step 3: Update arena data structures with positions, velocities, and orientations
        for entity_type in [self.ENTITY_COIN, self.ENTITY_POISON, self.ENTITY_AGENT]:
            pos_map_key = f"{entity_type}s"
            id_list_key = f"ids_of_{entity_type}s"
            arena_data["pos"][pos_map_key] = {}

            for actor_id in arena_data[id_list_key]:
                if actor_id in id_to_transform:
                    pos = id_to_transform[actor_id]
                    loc_tuple = (pos.location.x, pos.location.y, pos.location.z)
                    arena_data["pos"][pos_map_key][actor_id] = loc_tuple

                    # Initialize velocity for moving entities (coins and poisons)
                    if entity_type in [self.ENTITY_COIN, self.ENTITY_POISON]:
                        speed = self.supply_speed if entity_type == self.ENTITY_COIN else self.hazard_speed
                        # Generate random movement direction
                        random_dir = self.np_random.standard_normal(2)
                        random_dir /= np.linalg.norm(random_dir) + 1e-8
                        arena_data["velocities"][actor_id] = random_dir * speed
                    # Initialize orientation for agents
                    elif entity_type == self.ENTITY_AGENT:
                        arena_data["orientation"][actor_id] = np.array([1.0, 0.0, 0.0])

    def reset_one_env(self, arena_idx: int):
        """
        Synchronous interface for resetting a single environment that has finished an episode.

        This method is designed for use during training loops when individual arenas
        complete their episodes at different times. Unlike the full reset, this method
        only repositions existing actors without destroying or recreating them,
        making it much more efficient.

        Args:
            arena_idx (int): Index of the arena to reset.

        Returns:
            Tuple[Dict[str, np.ndarray], Dict]:
                - Initial observation for the reset environment.
                - Initial info dictionary (currently empty).

        Note:
            This method internally calls the async reset logic but provides
            a synchronous interface for compatibility with typical training loops.
        """
        new_observation = self.context.sync_run(self._async_reset_arena(arena_idx))
        return new_observation, {}

    async def _async_reset_arena(self, arena_idx: int):
        """
        Asynchronously reset a specific arena by repositioning actors.

        This lightweight reset method:
        1. Clears the arena's step-level state
        2. Reinitializes all actor positions and velocities
        3. Generates fresh observations

        Args:
            arena_idx (int): Index of the arena to reset.

        Returns:
            Dict[str, np.ndarray]: Initial observations for all agents in the arena.

        Note:
            This method is significantly faster than full reset as it reuses
            existing actors rather than spawning new ones.
        """
        arena_id = self.arena_ids[arena_idx]
        arena_data = self.arenas_data[arena_idx]
        print(f"  - [Async] Starting independent reset for Arena {arena_idx} (ID: {arena_id})...")

        # Step 1: Clear step-level state for this arena
        arena_data["count_step"] = 0
        arena_data["velocities"] = {}
        arena_data["orientation"] = {}
        arena_data["hit_coin"] = {}
        arena_data["hit_poison"] = {}

        # Step 2: Reinitialize positions and velocities for all actors
        await self._async_initialize_arena_actors(arena_idx, arena_id)

        # Step 3: Generate fresh observations for this arena
        jobs, rays_directions_map = self.build_observation_rays_for_single_arena(arena_idx)
        ray_results = await ts.UnaryAPI.multi_line_trace_by_object(self.conn, jobs=jobs, enable_debug_draw=True)
        arena_obs = self.process_ray_results_for_single_arena(ray_results, rays_directions_map, arena_idx)
        return arena_obs

    def _build_rays_for_arena(self, arena_idx: int):
        """
        Build ray-casting jobs for all agents in a single arena.

        This method generates ray-tracing tasks for perception, creating circular
        ray patterns around each agent's facing direction. Each ray can detect
        other agents, coins, poisons, walls, and obstacles.

        Args:
            arena_idx (int): Index of the arena to build rays for.

        Returns:
            Tuple[List[Dict], List[np.ndarray]]:
                - List of ray-tracing job dictionaries for TongSim API.
                - List of ray direction vectors corresponding to each job.

        Raises:
            ValueError: If an agent has no position data.

        Note:
            Rays are configured to ignore the casting agent itself to prevent
            self-collision detection.
        """
        arena_data = self.arenas_data[arena_idx]
        jobs = []
        rays_for_arena = []

        for agent_id in arena_data["ids_of_agents"]:
            # Get agent's current facing direction
            face_vector = arena_data["orientation"].get(agent_id, np.array([1.0, 0.0, 0.0]))
            start_point = arena_data["pos"]["agents"].get(agent_id)

            if not start_point:
                raise ValueError(f"Agent ID {agent_id} in Arena {arena_idx} has no position data.")

            # Generate circular ray pattern around facing direction
            generated_rays = generate_circular_rays(face_vector, self.n_sensors, radius=self.sensor_range)
            rays_for_arena.extend(generated_rays)

            # Create ray-tracing job for each ray
            for ray in generated_rays:
                jobs.append(
                    {
                        "start": ts.Vector3(*start_point),
                        "end": ts.Vector3(*(np.array(start_point) + ray)),
                        "object_types": [
                            CollisionObjectType.OBJECT_WORLD_STATIC,  # Walls
                            CollisionObjectType.OBJECT_WORLD_DYNAMIC,  # Movable objects
                            CollisionObjectType.OBJECT_PAWN,  # Agents and entities
                        ],
                        "actors_to_ignore": [agent_id],  # Prevent self-detection
                    }
                )

        return jobs, rays_for_arena

    def build_observation_rays_for_single_arena(self, arena_idx: int):
        """
        Build observation rays for a single arena only.

        Convenience wrapper around _build_rays_for_arena for single-arena operations.

        Args:
            arena_idx (int): Index of the arena to build rays for.

        Returns:
            Tuple[List[Dict], List[np.ndarray]]: Ray jobs and direction vectors.
        """
        return self._build_rays_for_arena(arena_idx)

    def build_observation_rays(self):
        """
        Build observation rays for all arenas and all agents.

        This method constructs ray-tracing jobs for every agent across all parallel
        arenas, along with metadata to properly route the results back to the correct
        arena and agent.

        Returns:
            Tuple[List[Dict], Dict]:
                - List of all ray-tracing jobs for TongSim API.
                - Dictionary containing:
                    - 'rays': All ray direction vectors
                    - 'offsets': Mapping from arena_idx to starting index in results

        Note:
            The offset mapping is crucial for correctly parsing batch ray-tracing
            results and assigning them to the appropriate arena.
        """
        all_jobs = []
        all_generated_rays = []
        rays_directions_map = {"rays": [], "offsets": {}}

        for arena_idx, _arena_id in enumerate(self.arena_ids):
            # Record where this arena's results start in the combined list
            rays_directions_map["offsets"][arena_idx] = len(all_jobs)

            # Build and append rays for this arena
            arena_jobs, arena_rays = self._build_rays_for_arena(arena_idx)
            all_jobs.extend(arena_jobs)
            all_generated_rays.extend(arena_rays)

        rays_directions_map["rays"] = all_generated_rays
        return all_jobs, rays_directions_map

    def _process_rays_for_one_arena(
        self, arena_idx: int, all_ray_results: list[dict], all_ray_directions: list, result_offset: int
    ) -> np.ndarray:
        """
        Process ray-tracing results for a single arena and construct observation arrays.

        This method converts raw ray-hit data into structured observation vectors
        for each agent in the arena. For each sensor ray, it identifies the closest
        hit object of each type and encodes relevant features (distance, velocity, etc.).

        Args:
            arena_idx (int): Index of the arena being processed.
            all_ray_results (List[dict]): Complete list of ray-tracing results from TongSim.
            all_ray_directions (List): Complete list of ray direction vectors.
            result_offset (int): Starting index of this arena's results in the complete list.

        Returns:
            np.ndarray: Observation array of shape (n_rescuers, obs_dim).

        Raises:
            IndexError: If ray index calculation exceeds the bounds of ray_results.

        Note:
            The observation vector structure:
            - For each of n_sensors rays:
                - Agent features (3): [distance, orientation_x, orientation_y]
                - Coin features (2): [distance, velocity_projection]
                - Poison features (2): [distance, velocity_projection]
                - Wall features (1): [distance]
                - Obstacle features (1): [distance]
            - Collision flags (2): [hit_coin, hit_poison]

            Only the closest hit of each type per ray is recorded (nearest-neighbor principle).
        """
        arena_data = self.arenas_data[arena_idx]
        # Initialize observation array with -1 (indicates no detection)
        arena_obs = np.full((self.n_rescuers, self.obs_dim), -1.0, dtype=np.float32)

        for agent_local_idx in range(self.n_rescuers):
            for sensor_idx in range(self.n_sensors):
                # Calculate global index in the combined ray results
                ray_global_idx = result_offset + agent_local_idx * self.n_sensors + sensor_idx
                if ray_global_idx >= len(all_ray_results):
                    raise IndexError("Ray index out of bounds for the provided ray results.")

                ray_result = all_ray_results[ray_global_idx]
                # Track which entity types have been recorded for this ray (closest only)
                closest_flags = dict.fromkeys(self.obs_feature_order, False)

                if len(ray_result["hits"]) > 0:
                    for hit in ray_result["hits"]:
                        # Normalize distance to [0, 1] range
                        hit_distance = max(0.0, min(1.0, hit["distance"] / (self.sensor_range + 1e-8)))
                        actor_state = hit["actor_state"]
                        actor_id = actor_state["id"]
                        tag = actor_state["tag"]

                        # Calculate base column for this sensor's features
                        base_col = sensor_idx * self.single_sensor_dim

                        # Encode features based on hit entity type (only if not already recorded)
                        if tag == self.TAG_AGENT and not closest_flags[self.ENTITY_AGENT]:
                            start_col = base_col + self.obs_indices[self.ENTITY_AGENT]
                            orientation = arena_data["orientation"].get(actor_id, [0, 0])
                            arena_obs[agent_local_idx, start_col : start_col + 3] = [
                                hit_distance,
                                orientation[0],
                                orientation[1],
                            ]
                            closest_flags[self.ENTITY_AGENT] = True

                        elif tag == self.TAG_COIN and not closest_flags[self.ENTITY_COIN]:
                            # Calculate velocity projection along ray direction
                            velocity = arena_data["velocities"].get(actor_id, np.zeros(2))
                            ray_direction = np.array(all_ray_directions[ray_global_idx])[:2]
                            velocity_projection = np.dot(velocity, ray_direction) / (
                                np.linalg.norm(ray_direction) + 1e-8
                            )
                            start_col = base_col + self.obs_indices[self.ENTITY_COIN]
                            arena_obs[agent_local_idx, start_col : start_col + 2] = [hit_distance, velocity_projection]
                            closest_flags[self.ENTITY_COIN] = True

                        elif tag == self.TAG_POISON and not closest_flags[self.ENTITY_POISON]:
                            # Calculate velocity projection along ray direction
                            velocity = arena_data["velocities"].get(actor_id, np.zeros(2))
                            ray_direction = np.array(all_ray_directions[ray_global_idx])[:2]
                            velocity_projection = np.dot(velocity, ray_direction) / (
                                np.linalg.norm(ray_direction) + 1e-8
                            )
                            start_col = base_col + self.obs_indices[self.ENTITY_POISON]
                            arena_obs[agent_local_idx, start_col : start_col + 2] = [hit_distance, velocity_projection]
                            closest_flags[self.ENTITY_POISON] = True

                        elif tag == self.TAG_WALL and not closest_flags["wall"]:
                            start_col = base_col + self.obs_indices["wall"]
                            arena_obs[agent_local_idx, start_col] = hit_distance
                            closest_flags["wall"] = True

                        elif tag == self.TAG_BLOCK and not closest_flags["obstacle"]:
                            start_col = base_col + self.obs_indices["obstacle"]
                            arena_obs[agent_local_idx, start_col] = hit_distance
                            closest_flags["obstacle"] = True

        # Append collision flags at the end of observation vector
        if arena_data.get("hit_coin"):
            for agent_idx in arena_data["hit_coin"]:
                arena_obs[agent_idx, -2] = 1.0  # Coin collision flag
        if arena_data.get("hit_poison"):
            for agent_idx in arena_data["hit_poison"]:
                arena_obs[agent_idx, -1] = 1.0  # Poison collision flag

        return arena_obs

    def process_ray_results_for_single_arena(self, ray_results: list[dict], rays_directions: list, arena_idx: int):
        """
        Process ray results for a single arena and convert to dictionary format.

        Args:
            ray_results (List[dict]): Ray-tracing results from TongSim.
            rays_directions (List): Ray direction vectors.
            arena_idx (int): Index of the arena being processed.

        Returns:
            Dict[str, np.ndarray]: Observations keyed by agent names.
        """
        arena_obs_np = self._process_rays_for_one_arena(
            arena_idx=arena_idx, all_ray_results=ray_results, all_ray_directions=rays_directions, result_offset=0
        )
        return {self.agents[i]: arena_obs_np[i] for i in range(self.n_rescuers)}

    def process_ray_results(self, ray_results: list[dict], rays_directions_map: dict):
        """
        Process ray results for all arenas and return observations for all environments.

        This method takes batched ray-tracing results from TongSim and distributes
        them to the appropriate arenas for processing. Each arena's observations
        are constructed independently.

        Args:
            ray_results (List[dict]): Complete list of ray-tracing results for all arenas.
            rays_directions_map (Dict): Mapping containing ray directions and arena offsets.

        Returns:
            List[Dict[str, np.ndarray]]: List of observation dictionaries (one per arena).

        Note:
            The rays_directions_map['offsets'] dictionary is used to correctly partition
            the batched results back to individual arenas.
        """
        observations_all_arenas = [{} for _ in range(self.num_arenas)]
        all_ray_directions = rays_directions_map["rays"]

        for arena_idx, _arena_id in enumerate(self.arena_ids):
            result_offset = rays_directions_map["offsets"][arena_idx]
            arena_obs_np = self._process_rays_for_one_arena(
                arena_idx=arena_idx,
                all_ray_results=ray_results,
                all_ray_directions=all_ray_directions,
                result_offset=result_offset,
            )
            observations_all_arenas[arena_idx] = {self.agents[i]: arena_obs_np[i] for i in range(self.n_rescuers)}

        return observations_all_arenas

    def step(self, actions: list[dict[str, np.ndarray]]):
        """
        Execute one step in all parallel environments.

        This is the main simulation loop method that:
        1. Executes agent actions and entity movements
        2. Detects collisions
        3. Calculates rewards
        4. Updates observations
        5. Checks termination conditions

        Args:
            actions (List[Dict[str, np.ndarray]]): Actions for all agents in all arenas.
                Expected structure: [
                    {agent_0: action_array, agent_1: action_array, ...},  # Arena 0
                    {agent_0: action_array, agent_1: action_array, ...},  # Arena 1
                    ...
                ]

        Returns:
            Tuple containing:
                - observations (List[Dict]): New observations for all arenas
                - rewards (List[Dict]): Rewards for all agents in all arenas
                - terminateds (List[Dict]): Termination flags (currently always False)
                - truncateds (List[Dict]): Truncation flags (True when max_cycles reached)
                - infos (List[Dict]): Additional information including agent masks

        Note:
            All parallel environments are stepped simultaneously using async operations
            for maximum throughput.
        """
        # Increment step counter for all arenas
        for arena_data in self.arenas_data:
            arena_data["count_step"] += 1

        # Execute async step logic and return results
        obs, rewards, terminated, truncated, infos = self.context.sync_run(self._async_step(actions))
        return obs, rewards, terminated, truncated, infos

    async def _async_step(self, all_actions: list[dict[str, np.ndarray]]):
        """
        Execute the core asynchronous step logic for all parallel environments.

        This method orchestrates the complete simulation step through five phases:
        1. Create movement tasks for all actors (agents, coins, poisons)
        2. Execute all movements concurrently
        3. Process movement results and detect collisions
        4. Calculate rewards and determine entities to respawn
        5. Execute respawns, compute final rewards, and generate observations

        Args:
            all_actions (List[Dict[str, np.ndarray]]): Actions for all agents in all arenas.

        Returns:
            Tuple: (observations, rewards, terminateds, truncateds, infos)

        Note:
            The async design allows all arenas to simulate in parallel, with collision
            resolution handled in a deterministic order based on movement completion times.
        """
        # Phase 1: Create all movement tasks and calculate movement penalties
        all_move_tasks, per_arena_rewards = self._create_move_tasks(all_actions)

        # Phase 2: Execute all movements concurrently
        all_results_with_timing = await asyncio.gather(*all_move_tasks, return_exceptions=True)

        # Phase 3: Process movement results and handle collisions
        coin_settlement_maps, poison_settlement_maps = self._process_move_results(all_results_with_timing)

        # Phase 4: Calculate rewards and generate respawn tasks
        respawn_tasks = self._calculate_rewards_and_respawns(
            coin_settlement_maps, poison_settlement_maps, per_arena_rewards
        )

        # Phase 5: Execute respawns concurrently
        if respawn_tasks:
            await asyncio.gather(*respawn_tasks, return_exceptions=True)

        # Phase 6: Finalize step with reward calculation, observations, and termination checks
        return await self._finalize_step(per_arena_rewards)

    def _create_move_tasks(self, all_actions: list[dict[str, np.ndarray]]):
        """
        Create movement tasks for all actors in all arenas and calculate movement penalties.

        This method generates async movement tasks for:
        - Agents (controlled by policy actions)
        - Coins (autonomous movement with random steering)
        - Poisons (autonomous movement with random steering)

        Args:
            all_actions (List[Dict[str, np.ndarray]]): Actions for all agents in all arenas.

        Returns:
            Tuple[List, List[Dict]]:
                - List of async movement tasks for all actors
                - List of reward dictionaries (one per arena) with:
                    - 'control': Movement penalties for each agent
                    - 'food': Initialized to zero (calculated later)
                    - 'poison': Initialized to zero (calculated later)

        Note:
            Agent orientations are updated based on action direction.
            Coin and poison velocities are updated with random steering for realistic movement.
        """
        all_move_tasks = []
        per_arena_rewards = []

        for arena_idx, _arena_id in enumerate(self.arena_ids):
            arena_data = self.arenas_data[arena_idx]
            actions = all_actions[arena_idx]

            # Initialize current step state
            arena_data["hit_coin"] = {}
            arena_data["hit_poison"] = {}
            rewards_this_arena = {
                "control": np.zeros(self.n_rescuers),
                "food": np.zeros(self.n_rescuers),
                "poison": np.zeros(self.n_rescuers),
            }

            # Create movement tasks for agents
            for i, agent_name in enumerate(self.agents):
                agent_id = self.agent_ids_map[arena_idx][agent_name]
                action_array = np.clip(np.array(actions[agent_name]), -1, 1)

                # Calculate movement penalty (energy cost)
                rewards_this_arena["control"][i] = self.thrust_penalty * np.linalg.norm(action_array)

                # Calculate target location based on action
                current_pos = arena_data["pos"]["agents"].get(agent_id, (0, 0, 0))
                target_loc = ts.Vector3(
                    current_pos[0] + action_array[0] * DEFAULT_CONFIG["action_multiplier"],
                    current_pos[1] + action_array[1] * DEFAULT_CONFIG["action_multiplier"],
                    current_pos[2],
                )

                # Update agent orientation based on movement direction
                norm = np.linalg.norm(action_array) + 1e-8
                arena_data["orientation"][agent_id] = np.array([action_array[0] / norm, action_array[1] / norm, 0.0])

                # Create movement task
                coro = ts.UnaryAPI.simple_move_towards(
                    self.conn,
                    actor_id=agent_id,
                    target_location=target_loc,
                    timeout=60.0,
                    orientation_mode=RLDemoOrientationMode.ORIENTATION_FACE_MOVEMENT,
                    speed_uu_per_sec=12000.0,
                )
                all_move_tasks.append(run_and_time_task(coro, agent_id))

            # Create movement tasks for coins and poisons
            for entity_type in [self.ENTITY_COIN, self.ENTITY_POISON]:
                speed = self.supply_speed if entity_type == self.ENTITY_COIN else self.hazard_speed
                id_list_key = f"ids_of_{entity_type}s"
                pos_map_key = f"{entity_type}s"

                for actor_id in arena_data[id_list_key]:
                    current_pos = arena_data["pos"][pos_map_key].get(actor_id, (0, 0, 0))
                    current_velocity = arena_data["velocities"].get(actor_id, np.zeros(2))

                    # Apply random steering for natural movement
                    steering = self.np_random.standard_normal(2)
                    new_velocity = current_velocity + steering * self.steering_strength
                    new_velocity /= np.linalg.norm(new_velocity) + 1e-8
                    final_velocity = new_velocity * speed
                    arena_data["velocities"][actor_id] = final_velocity

                    # Calculate target location
                    target_loc = ts.Vector3(
                        current_pos[0] + final_velocity[0] * DEFAULT_CONFIG["action_multiplier"],
                        current_pos[1] + final_velocity[1] * DEFAULT_CONFIG["action_multiplier"],
                        current_pos[2],
                    )

                    # Create movement task
                    coro = ts.UnaryAPI.simple_move_towards(
                        self.conn,
                        actor_id=actor_id,
                        target_location=target_loc,
                        timeout=6.0,
                        speed_uu_per_sec=12000.0,
                    )
                    all_move_tasks.append(run_and_time_task(coro, actor_id))

            per_arena_rewards.append(rewards_this_arena)

        return all_move_tasks, per_arena_rewards

    def _process_move_results(self, all_results_with_timing: list[dict]):
        """
        Process movement results, update positions, and handle collision events.

        This method processes the results of all concurrent movement operations:
        1. Groups results by arena
        2. Sorts by completion time for deterministic collision handling
        3. Updates actor positions
        4. Detects and records collisions

        Args:
            all_results_with_timing (List[Dict]): Results from all movement tasks,
                each containing: agent_id, result, status, end_time, duration

        Returns:
            Tuple[List[Dict], List[Dict]]:
                - coin_settlement_maps: List of dicts mapping coin_id -> [agent_ids]
                - poison_settlement_maps: List of dicts mapping poison_id -> [agent_ids]

        Raises:
            ValueError: If the number of results doesn't match expected actor count.

        Note:
            Sorting by completion time ensures collision handling is deterministic,
            which is crucial for fair multi-agent learning and reproducibility.
        """
        coin_settlement_maps = [defaultdict(list) for _ in range(self.num_arenas)]
        poison_settlement_maps = [defaultdict(list) for _ in range(self.num_arenas)]

        # Group results by arena and sort by completion time
        sorted_groups = []
        for i in range(self.num_arenas):
            group = all_results_with_timing[i * self.actors_per_arena : (i + 1) * self.actors_per_arena]
            sorted_group = sorted(group, key=lambda r: r["end_time"])
            if len(sorted_group) != self.actors_per_arena:
                raise ValueError(
                    f"Arena {i} result count mismatch: expected {self.actors_per_arena}, got {len(sorted_group)}"
                )
            sorted_groups.append(sorted_group)

        # Process each arena's results in order of completion
        for arena_idx, sorted_group in enumerate(sorted_groups):
            for res in sorted_group:
                if not isinstance(res, dict) or "result" not in res:
                    continue

                cur_loc, hit = res["result"]
                actor_id = res["agent_id"]

                # Update actor position
                self._update_actor_position(arena_idx, actor_id, cur_loc)

                # Handle collision if occurred
                if hit:
                    self._handle_collision(arena_idx, actor_id, hit, coin_settlement_maps, poison_settlement_maps)

        return coin_settlement_maps, poison_settlement_maps

    def _update_actor_position(self, arena_idx: int, actor_id: str, location: ts.Vector3):
        """
        Update an actor's position in the internal state tracking system.

        Args:
            arena_idx (int): Index of the arena containing the actor.
            actor_id (str): Unique identifier of the actor.
            location (ts.Vector3): New location of the actor.

        Note:
            The actor is automatically categorized as agent, coin, or poison
            based on its ID presence in the respective tracking lists.
        """
        arena_data = self.arenas_data[arena_idx]
        loc_tuple = (location.x, location.y, location.z)

        if actor_id in arena_data["ids_of_agents"]:
            arena_data["pos"]["agents"][actor_id] = loc_tuple
        elif actor_id in arena_data["ids_of_coins"]:
            arena_data["pos"]["coins"][actor_id] = loc_tuple
        elif actor_id in arena_data["ids_of_poisons"]:
            arena_data["pos"]["poisons"][actor_id] = loc_tuple

    def _handle_collision(
        self,
        arena_idx: int,
        moving_actor_id: str,
        hit_info: dict,
        coin_settlement_maps: list,
        poison_settlement_maps: list,
    ):
        """
        Handle a single collision event between two actors.

        This method processes collision logic based on the types of actors involved:

        Case 1 - Agent hits Coin/Poison:
            - Records collision for reward calculation
            - Deduplicates multiple collisions with same entity

        Case 2 - Coin hits Agent:
            - Records collision (reciprocal to Case 1)
            - Deduplicates multiple collisions with same agent

        Case 3 - Coin hits Wall/Obstacle:
            - Calculates bounce velocity

        Case 4 - Poison hits Agent:
            - Records collision
            - Deduplicates multiple collisions with same agent

        Case 5 - Poison hits Wall/Obstacle:
            - Calculates bounce velocity

        Args:
            arena_idx (int): Index of the arena where collision occurred.
            moving_actor_id (str): ID of the actor that was moving.
            hit_info (Dict): Collision information from TongSim containing:
                - hit_actor: Information about the hit actor
                - Other collision details
            coin_settlement_maps (List): Collision tracking for coins.
            poison_settlement_maps (List): Collision tracking for poisons.

        Note:
            The deduplication checks prevent the same collision from being counted
            multiple times if both actors are moving toward each other.

            Bounce velocity calculations simulate realistic physics for coins and
            poisons bouncing off walls and obstacles.
        """
        arena_data = self.arenas_data[arena_idx]
        hit_actor_id = convert_bytes_le_to_guid_string(hit_info["hit_actor"].object_info.id.guid)
        hit_actor_tag = hit_info["hit_actor"].tag

        # Case 1: Moving actor is an agent
        if moving_actor_id in arena_data["ids_of_agents"]:
            if hit_actor_tag == self.TAG_COIN:
                # Record collision with coin (with deduplication)
                if (
                    len(coin_settlement_maps[arena_idx][hit_actor_id]) < self.n_coop
                    and moving_actor_id not in coin_settlement_maps[arena_idx][hit_actor_id]
                ):
                    coin_settlement_maps[arena_idx][hit_actor_id].append(moving_actor_id)
            elif hit_actor_tag == self.TAG_POISON:
                # Record collision with poison (with deduplication)
                if (
                    len(poison_settlement_maps[arena_idx][hit_actor_id]) < 1
                    and moving_actor_id not in poison_settlement_maps[arena_idx][hit_actor_id]
                ):
                    poison_settlement_maps[arena_idx][hit_actor_id].append(moving_actor_id)

        # Case 2: Moving actor is a coin
        elif moving_actor_id in arena_data["ids_of_coins"]:
            if hit_actor_tag == self.TAG_AGENT:
                # Record collision with agent (with deduplication)
                if (
                    len(coin_settlement_maps[arena_idx][moving_actor_id]) < self.n_coop
                    and hit_actor_id not in coin_settlement_maps[arena_idx][moving_actor_id]
                ):
                    coin_settlement_maps[arena_idx][moving_actor_id].append(hit_actor_id)
            else:
                # Coin hit wall or obstacle - calculate bounce
                old_vel = arena_data["velocities"].get(moving_actor_id, np.zeros(2))
                new_vel = calculate_bounce_velocity_sample(old_vel, hit_info["hit_actor"].unit_forward_vector)
                arena_data["velocities"][moving_actor_id] = new_vel

        # Case 3: Moving actor is a poison
        elif moving_actor_id in arena_data["ids_of_poisons"]:
            if hit_actor_tag == self.TAG_AGENT:
                # Record collision with agent (with deduplication)
                if (
                    len(poison_settlement_maps[arena_idx][moving_actor_id]) < 1
                    and hit_actor_id not in poison_settlement_maps[arena_idx][moving_actor_id]
                ):
                    poison_settlement_maps[arena_idx][moving_actor_id].append(hit_actor_id)
            else:
                # Poison hit wall or obstacle - calculate bounce
                old_vel = arena_data["velocities"].get(moving_actor_id, np.zeros(2))
                new_vel = calculate_bounce_velocity_sample(old_vel, hit_info["hit_actor"].unit_forward_vector)
                arena_data["velocities"][moving_actor_id] = new_vel

    def _calculate_rewards_and_respawns(self, coin_settlement_maps, poison_settlement_maps, per_arena_rewards):
        """
        Calculate rewards based on collision settlements and generate respawn tasks.

        This method processes all collision events to:
        1. Assign food and poison rewards to agents
        2. Update collision flags for observations
        3. Simulate bounce effects for coins and poisons
        4. Create respawn tasks for captured/consumed entities

        Reward Logic:
            - Coins:
                - All colliding agents receive encounter_reward
                - If n_coop agents collide, they additionally receive supply_reward
                - Coin bounces regardless of capture status (simulating struggle)
                - Captured coins are respawned
            - Poisons:
                - Colliding agent receives hazard_reward (typically negative)
                - Poison is always respawned after collision

        Args:
            coin_settlement_maps (List[Dict]): Coin collision records per arena.
            poison_settlement_maps (List[Dict]): Poison collision records per arena.
            per_arena_rewards (List[Dict]): Reward accumulators for all arenas.

        Returns:
            List: Async respawn tasks for captured coins and consumed poisons.

        Note:
            The coin bounce mechanic creates interesting emergent behavior where
            coins can escape even when being pursued by multiple agents.
        """
        respawn_tasks = []

        # Process coin rewards and respawns
        for arena_idx, settlement in enumerate(coin_settlement_maps):
            arena_data = self.arenas_data[arena_idx]
            for coin_id, agent_list in settlement.items():
                # Check if cooperative capture threshold is met
                is_captured = len(agent_list) >= self.n_coop

                # Assign rewards to all colliding agents
                for agent_id in agent_list:
                    if agent_id not in arena_data["ids_of_agents"]:
                        continue
                    agent_idx = arena_data["ids_of_agents"].index(agent_id)

                    # Encounter reward for collision
                    per_arena_rewards[arena_idx]["food"][agent_idx] += self.encounter_reward_num
                    arena_data["hit_coin"][agent_idx] = 1

                    # Additional capture reward if threshold met
                    if is_captured:
                        per_arena_rewards[arena_idx]["food"][agent_idx] += self.supply_reward_num

                # Simulate coin bounce/struggle regardless of capture
                old_vel = arena_data["velocities"].get(coin_id, np.zeros(2))
                new_vel = calculate_bounce_velocity_sample(old_vel, ts.Vector3(1, 1, 0))
                arena_data["velocities"][coin_id] = new_vel

                # Respawn if captured
                if is_captured:
                    respawn_tasks.append(self._respawn_entity(arena_idx, coin_id, self.ENTITY_COIN))

        # Process poison rewards and respawns
        for arena_idx, settlement in enumerate(poison_settlement_maps):
            arena_data = self.arenas_data[arena_idx]
            for poison_id, agent_list in settlement.items():
                # Assign poison penalty to all colliding agents
                for agent_id in agent_list:
                    if agent_id not in arena_data["ids_of_agents"]:
                        continue
                    agent_idx = arena_data["ids_of_agents"].index(agent_id)
                    per_arena_rewards[arena_idx]["poison"][agent_idx] += self.hazard_reward_num
                    arena_data["hit_poison"][agent_idx] = 1

                # Always respawn poison after collision
                respawn_tasks.append(self._respawn_entity(arena_idx, poison_id, self.ENTITY_POISON))

        return respawn_tasks

    async def _finalize_step(self, per_arena_rewards):
        """
        Finalize the step by calculating final rewards, generating observations, and checking termination.

        This method performs the final phase of each simulation step:
        1. Calculate mixed rewards (local + global components)
        2. Generate fresh observations for all agents
        3. Determine episode termination and truncation status

        Reward Mixing:
            final_reward = local_reward * local_ratio + global_reward * (1 - local_ratio)
            where:
            - local_reward = individual agent's total reward
            - global_reward = mean reward across all agents (encourages cooperation)

        Args:
            per_arena_rewards (List[Dict]): Accumulated rewards for all arenas containing:
                - 'control': Movement penalties
                - 'food': Food capture rewards
                - 'poison': Poison collision penalties

        Returns:
            Tuple containing:
                - observations (List[Dict]): New observations for all arenas
                - rewards (List[Dict]): Mixed rewards for all agents
                - terminateds (List[Dict]): Always False (no agent-specific termination)
                - truncateds (List[Dict]): True when max_cycles reached
                - infos (List[Dict]): Agent masks (all True)

        Note:
            The global reward component encourages agents to maximize team performance,
            not just individual rewards, which is crucial for cooperative behavior.
        """
        # Step 1: Calculate final mixed rewards for all arenas
        final_rewards_all_arenas = []
        for _arena_idx, rewards_dict in enumerate(per_arena_rewards):
            # Sum all reward components for each agent
            local_rewards = rewards_dict["control"] + rewards_dict["food"] + rewards_dict["poison"]

            # Calculate global (team) reward as mean of all agents
            global_reward = local_rewards.mean()

            # Mix local and global rewards
            final_rewards = local_rewards * self.local_ratio + global_reward * (1 - self.local_ratio)

            # Convert to dictionary format
            final_rewards_all_arenas.append({self.agents[i]: final_rewards[i] for i in range(self.n_rescuers)})

        # Step 2: Generate fresh observations through ray-tracing
        jobs, rays_directions_map = self.build_observation_rays()
        ray_results = await ts.UnaryAPI.multi_line_trace_by_object(self.conn, jobs=jobs, enable_debug_draw=True)
        observations = self.process_ray_results(ray_results, rays_directions_map)

        # Step 3: Determine termination and truncation status
        # Terminated: Never happens (agents don't die)
        terminated_all_arenas = [dict.fromkeys(self.agents, False) for _ in self.arena_ids]

        # Truncated: Episode ends when max_cycles is reached
        truncated_all_arenas = []
        for arena_idx in range(len(self.arena_ids)):
            is_truncated = self.arenas_data[arena_idx]["count_step"] >= self.max_cycles
            truncated_all_arenas.append(dict.fromkeys(self.agents, is_truncated))

        # Step 4: Prepare info dictionaries (agent masks indicate active agents)
        info = [{"agent_mask": dict.fromkeys(self.agents, True)} for _ in self.arena_ids]

        return observations, final_rewards_all_arenas, terminated_all_arenas, truncated_all_arenas, info

    def close(self):
        """
        Close the environment and disconnect from TongSim.

        This method performs cleanup operations:
        - Closes the TongSim connection
        - Releases any held resources

        Note:
            Always call this method when finished with the environment to prevent
            resource leaks and ensure proper cleanup of the TongSim server connection.
        """
        print("[INFO] Closing MACS environment...")
        self.ue.close()
