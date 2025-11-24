# robot.py
import math
import random
import pygame
from bfs import bfs, neighbors4
from warehouse import get_walls

CELL = 32
MOVE_SPEED = 3

FPS = 30              # igual que en game.py
STUCK_TIME_S = 3
STUCK_FRAMES = FPS * STUCK_TIME_S

class Robot:
    def __init__(self, rid, r, c, warehouse, destination_cells, color=(80, 180, 255)):
        self.id = rid
        self.r = r
        self.c = c
        self.x = c * CELL
        self.y = r * CELL
        self.color = color

        # sprite
        self.sprite = pygame.image.load("sources/robot.png").convert_alpha()
        self.sprite = pygame.transform.scale(self.sprite, (CELL, CELL))

        self.warehouse = warehouse
        self.destinations = destination_cells

        self.state = "search"
        self.carrying = False

        self.path = []
        self.target_box = None
        self.target_pile = None
        self.moves = 0
        self.wait_frames = 0

        # Paredes (NO pisables)
        self.walls = get_walls()

        # Anti-stuck
        self.stuck_frames = 0
        self.last_pos = (self.r, self.c)

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
        """
        Busca celdas libres adyacentes a las pilas de destino
        en la fila de piso (una arriba de la pared).
        """
        H = len(self.warehouse)
        W = len(self.warehouse[0])

        # fila destino tomada de destination_cells
        if self.destinations:
            dest_row = self.destinations[0][0]
        else:
            dest_row = H - 2  # fallback

        for col in range(1, W - 1):
            pile = (dest_row, col)
            if self.warehouse[pile[0]][pile[1]] < 5:
                adj = []
                for nr, nc in neighbors4(pile[0], pile[1], H, W):
                    if self.warehouse[nr][nc] == 0 and (nr, nc) not in self.walls:
                        adj.append((nr, nc))
                if adj:
                    return set(adj), pile
        return set(), None

    def _path_is_valid_adjacent_steps(self, path):
        if not path:
            return True
        prev = (self.r, self.c)
        for step in path:
            if self.dist_manhattan(prev, step) != 1:
                return False
            prev = step
        return True

    def safe_move(self, nr, nc, robots_positions, allowed_map):
        # No entrar a paredes
        if (nr, nc) in self.walls:
            return False

        if self.dist_manhattan((self.r, self.c), (nr, nc)) != 1 and (nr, nc) != (self.r, self.c):
            return False

        if (nr, nc) in allowed_map and allowed_map[(nr, nc)] != self.id:
            return False

        if (nr, nc) in robots_positions:
            return False
        
        if self.warehouse[nr][nc] > 0:
            return False

        # movimiento físico
        tx = nc * CELL
        ty = nr * CELL
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)

        if dist == 0:
            self.r, self.c = nr, nc
            return True

        move = min(MOVE_SPEED, dist)
        self.x += (dx / dist) * move
        self.y += (dy / dist) * move

        if abs(self.x - tx) < 1 and abs(self.y - ty) < 1:
            self.x = tx
            self.y = ty
            self.r, self.c = nr, nc
            return True

        return None

    def update(self, robots, allowed_map):
        if self.wait_frames > 0:
            self.wait_frames -= 1
            return

        H = len(self.warehouse)
        W = len(self.warehouse[0])
        robots_positions = {(rb.r, rb.c) for rb in robots if rb is not self}

        # ---------------- DETECT STUCK (3s sin moverse) ----------------
        if (self.r, self.c) == self.last_pos:
            self.stuck_frames += 1
        else:
            self.stuck_frames = 0

        self.last_pos = (self.r, self.c)

        if self.stuck_frames >= STUCK_FRAMES:
            # 1) Si está buscando caja, intentar BFS ignorando robots
            if self.state == "search":
                goals = set()
                for r in range(H):
                    for c in range(W):
                        if self.warehouse[r][c] > 0 and (r, c) not in self.destinations:
                            for nr, nc in neighbors4(r, c, H, W):
                                if (
                                    self.warehouse[nr][nc] == 0
                                    and (nr, nc) not in self.walls
                                ):
                                    goals.add((nr, nc))

                if goals:
                    blocked = set()
                    for rr in range(H):
                        for cc in range(W):
                            if self.warehouse[rr][cc] > 0:
                                blocked.add((rr, cc))
                    blocked |= self.walls

                    route = bfs((self.r, self.c), goals, blocked, self.warehouse)
                    if route:
                        if route[0] == (self.r, self.c):
                            route = route[1:]
                        self.path = route
                        self.state = "going_box"
                        self.stuck_frames = 0
                        return

            # 2) Si está intentando dejar caja, replan drop ignorando robots
            elif self.state in ("plan_drop", "going_drop") and self.carrying:
                adj_goals, pile = self.find_drop_adjacent_goals()
                if adj_goals:
                    blocked = set()
                    for rr in range(H):
                        for cc in range(W):
                            if self.warehouse[rr][cc] > 0:
                                blocked.add((rr, cc))
                    blocked |= self.walls

                    route = bfs((self.r, self.c), adj_goals, blocked, self.warehouse)
                    if route:
                        if route[0] == (self.r, self.c):
                            route = route[1:]
                        self.path = route
                        self.target_pile = pile
                        self.state = "going_drop"
                        self.stuck_frames = 0
                        return

            # 3) Si está formando, intentar form ignorando robots
            elif self.state == "form":
                goal = (1, min(self.id, W-1))
                blocked = set()
                for rr in range(H):
                    for cc in range(W):
                        if self.warehouse[rr][cc] > 0:
                            blocked.add((rr, cc))
                blocked |= self.walls

                route = bfs((self.r, self.c), [goal], blocked, self.warehouse)
                if route:
                    if route[0] == (self.r, self.c):
                        route = route[1:]
                    self.path = route
                    self.stuck_frames = 0
                    return

            # 4) Fallback: reset de estado
            self.path = []
            if self.state in ("going_drop", "plan_drop"):
                self.state = "plan_drop"
            else:
                self.state = "search"
            self.wait_frames = random.randint(1, 3)
            self.stuck_frames = 0
            return

        # ---------------- MOVEMENT ----------------
        if self.path:
            if not self._path_is_valid_adjacent_steps(self.path):
                self.path = []
                self.wait_frames = random.randint(0, 3)
                return

            nr, nc = self.path[0]
            m = self.safe_move(nr, nc, robots_positions, allowed_map)

            if m is None:
                return

            if m is False:
                occupied = set(robots_positions)
                for r in range(H):
                    for c in range(W):
                        if self.warehouse[r][c] > 0:
                            occupied.add((r, c))

                # paredes bloquean paso real
                occupied |= self.walls

                if (self.r, self.c) in occupied:
                    occupied.remove((self.r, self.c))

                goal = self.path[-1] if self.path else None
                new_route = bfs((self.r, self.c), [goal], occupied, self.warehouse) if goal else None

                if not new_route:
                    self.path = []
                    self.wait_frames = random.randint(0, 3)
                    if self.state in ("going_drop", "plan_drop"):
                        self.state = "plan_drop"
                    return

                if new_route[0] == (self.r, self.c):
                    new_route = new_route[1:]

                self.path = new_route
                return

            self.path.pop(0)
            self.moves += 1
            return

        # ---------------- STATE MACHINE ----------------

        # ---- SEARCH ----
        if self.state == "search":
            goals = set()
            for r in range(H):
                for c in range(W):
                    if self.warehouse[r][c] > 0 and (r, c) not in self.destinations:
                        for nr, nc in neighbors4(r, c, H, W):
                            if (
                                self.warehouse[nr][nc] == 0
                                and (nr, nc) not in self.walls
                            ):
                                goals.add((nr, nc))

            if not goals:
                self.wait_frames = random.randint(1, 3)
                return

            # robots + cajas + paredes bloquean BFS
            blocked = set(robots_positions)
            for rr in range(H):
                for cc in range(W):
                    if self.warehouse[rr][cc] > 0:
                        blocked.add((rr, cc))

            blocked |= self.walls

            if (self.r, self.c) in blocked:
                blocked.remove((self.r, self.c))

            route = bfs((self.r, self.c), goals, blocked, self.warehouse)
            if route:
                if route[0] == (self.r, self.c):
                    route = route[1:]
                self.path = route
                self.state = "going_box"
            else:
                self.wait_frames = random.randint(1, 3)
            return

        # ---- GOING BOX ----
        if self.state == "going_box":
            for nr, nc in neighbors4(self.r, self.c, H, W):
                if self.warehouse[nr][nc] > 0 and (nr, nc) not in self.destinations:
                    self.warehouse[nr][nc] -= 1
                    self.carrying = True
                    self.state = "plan_drop"
                    self.path = []
                    return
            self.state = "search"
            return

        # ---- PLAN DROP ----
        if self.state == "plan_drop":
            adj_goals, pile = self.find_drop_adjacent_goals()
            if not adj_goals:
                self.wait_frames = random.randint(0, 3)
                return

            blocked = set(robots_positions)
            for rr in range(H):
                for cc in range(W):
                    if self.warehouse[rr][cc] > 0:
                        blocked.add((rr, cc))

            blocked |= self.walls

            if (self.r, self.c) in blocked:
                blocked.remove((self.r, self.c))

            route = bfs((self.r, self.c), adj_goals, blocked, self.warehouse)
            if route:
                if route[0] == (self.r, self.c):
                    route = route[1:]
                self.path = route
                self.target_pile = pile
                self.state = "going_drop"
            else:
                self.wait_frames = random.randint(0, 3)
            return

        # ---- GOING DROP ----
        if self.state == "going_drop":
            if not self.path:

                if not self.target_pile:
                    self.state = "plan_drop"
                    return

                pr, pc = self.target_pile
                if self.warehouse[pr][pc] < 5:
                    if self.dist_manhattan((self.r, self.c), (pr, pc)) == 1:
                        self.warehouse[pr][pc] += 1
                        self.carrying = False
                        self.target_pile = None
                        self.state = "search"
                        return
                    else:
                        self.state = "plan_drop"
                        self.target_pile = None
                        return

                # fila destino (piso) para buscar otra columna
                if self.destinations:
                    dest_row = self.destinations[0][0]
                else:
                    dest_row = H - 2

                found = None
                for col in range(pc-1, 0, -1):
                    if self.warehouse[dest_row][col] < 5:
                        found = (dest_row, col)
                        break
                if not found:
                    for col in range(pc-1, 0, -1):
                        if self.warehouse[dest_row][col] < 5:
                            found = (dest_row, col)
                            break

                if not found:
                    self.state = "plan_drop"
                    self.target_pile = None
                    self.wait_frames = random.randint(0, 3)
                    return

                adj_free = set()
                for ar, ac in neighbors4(found[0], found[1], H, W):
                    if (
                        self.warehouse[ar][ac] == 0
                        and (ar, ac) not in robots_positions
                        and (ar, ac) not in self.walls
                    ):
                        adj_free.add((ar, ac))

                if not adj_free:
                    self.target_pile = None
                    self.state = "plan_drop"
                    self.wait_frames = random.randint(0, 3)
                    return

                blocked = set(robots_positions)
                for rr in range(H):
                    for cc in range(W):
                        if self.warehouse[rr][cc] > 0:
                            blocked.add((rr, cc))

                blocked |= self.walls

                if (self.r, self.c) in blocked:
                    blocked.remove((self.r, self.c))

                route = bfs((self.r, self.c), adj_free, blocked, self.warehouse)
                if route:
                    if route[0] == (self.r, self.c):
                        route = route[1:]
                    self.path = route
                    self.target_pile = found
                else:
                    self.target_pile = None
                    self.state = "plan_drop"
                    self.wait_frames = random.randint(0, 3)
                return

        # ---- FORM ----
        if self.state == "form":
            # meta: fila 1, columna según id, sin tocar la pared de arriba
            goal_col = min(self.id, W - 2)   # evitar última columna pegada a pared
            goal = (1, goal_col)

            # EN FORM: ignoramos robots, solo bloquean cajas + paredes
            blocked = set()
            for rr in range(H):
                for cc in range(W):
                    if self.warehouse[rr][cc] > 0:
                        blocked.add((rr, cc))

            blocked |= self.walls

            # nunca nos bloqueamos a nosotros mismos
            if (self.r, self.c) in blocked:
                blocked.remove((self.r, self.c))

            route = bfs((self.r, self.c), [goal], blocked, self.warehouse)
            if route:
                if route[0] == (self.r, self.c):
                    route = route[1:]
                self.path = route
            return

    # ---------------- DRAW ----------------
    def draw(self, screen):
        screen.blit(self.sprite, (int(self.x), int(self.y)))

        if self.carrying:
            margin = 3
            rect = pygame.Rect(int(self.x), int(self.y), CELL, CELL)
            pygame.draw.rect(screen, (150, 90, 40), rect, margin)
