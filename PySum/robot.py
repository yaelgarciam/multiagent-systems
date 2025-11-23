# robot.py
import math
import random
from bfs import bfs, neighbors4
CELL = 32
MOVE_SPEED = 3  # píxeles/frame (ya lo dejaste así)

class Robot:
    def __init__(self, rid, r, c, warehouse, destination_cells, color=(80,180,255)):
        self.id = rid
        self.r = r
        self.c = c
        self.x = c * CELL
        self.y = r * CELL
        self.color = color

        self.warehouse = warehouse
        self.destinations = destination_cells

        self.state = "search"   # search -> going_box -> pickup -> plan_drop -> going_drop -> drop -> form -> done
        self.carrying = False

        self.path = []          # lista de (r,c) pasos a seguir
        self.target_box = None   # coordenada de la caja objetivo (celda con caja)
        self.target_pile = None  # coordenada real de la pila destino (fila inferior, col)
        self.moves = 0

        # backoff frames cuando pierde contienda por celda (evita reintentos inmediatos)
        self.wait_frames = 0

    # helpers
    def dist_manhattan(self, a, b):
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

    def cells_adjacent_to_box_goals(self):
        goals = set()
        H = len(self.warehouse)
        W = len(self.warehouse[0])
        for r in range(H):
            for c in range(W):
                if self.warehouse[r][c] > 0 and (r, c) not in self.destinations:
                    for nr, nc in neighbors4(r, c, H, W):
                        if self.warehouse[nr][nc] == 0:
                            goals.add((nr, nc))
        return goals

    def find_drop_adjacent_goals(self):
        H = len(self.warehouse)
        W = len(self.warehouse[0])
        for col in range(W):
            pile = (H-1, col)
            if self.warehouse[pile[0]][pile[1]] < 5:
                # return all free adjacent cells to that pile
                adj = []
                for nr, nc in neighbors4(pile[0], pile[1], H, W):
                    if self.warehouse[nr][nc] == 0:
                        adj.append((nr, nc))
                if adj:
                    return set(adj), pile
        return set(), None

    def _path_is_valid_adjacent_steps(self, path):
        """
        Verifica que la ruta esté compuesta por pasos unitarios (Manhattan = 1)
        empezando desde la posición actual (self.r,self.c).
        """
        if not path:
            return True
        prev = (self.r, self.c)
        for step in path:
            if self.dist_manhattan(prev, step) != 1:
                return False
            prev = step
        return True

    def safe_move(self, nr, nc, robots_positions, allowed_map):
        """
        allowed_map: dict cell -> robot_id allowed to move into that cell this frame.
        Return values:
          True -> reached the target cell and updated r,c
          False -> blocked (cannot move into target)
          None -> still interpolating towards target
        """

        # Reject non-adjacent moves (evita movimientos diagonales raros)
        if self.dist_manhattan((self.r, self.c), (nr, nc)) != 1 and (nr, nc) != (self.r, self.c):
            return False

        # check if some other robot was chosen for that target this frame
        if (nr, nc) in allowed_map and allowed_map[(nr, nc)] != self.id:
            return False

        # robot collision with settled robots
        if (nr, nc) in robots_positions:
            return False
        # boxes collision
        if self.warehouse[nr][nc] > 0:
            return False

        tx = nc * CELL
        ty = nr * CELL
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist == 0:
            # already there
            self.r, self.c = nr, nc
            return True

        # movement in pixels per frame:
        speed_px = MOVE_SPEED  # interpretado como pixels/frame
        if speed_px <= 0:
            # fallback a interpolación suave si alguien pone 0
            self.x += (tx - self.x) * 0.2
            self.y += (ty - self.y) * 0.2
        else:
            # move along vector by up to speed_px
            move = min(speed_px, dist)
            # normalize
            nx = self.x + (dx / dist) * move
            ny = self.y + (dy / dist) * move
            self.x = nx
            self.y = ny

        # if close enough, snap to cell
        if abs(self.x - tx) < 1 and abs(self.y - ty) < 1:
            self.x = tx
            self.y = ty
            self.r, self.c = nr, nc
            return True
        return None

    def update(self, robots, allowed_map):
        """
        robots: list of Robot objects (including self)
        allowed_map: dict mapping cell -> robot_id allowed this frame to move into that cell
        """
        # handle backoff waiting
        if self.wait_frames > 0:
            self.wait_frames -= 1
            return

        H = len(self.warehouse)
        W = len(self.warehouse[0])
        robots_positions = {(rb.r, rb.c) for rb in robots if rb is not self}

        # if currently moving along a planned path, try to step towards next cell
        if self.path:
            # validate path is composed of adjacent steps; si no, descartar y recalcular
            if not self._path_is_valid_adjacent_steps(self.path):
                # fuerza replanificación
                self.path = []
                # small randomized backoff to avoid immediate contention
                self.wait_frames = random.randint(0, 3)
                return

            nr, nc = self.path[0]

            m = self.safe_move(nr, nc, robots_positions, allowed_map)
            if m is None:
                # still interpolating
                return
            if m is False:
                # blocked -> recalc route to same goal (avoid robots and boxes)
                occupied = set(robots_positions)
                # add box cells
                for r in range(H):
                    for c in range(W):
                        if self.warehouse[r][c] > 0:
                            occupied.add((r,c))
                # allow leaving start by removing own cell
                if (self.r, self.c) in occupied:
                    occupied.remove((self.r, self.c))
                goal = self.path[-1] if self.path else None

                # try replan to the same goal
                new_route = None
                if goal:
                    new_route = bfs((self.r, self.c), [goal], occupied, self.warehouse)

                # If replan failed or no goal, and we're trying to drop, fallback to plan_drop to search alternative piles
                if not new_route:
                    if self.state in ("going_drop", "plan_drop"):
                        # change to plan_drop to retrigger drop-seeking logic
                        self.path = []
                        self.state = "plan_drop"
                        # add a small backoff to lower collision probability
                        self.wait_frames = random.randint(0, 3)
                        return
                    else:
                        # other states: simply wait a bit before retry
                        self.path = []
                        self.wait_frames = random.randint(0, 3)
                        return

                # normalize BFS return: ensure it doesn't include start
                if len(new_route) >= 1 and new_route[0] == (self.r, self.c):
                    new_route = new_route[1:]
                self.path = new_route
                return
            # m is True -> reached next cell
            self.path.pop(0)
            self.moves += 1
            return

        # STATE MACHINE
        # 1) SEARCH: plan path to a free cell adjacent to any box (not in destination)
        if self.state == "search":
            # find goals: free cells adjacent to boxes (filter out destination piles)
            goals = set()
            for r in range(H):
                for c in range(W):
                    if self.warehouse[r][c] > 0 and (r,c) not in self.destinations:
                        for nr, nc in neighbors4(r, c, H, W):
                            if self.warehouse[nr][nc] == 0 and (nr,nc) not in robots_positions:
                                goals.add((nr,nc))
            if not goals:
                # nothing to pick -> go to form
                self.state = "form"
                return

            # blocked set = robots positions + cells with boxes
            blocked = set(robots_positions)
            for rr in range(H):
                for cc in range(W):
                    if self.warehouse[rr][cc] > 0:
                        blocked.add((rr,cc))
            # allow leaving current cell
            if (self.r, self.c) in blocked:
                blocked.remove((self.r, self.c))

            route = bfs((self.r, self.c), goals, blocked, self.warehouse)
            if route:
                # bfs returns path excluding start in our implementation; ensure no start duplicate
                if route and route[0] == (self.r, self.c):
                    route = route[1:]
                # validate adjacency of first step
                if route and self.dist_manhattan((self.r,self.c), route[0]) != 1:
                    # something odd: discard and backoff
                    self.path = []
                    self.wait_frames = random.randint(0, 2)
                    return
                self.path = route or []
                if self.path:
                    self.state = "going_box"
            return

        # 2) going_box: when path empty, we are adjacent to a box -> pick it
        if self.state == "going_box":
            # find adjacent box
            for nr, nc in neighbors4(self.r, self.c, H, W):
                if self.warehouse[nr][nc] > 0 and (nr,nc) not in self.destinations:
                    # pick box
                    self.warehouse[nr][nc] -= 1
                    self.carrying = True
                    self.state = "plan_drop"
                    self.target_box = None
                    self.path = []
                    return
            # if no adjacent box (race), go back to search
            self.state = "search"
            return

        # 3) plan_drop: pick an adjacent free cell to a pile as goal, and set target_pile (actual pile coordinate)
        if self.state == "plan_drop":
            # try to find any pile adjacent free cell
            adj_goals, pile = self.find_drop_adjacent_goals()
            if not adj_goals:
                # nowhere to drop now -> wait and retry later while keeping carrying True
                # keep state plan_drop and back off a bit to avoid busy-loop
                self.wait_frames = random.randint(0, 3)
                return

            # blocked includes robots positions and boxes
            blocked = set(robots_positions)
            for rr in range(H):
                for cc in range(W):
                    if self.warehouse[rr][cc] > 0:
                        blocked.add((rr,cc))
            if (self.r, self.c) in blocked:
                blocked.remove((self.r, self.c))

            route = bfs((self.r, self.c), adj_goals, blocked, self.warehouse)
            if route:
                if route and route[0] == (self.r, self.c):
                    route = route[1:]
                # ensure adjacency of first step
                if route and self.dist_manhattan((self.r,self.c), route[0]) != 1:
                    # odd route -> backoff and retry later
                    self.wait_frames = random.randint(0, 2)
                    return
                self.path = route or []
                self.target_pile = pile
                self.state = "going_drop"
            else:
                # can't find route now -> backoff and retry
                self.wait_frames = random.randint(0, 3)
            return

        # 4) going_drop: handled at top (movement); when path empty we arrived to adj cell and will execute drop
        if self.state == "going_drop":
            # if path empty, we are at adj cell -> drop logic
            if not self.path:
                # if no target_pile (race), go back to plan_drop
                if not self.target_pile:
                    self.state = "plan_drop"
                    return

                pr, pc = self.target_pile
                # verify pile still has space
                if self.warehouse[pr][pc] < 5:
                    # double-check that we are adjacent to the pile (safety)
                    if self.dist_manhattan((self.r, self.c), (pr, pc)) == 1:
                        self.warehouse[pr][pc] += 1
                        self.carrying = False
                        self.target_pile = None
                        self.state = "search"
                        return
                    else:
                        # if we're not adjacent (race or moved), go to plan_drop to replan
                        self.state = "plan_drop"
                        self.target_pile = None
                        return

                # if full, look for alternative piles (right then left)
                found = None
                for col in range(pc+1, W):
                    if self.warehouse[H-1][col] < 5:
                        found = (H-1, col)
                        break
                if not found:
                    for col in range(pc-1, -1, -1):
                        if self.warehouse[H-1][col] < 5:
                            found = (H-1, col)
                            break
                if not found:
                    # nowhere to drop -> revert to plan_drop and keep carrying
                    self.target_pile = None
                    self.state = "plan_drop"
                    self.wait_frames = random.randint(0, 3)
                    return

                # attempt to move to a free adjacent cell near found
                adj_free = set()
                for ar, ac in neighbors4(found[0], found[1], H, W):
                    if self.warehouse[ar][ac] == 0 and (ar,ac) not in robots_positions:
                        adj_free.add((ar,ac))
                if not adj_free:
                    # can't reach the adjacent cell now -> go back to plan_drop and retry later
                    self.target_pile = None
                    self.state = "plan_drop"
                    self.wait_frames = random.randint(0, 3)
                    return

                # recalc route to adj_free
                blocked = set(robots_positions)
                for rr in range(H):
                    for cc in range(W):
                        if self.warehouse[rr][cc] > 0:
                            blocked.add((rr,cc))
                if (self.r, self.c) in blocked:
                    blocked.remove((self.r, self.c))
                route = bfs((self.r, self.c), adj_free, blocked, self.warehouse)
                if route:
                    if route and route[0] == (self.r, self.c):
                        route = route[1:]
                    # safety: ensure adjacency first step
                    if route and self.dist_manhattan((self.r,self.c), route[0]) != 1:
                        # weird route, backoff
                        self.wait_frames = random.randint(0, 2)
                        self.target_pile = None
                        self.state = "plan_drop"
                        return
                    self.path = route or []
                    self.target_pile = found
                    self.state = "going_drop"
                else:
                    # wait and retry later, keep carrying
                    self.target_pile = None
                    self.state = "plan_drop"
                    self.wait_frames = random.randint(0, 3)
                    return
            return

        # 5) form
        if self.state == "form":
            # go to top row at column = id (clamped)
            goal = (0, min(self.id, W-1))
            # blocked set
            blocked = set(robots_positions)
            for rr in range(H):
                for cc in range(W):
                    if self.warehouse[rr][cc] > 0:
                        blocked.add((rr,cc))
            if (self.r, self.c) in blocked:
                blocked.remove((self.r, self.c))
            route = bfs((self.r, self.c), [goal], blocked, self.warehouse)
            if route:
                if route and route[0] == (self.r, self.c):
                    route = route[1:]
                # safety: ensure adjacency
                if route and self.dist_manhattan((self.r,self.c), route[0]) != 1:
                    self.wait_frames = random.randint(0, 2)
                    return
                self.path = route or []
                if self.path:
                    self.state = "going_drop"  # reuse movement machinery to go to formation tile
            return

    # draw helper
    def draw(self, screen):
        import pygame
        rect = (int(self.x), int(self.y), CELL, CELL)
        pygame.draw.rect(screen, self.color, rect)
        if self.carrying:
            pygame.draw.circle(screen, (255,200,0), (int(self.x+CELL/2), int(self.y+CELL/2)), 6)
