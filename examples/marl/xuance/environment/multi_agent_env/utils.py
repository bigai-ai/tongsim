"""
Utility functions for multi-agent environment simulation.

This module provides helper functions for physics calculations, async task management,
and geometric transformations used in the MACS multi-agent environment.
"""

import asyncio
import random
import time
import uuid

import numpy as np
import tongsim as ts

DEFAULT_CONFIG = {
    "grpc_endpoint": "127.0.0.1:5726",
    "level_asset_path": "/Game/Developer/Maps/L_Mulit_Agent_DemoRL.L_Mulit_Agent_DemoRL",
    "agent_bp_path": "/Game/Developer/Characters/UE4Mannequin/BP_UE4Mannequin.BP_UE4Mannequin_C",
    "coin_bp_path": "/Game/developer/DemoCoin/BP_DemoCoin.BP_DemoCoin_C",
    "poison_bp_path": "/Game/developer/DemoCoin/BP_DemoPoision.BP_DemoPoision_C",
    "arena_spacing": 3000.0,
    "spawn_z": 200.0,
    "x_bounds": (50, 1900),
    "y_bounds": (-1900, -50),
    "block_ranges": [[[1200, 1500], [-1500, -1000]]],
    "action_multiplier": 150.0,
    "coin_scale": ts.Vector3(1.2, 1.2, 1.2),
    "default_scale": ts.Vector3(1.0, 1.0, 1.0),
}


def get_grid_anchor(arena_index: int, num_arenas: int, spacing: float) -> ts.Transform:
    """
    Calculates the anchor transform for an arena in a grid layout.

    This function determines the world-space position of an arena by calculating
    its row and column in a 2D grid (as close to a square as possible)
    based on its linear index.

    Args:
        arena_index (int): The index of the arena (starting from 0).
        num_arenas (int): The total number of arenas.
        spacing (float): The spacing between arenas.

    Returns:
        ts.Transform: A TongSim Transform object containing the calculated position.
    """
    grid_cols = int(np.ceil(np.sqrt(num_arenas)))

    row = arena_index // grid_cols
    col = arena_index % grid_cols

    x_pos = col * spacing
    y_pos = row * spacing

    return ts.Transform(location=ts.Vector3(x_pos, y_pos, 0.0))


async def get_actor_transform_safe(conn, actor_id_list):
    """
    Safely retrieve transforms for multiple actors concurrently.

    This function fetches actor transforms in parallel and handles exceptions
    gracefully. If any actor fails to return a valid transform, an error is raised.

    Args:
        conn: TongSim connection object for API calls.
        actor_id_list: List of actor IDs to retrieve transforms for.

    Returns:
        Dictionary mapping actor IDs to their Transform objects.
        Empty dictionary if actor_id_list is empty.

    Raises:
        RuntimeError: If any actor fails to return a valid transform.

    Example:
        >>> transforms = await get_actor_transform_safe(conn, ["actor_1", "actor_2"])
        >>> print(f"Actor 1 position: {transforms['actor_1'].location}")
    """
    if not actor_id_list:
        return {}

    # Create concurrent tasks for all actor transform requests
    tasks = [ts.UnaryAPI.get_actor_transform(conn, actor_id) for actor_id in actor_id_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results and build transform mapping
    id_to_transform_map = {}
    for i, res in enumerate(results):
        if isinstance(res, ts.Transform):
            actor_id = actor_id_list[i]
            id_to_transform_map[actor_id] = res
        else:
            actor_id = actor_id_list[i]
            raise RuntimeError(f"Failed to get transform for actor {actor_id}: {res}")

    return id_to_transform_map


async def spawn_actors_concurrently(
    context, arena_id: str, count: int, blueprint_path: str, actor_type_name: str, spawn_z: float
) -> list[dict]:
    """
    Spawn multiple actors concurrently in a specified arena.

    This function generates safe random locations for actors and spawns them
    in parallel to improve performance. Failed spawns are tracked and reported.

    Args:
        context: World context containing connection and configuration.
        arena_id: Identifier of the target arena for spawning.
        count: Number of actors to spawn.
        blueprint_path: Path to the actor blueprint in TongSim.
        actor_type_name: Human-readable name for the actor type (for logging).
        spawn_z: Z-coordinate (height) for actor placement.

    Returns:
        List of successfully spawned actor dictionaries.

    Raises:
        RuntimeError: If any actors fail to spawn, with detailed error information.

    Example:
        >>> actors = await spawn_actors_concurrently(
        ...     context, "arena_1", 5, "/Game/Blueprints/Agent", "Pursuer", 10.0
        ... )
        >>> print(f"Spawned {len(actors)} actors successfully")
    """
    # Generate spawn tasks with random safe locations

    tasks = []
    for _i in range(count):
        # Generate safe random location for this actor
        rand_x, rand_y = generate_safe_random_location(
            DEFAULT_CONFIG["x_bounds"], DEFAULT_CONFIG["y_bounds"], DEFAULT_CONFIG["block_ranges"]
        )

        # Create spawn task
        tasks.append(
            ts.UnaryAPI.spawn_actor_in_arena(
                context.conn,
                arena_id,
                blueprint_path,
                ts.Transform(location=ts.Vector3(rand_x, rand_y, spawn_z)),
                15.0,  # Spawn timeout in seconds
            )
        )

    # Execute all spawn operations concurrently
    spawn_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Categorize results
    successful_spawns = []
    failed_spawns = []

    for i, res in enumerate(spawn_results):
        if isinstance(res, dict):
            successful_spawns.append(res)
        else:
            failed_spawns.append((i, res))

    # Handle spawn failures
    if failed_spawns:
        print(f"  - [WARNING] Arena {arena_id}: {len(failed_spawns)} {actor_type_name}(s) failed to spawn:")
        for idx, error in failed_spawns:
            print(f"    - Index {idx}: {error}")
        raise RuntimeError(
            f"Actor spawning failed in arena {arena_id}! "
            f"This may be due to connection issues or invalid blueprint path."
        )

    return successful_spawns


def arena_anchor_at(x: float, y: float = 0.0) -> ts.Transform:
    """
    Calculate arena placement position to prevent overlapping.

    Args:
        x: X-coordinate offset for arena position.
        y: Y-coordinate offset for arena position (default: 0.0).

    Returns:
        TongSim Transform object with the calculated position (Z=0).

    Example:
        >>> transform = arena_anchor_at(500.0, 100.0)
    """
    return ts.Transform(location=ts.Vector3(x, y, 0))


def generate_safe_random_location(
    x_bounds: tuple[float, float],
    y_bounds: tuple[float, float],
    block_ranges: list[list[list[float]]],
    max_retries: int = 100,
) -> tuple[float, float] | None:
    """
    Generate a random location within specified bounds that avoids blocked regions.

    This function uses rejection sampling to generate a valid random coordinate.
    It repeatedly samples random points until one is found outside all blocked regions,
    or the maximum number of attempts is reached.

    Args:
        x_bounds: Tuple (min_x, max_x) defining the valid range for x-coordinate.
        y_bounds: Tuple (min_y, max_y) defining the valid range for y-coordinate.
        block_ranges: List of blocked regions to avoid. Each region should define
                      a rectangular area where agents cannot be placed.
        max_retries: Maximum number of sampling attempts before giving up.
                     Prevents infinite loops when valid space is scarce.

    Returns:
        Tuple (x, y) containing the generated safe coordinates if successful.
        None if no valid location is found after max_retries attempts.

    Note:
        If this function frequently returns None, consider:
        - Increasing max_retries
        - Reducing the size of blocked regions
        - Expanding the bounds to provide more valid space

    Example:
        >>> x_bounds = (-100, 100)
        >>> y_bounds = (-100, 100)
        >>> blocked = [[[0, 0], [10, 10]]]  # Block region from (0,0) to (10,10)
        >>> loc = generate_safe_random_location(x_bounds, y_bounds, blocked)
        >>> if loc:
        ...     print(f"Safe location found at: {loc}")
    """
    for _ in range(max_retries):
        # Sample a random candidate coordinate within the specified bounds
        candidate_x = random.uniform(x_bounds[0], x_bounds[1])
        candidate_y = random.uniform(y_bounds[0], y_bounds[1])

        # Check if the candidate location is outside all blocked regions
        if not _is_location_in_block_ranges(candidate_x, candidate_y, block_ranges):
            # Valid location found - return immediately
            return candidate_x, candidate_y

    # All attempts exhausted without finding a valid location
    print(f"Warning: Failed to find a safe location after {max_retries} attempts.")
    return None


def _is_location_in_block_ranges(x: float, y: float, block_ranges: list[list[list[float]]]) -> bool:
    """
    Check if a point falls within any blocked region.

    Helper function for generate_safe_random_location that tests whether
    a given coordinate intersects with any of the defined blocked areas.

    Args:
        x: X-coordinate of the point to test.
        y: Y-coordinate of the point to test.
        block_ranges: List of blocked rectangular regions.

    Returns:
        True if the point is inside any blocked region, False otherwise.
    """
    for block in block_ranges:
        # Each block is defined by two corners: [[x_min, y_min], [x_max, y_max]]
        x_min, y_min = block[0]
        x_max, y_max = block[1]

        # Check if point is within the rectangular block
        if x_min <= x <= x_max and y_min <= y <= y_max:
            return True

    return False


def calculate_bounce_velocity_sample(
    velocity_vector: np.ndarray, wall_normal_vector: ts.Vector3, restitution: float = 1.0, scatter_strength: float = 0.4
) -> np.ndarray:
    """
    Calculate bounce velocity with stochastic scattering effect.

    This function simulates realistic collision with walls by combining
    perfect reflection with random scattering. The scatter_strength parameter
    controls the balance between deterministic reflection and random perturbation.

    Args:
        velocity_vector: Incoming velocity vector as 2D numpy array [vx, vy].
        wall_normal_vector: Normal vector of the wall (TongSim Vector3 object).
        restitution: Coefficient of restitution (0 = inelastic, 1 = elastic).
        scatter_strength: Strength of random scattering (0 = perfect reflection, 1 = fully random).

    Returns:
        Reflected velocity vector as 2D numpy array with applied scattering.

    Note:
        The scatter_strength parameter allows modeling of surface roughness
        and non-ideal collision behavior.
    """
    # Base reflection (invert velocity)
    base_reflection = -velocity_vector

    # Generate random scatter direction
    random_scatter = np.random.standard_normal(2)
    norm_scatter = np.linalg.norm(random_scatter)
    if norm_scatter > 1e-6:
        random_scatter /= norm_scatter

    # Blend deterministic reflection with random scattering
    new_velocity_direction = (1 - scatter_strength) * base_reflection + scatter_strength * random_scatter

    # Normalize and scale to original speed with restitution
    norm_new_velocity = np.linalg.norm(new_velocity_direction)
    if norm_new_velocity < 1e-6:
        # Degenerate case: use pure random direction
        final_velocity = random_scatter * np.linalg.norm(velocity_vector) * restitution
    else:
        # Normal case: scale normalized direction to match original speed
        final_velocity = (new_velocity_direction / norm_new_velocity) * np.linalg.norm(velocity_vector) * restitution

    return final_velocity


def calculate_bounce_velocity(
    velocity_vector: np.ndarray, wall_normal_vector: ts.Vector3, restitution: float = 1.0
) -> np.ndarray:
    """
    Calculate bounce velocity using perfect specular reflection.

    Implements the standard reflection formula: v' = v - 2(v·n)n
    where v is the incident velocity and n is the wall normal vector.

    Args:
        velocity_vector: Incoming velocity vector as 2D numpy array [vx, vy].
        wall_normal_vector: Normal vector of the wall (TongSim Vector3 object).
        restitution: Coefficient of restitution controlling energy loss (0-1).

    Returns:
        Reflected velocity vector as 2D numpy array.

    Note:
        If the velocity is already moving away from the wall (dot product >= 0),
        the velocity is returned unchanged to prevent incorrect reflections.
    """
    # Convert wall normal to numpy array
    wall_normal = np.array([wall_normal_vector.x, wall_normal_vector.y])

    # Normalize the wall normal vector
    norm_of_normal = np.linalg.norm(wall_normal)
    if norm_of_normal < 1e-8:
        # Degenerate case: invalid normal, return original velocity
        return velocity_vector
    wall_normal /= norm_of_normal

    # Calculate dot product between velocity and normal
    dot_product = np.dot(velocity_vector, wall_normal)

    # Check if velocity is already moving away from wall
    if dot_product >= 0:
        return velocity_vector

    # Apply reflection formula: v' = v - 2(v·n)n
    bounce_vector = velocity_vector - 2 * dot_product * wall_normal

    # Apply coefficient of restitution
    return bounce_vector * restitution


async def run_and_time_task(coro, agent_id):
    """
    Execute an asynchronous coroutine and measure its execution time.

    This utility function wraps async operations to provide timing information
    and exception handling, useful for performance monitoring and debugging.

    Args:
        coro: Coroutine to be executed.
        agent_id: Identifier of the agent associated with this task.

    Returns:
        Dictionary containing:
            - agent_id: The agent identifier
            - status: "completed" or "failed"
            - result: The coroutine's return value (if successful)
            - error: The exception object (if failed)
            - end_time: Timestamp when execution finished
            - duration: Total execution time in seconds

    Example:
        >>> result = await run_and_time_task(some_async_func(), "agent_0")
        >>> print(f"Task took {result['duration']:.3f}s")
    """
    start_time = time.monotonic()
    try:
        # Execute the coroutine
        original_result = await coro
        return {
            "agent_id": agent_id,
            "status": "completed",
            "result": original_result,
            "end_time": time.monotonic(),
            "duration": time.monotonic() - start_time,
        }
    except Exception as e:
        # Capture exception and timing information
        return {
            "agent_id": agent_id,
            "status": "failed",
            "error": e,
            "end_time": time.monotonic(),
            "duration": time.monotonic() - start_time,
        }


def convert_bytes_le_to_guid_string(guid_bytes_le: bytes) -> str:
    """
    Convert little-endian GUID bytes to uppercase string representation.

    This function is useful for converting binary GUID data from TongSim
    to human-readable string format compatible with Unreal Engine's GUID system.

    Args:
        guid_bytes_le: 16-byte GUID in little-endian format.

    Returns:
        Uppercase GUID string in format: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX

    Example:
        >>> guid_bytes = b'\\x01\\x02\\x03\\x04\\x05\\x06\\x07\\x08\\x09\\x0a\\x0b\\x0c\\x0d\\x0e\\x0f\\x10'
        >>> convert_bytes_le_to_guid_string(guid_bytes)
        '04030201-0605-0807-090A-0B0C0D0E0F10'
    """
    # Parse bytes as UUID in little-endian format
    uuid_obj = uuid.UUID(bytes_le=guid_bytes_le)

    # Convert to string representation
    guid_string = str(uuid_obj)

    # Return uppercase version for consistency with UE conventions
    return guid_string.upper()


def generate_circular_rays(forward_vector: np.ndarray, num_rays: int = 30, radius: float = 1.0) -> np.ndarray:
    """
    Generate evenly distributed ray directions in a circle around a forward vector.

    This function creates a set of 3D ray directions by rotating the forward vector
    around the Z-axis. Useful for implementing omnidirectional sensors or
    uniform sampling in circular patterns.

    Args:
        forward_vector: Initial direction vector (3D numpy array).
        num_rays: Number of rays to generate (evenly distributed 360°).
        radius: Scaling factor for ray lengths.

    Returns:
        Array of shape (num_rays, 3) containing the generated ray directions.

    Raises:
        ValueError: If forward_vector is a zero vector.

    Example:
        >>> rays = generate_circular_rays(np.array([1, 0, 0]), num_rays=8)
        >>> rays.shape
        (8, 3)
    """
    # Convert to numpy array and validate
    forward_vector = np.array(forward_vector, dtype=float)
    norm = np.linalg.norm(forward_vector)
    if norm == 0:
        raise ValueError("Input vector cannot be a zero vector.")

    # Normalize the initial vector
    initial_vector = forward_vector / norm

    # Calculate angular increment for uniform distribution
    angle_increment_rad = np.deg2rad(360.0 / num_rays)

    rays = []
    for i in range(num_rays):
        # Calculate rotation angle for this ray
        current_angle_rad = i * angle_increment_rad
        c, s = np.cos(current_angle_rad), np.sin(current_angle_rad)

        # Construct 3D rotation matrix around Z-axis
        rotation_matrix_z = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

        # Apply rotation and scaling
        new_ray = rotation_matrix_z @ initial_vector
        new_ray = new_ray * radius
        rays.append(new_ray)

    return np.array(rays)


if __name__ == "__main__":
    """
    Demonstration script for circular ray generation.

    This example generates rays and visualizes them using matplotlib
    to verify the uniform distribution around a forward vector.
    """
    import matplotlib.pyplot as plt

    # Configuration
    actor_forward_vector = np.array([1, 0, 0])
    number_of_rays = 30

    # Generate rays
    generated_rays = generate_circular_rays(actor_forward_vector, num_rays=number_of_rays)

    # Create visualization
    fig, ax = plt.subplots(figsize=(8, 8))

    # Draw unit circle for reference
    unit_circle = plt.Circle((0, 0), 1, color="gray", linestyle="--", fill=False, label="Unit Circle")
    ax.add_artist(unit_circle)

    # Plot generated rays as arrows
    ax.quiver(
        np.zeros(number_of_rays),
        np.zeros(number_of_rays),
        generated_rays[:, 0],
        generated_rays[:, 1],
        color="blue",
        alpha=0.7,
        label="Generated Rays",
        angles="xy",
        scale_units="xy",
        scale=1,
    )

    # Highlight the initial forward vector
    ax.quiver(
        0,
        0,
        actor_forward_vector[0],
        actor_forward_vector[1],
        color="red",
        label="Initial Vector (0°)",
        angles="xy",
        scale_units="xy",
        scale=1,
        zorder=10,
    )

    # Configure plot appearance
    ax.set_xlim([-1.5, 1.5])
    ax.set_ylim([-1.5, 1.5])
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle=":")
    ax.set_xlabel("X-axis", fontsize=12)
    ax.set_ylabel("Y-axis", fontsize=12)
    ax.set_title(f"Visualization of {number_of_rays} Circular Rays", fontsize=14)
    ax.legend()

    # Display the plot
    plt.show()
