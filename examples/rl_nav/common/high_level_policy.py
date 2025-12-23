import math

import numpy as np

from common import para


def distance(a, b):
    x1, y1 = a
    x2, y2 = b
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def find_frontiers(internal_map):
    """
    find frontier points in the internal map.

    parameters:
    internal_map (numpy.ndarray): UNKNOW、OBS、GOAL、AGENT、FREE to represent the internal map

    returns:
    list: list of frontier points (x, y)
    """
    frontiers = []
    height, width = internal_map.shape
    # define 4-connected directions
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]

    # get free mask
    free_mask = internal_map == para.FREE

    for x in range(height):
        for y in range(width):
            if free_mask[x, y]:
                for dx, dy in directions:
                    nx, ny = x + dx, y + dy

                    if (
                        0 <= nx < height
                        and 0 <= ny < width
                        and internal_map[nx, ny] == para.UNKNOW
                    ):
                        # if internal_map[nx, ny] == para.UNKNOW:
                        if is_safe_frontier(internal_map, (x, y), n=para.AGENT_PIX + 1):
                            too_close = False
                            for fx, fy in frontiers:
                                dist = np.hypot(fx - x, fy - y)
                                if dist < 5:
                                    # skip too close frontier points
                                    too_close = True
                                    break
                            if not too_close:
                                frontiers.append((x, y))
                        break
    return frontiers


def is_safe_frontier(internal_map, frontier, n=para.AGENT_PIX):
    """check if the frontier point is safe to approach."""
    height, width = internal_map.shape
    x, y = frontier
    x_min = max(0, x - n)
    x_max = min(width, x + n + 1)
    y_min = max(0, y - n)
    y_max = min(height, y + n + 1)
    tmp = internal_map[x_min:x_max, y_min:y_max]
    coords = np.argwhere(tmp == para.OBS)
    return not len(coords) > 0


class HighLevelPolicy:
    def __init__(self, map_size):
        self.internal_map = np.full(map_size, para.UNKNOW)
        self.targets = []
        self.agent_pos = (0, 0)
        self.curr_global_goal = None
        self.steps_towards_goal = 0

    def update0(self, local_view, agent_pos):
        """
        update internal_map based on local_view.
        can see through walls.
        """
        view_size = local_view.shape[0]
        half_view = view_size // 2
        self.agent_pos = agent_pos

        for i in range(view_size):
            for j in range(view_size):
                global_x = agent_pos[0] + i - half_view
                global_y = agent_pos[1] + j - half_view

                if (
                    0 <= global_x < self.internal_map.shape[0]
                    and 0 <= global_y < self.internal_map.shape[1]
                ):
                    cell_type = local_view[i, j]
                    old_cell_type = self.internal_map[global_x, global_y]
                    self.internal_map[global_x, global_y] = cell_type

                    if (
                        cell_type == para.GOAL
                        and (global_x, global_y) not in self.targets
                    ):
                        self.targets.append((global_x, global_y))
                    elif (
                        old_cell_type == para.GOAL
                        and cell_type != para.GOAL
                        and (global_x, global_y) in self.targets
                    ):
                        self.targets.remove((global_x, global_y))

    def update(self, local_view, agent_pos):
        """
        update internal_map based on local_view.
        can't see through walls.
        """
        view_size = local_view.shape[0]
        half_view = view_size // 2

        self.agent_pos = agent_pos

        for i in range(view_size):
            for j in range(view_size):
                global_x = agent_pos[0] + i - half_view
                global_y = agent_pos[1] + j - half_view

                if (
                    0 <= global_x < self.internal_map.shape[0]
                    and 0 <= global_y < self.internal_map.shape[1]
                ):
                    # transform to relative coordinates (centered at agent)
                    rel_x, rel_y = i - half_view, j - half_view
                    # get line cells using Bresenham's line algorithm
                    line_cells = self._bresenham_line(0, 0, rel_x, rel_y)
                    blocked = False
                    for lx, ly in line_cells:
                        gx, gy = agent_pos[0] + lx, agent_pos[1] + ly
                        if not (
                            0 <= gx < self.internal_map.shape[0]
                            and 0 <= gy < self.internal_map.shape[1]
                        ):
                            break
                        cell_type = local_view[half_view + lx, half_view + ly]
                        if not blocked:
                            old_cell_type = self.internal_map[gx, gy]
                            self.internal_map[gx, gy] = cell_type

                            if cell_type == para.GOAL and (gx, gy) not in self.targets:
                                self.targets.append((gx, gy))
                            elif (
                                old_cell_type == para.GOAL
                                and cell_type != para.GOAL
                                and (gx, gy) in self.targets
                            ):
                                self.targets.remove((gx, gy))

                            if cell_type == para.OBS:
                                blocked = True
                        else:
                            break

    def _bresenham_line(self, x0, y0, x1, y1):
        """
        Bresenham algorithm source: https://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm
        return list of (x, y) points from (x0, y0) to (x1, y1)
        """
        points = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            points.append((x0, y0))
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
        return points

    def get_global_goal(self, force_update=False):
        """
        get or update the global goal.

        parameters:
            force_update (bool): if True, force to update the global goal
        """
        if (
            force_update
            or self.curr_global_goal is None
            or self.steps_towards_goal >= para.MAX_UPDATE_GOAL_STEPS
        ):
            # reset steps towards goal
            self.steps_towards_goal = 0
            old_global_goal = self.curr_global_goal

            # first try to go to target points
            if self.targets:
                self.curr_global_goal = min(
                    self.targets, key=lambda p: distance(p, self.agent_pos)
                )
            else:
                # if no target points, find frontiers
                self.frontiers = find_frontiers(self.internal_map)
                if self.frontiers:
                    sorted_frontiers = sorted(
                        self.frontiers, key=lambda p: distance(p, self.agent_pos)
                    )
                    self.curr_global_goal = (
                        sorted_frontiers[
                            (sorted_frontiers.index(old_global_goal) + 1)
                            % len(sorted_frontiers)
                        ]
                        if old_global_goal in sorted_frontiers
                        else sorted_frontiers[0]
                    )
                else:
                    # all explored
                    self.curr_global_goal = None
        else:
            self.steps_towards_goal += 1

        return self.curr_global_goal
