import pygame
import random
from collections import deque
import math

pygame.init()

# -----------------------------------------
# CONFIGURACIÓN GENERAL
# -----------------------------------------
GRID_W = 15
GRID_H = 20
CELL = 32
WIDTH = GRID_W * CELL
HEIGHT = GRID_H * CELL
FPS = 30

screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

MOVE_SPEED = 0.3   # ajustado (0.3 es suave y razonable)
N_ROBOTS = 5

# -----------------------------------------
# AUXILIARES
# -----------------------------------------
def neighbors4(r, c):
    for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
        nr, nc = r+dr, c+dc
        if 0 <= nr < GRID_H and 0 <= nc < GRID_W:
            yield nr, nc

def bfs(start, goals, robot_positions, warehouse):
    if not goals:
        return None

    sr, sc = start
    queue = deque([(sr, sc, [])])
    visited = {(sr, sc)}

    obstacles = set(robot_positions)

    for r in range(GRID_H):
        for c in range(GRID_W):
            if warehouse[r][c] > 0:
                obstacles.add((r, c))

    # permitir salir de la propia celda incluso si ahora hay caja
    if start in obstacles:
        obstacles.remove(start)

    while queue:
        r, c, path = queue.popleft()

        if (r, c) in goals:
            return path

        for nr, nc in neighbors4(r, c):
            if (nr, nc) not in visited and (nr, nc) not in obstacles:
                visited.add((nr, nc))
                queue.append((nr, nc, path + [(nr, nc)]))

    return None

# -----------------------------------------
# ALMACÉN
# -----------------------------------------
warehouse = [[0 for _ in range(GRID_W)] for _ in range(GRID_H)]

INITIAL_BOXES = 35
for _ in range(INITIAL_BOXES):
    while True:
        r = random.randint(0, GRID_H-5)
        c = random.randint(0, GRID_W-1)
        if warehouse[r][c] == 0:
            warehouse[r][c] = 1
            break

destination_cells = [(GRID_H - 1, x) for x in range(GRID_W)]

# -----------------------------------------
# ROBOT
# -----------------------------------------
class Robot:
    def __init__(self, rid):
        self.id = rid

        while True:
            r = random.randint(0, GRID_H-10)
            c = random.randint(0, GRID_W-1)
            if warehouse[r][c] == 0:
                self.r, self.c = r, c
                break

        self.x = self.c * CELL
        self.y = self.r * CELL
        self.state = "search"
        self.carrying = False
        self.path = []
        self.target_pile = None

    def nearest_box_goal(self, all_robots):
        robot_positions = {(rb.r, rb.c) for rb in all_robots}
        goals = set()

        for r in range(GRID_H):
            for c in range(GRID_W):
                if warehouse[r][c] > 0 and (r, c) not in destination_cells:
                    for nr, nc in neighbors4(r, c):
                        if warehouse[nr][nc] == 0 and (nr, nc) not in robot_positions:
                            goals.add((nr, nc))
        return goals

    def nearest_drop_goal(self, all_robots):
        robot_positions = {(rb.r, rb.c) for rb in all_robots}

        for c in range(GRID_W):
            pile = (GRID_H-1, c)
            if warehouse[pile[0]][pile[1]] < 5:
                for nr, nc in neighbors4(pile[0], pile[1]):
                    if warehouse[nr][nc] == 0 and (nr, nc) not in robot_positions:
                        return [(nr, nc)], pile
        return [], None

    def update(self, all_robots):
        robot_positions = {(rb.r, rb.c) for rb in all_robots if rb is not self}

        # STATE: SEARCH (buscar caja)
        if self.state == "search":
            goals = self.nearest_box_goal(all_robots)
            if not goals:
                self.state = "form"
                return

            route = bfs((self.r, self.c), goals, robot_positions, warehouse)
            if route:
                self.path = route
                self.state = "going_box"
            return

        # STATE: GOING_BOX (ir a la celda adyacente a la caja)
        if self.state == "going_box":
            if not self.path:
                self.state = "search"
                return

            nr, nc = self.path[0]
            self.x += (nc*CELL - self.x)*MOVE_SPEED
            self.y += (nr*CELL - self.y)*MOVE_SPEED

            if abs(self.x - nc*CELL) < 1 and abs(self.y - nr*CELL) < 1:
                self.r, self.c = nr, nc
                self.path.pop(0)

            if not self.path:
                for ar, ac in neighbors4(self.r, self.c):
                    if warehouse[ar][ac] > 0 and (ar, ac) not in destination_cells:
                        warehouse[ar][ac] -= 1
                        self.carrying = True
                        self.state = "drop"
                        break
            return

        # STATE: DROP (planear celda adyacente a pila)
        if self.state == "drop":
            adj_goals, real_pile = self.nearest_drop_goal(all_robots)
            if not adj_goals:
                return

            route = bfs((self.r, self.c), adj_goals, robot_positions, warehouse)
            if route:
                self.path = route
                self.target_pile = real_pile
                self.state = "going_drop"
            return

        # STATE: GOING_DROP (moverse a la celda adyacente asignada)
        if self.state == "going_drop":
            if not self.path:
                self.state = "drop"
                return

            nr, nc = self.path[0]
            self.x += (nc*CELL - self.x)*MOVE_SPEED
            self.y += (nr*CELL - self.y)*MOVE_SPEED

            if abs(self.x - nc*CELL) < 1 and abs(self.y - nr*CELL) < 1:
                self.r, self.c = nr, nc
                self.path.pop(0)

            # al llegar a la celda adyacente -> procesar entrega o reasignar pila
            if not self.path:
                pr, pc = self.target_pile

                # si sigue teniendo espacio -> entregar
                if warehouse[pr][pc] < 5:
                    warehouse[pr][pc] += 1
                    self.carrying = False
                    self.target_pile = None
                    self.state = "search"
                    return

                # si está llena, buscar siguiente pila
                found_pile = None
                for nc in range(pc + 1, GRID_W):
                    if warehouse[GRID_H - 1][nc] < 5:
                        found_pile = (GRID_H - 1, nc)
                        break
                if not found_pile:
                    for nc in range(pc - 1, -1, -1):
                        if warehouse[GRID_H - 1][nc] < 5:
                            found_pile = (GRID_H - 1, nc)
                            break

                if not found_pile:
                    # no hay pila disponible -> fallback
                    self.carrying = False
                    self.target_pile = None
                    self.state = "search"
                    return

                # buscar celdas adyacentes libres alrededor de found_pile
                new_pr, new_pc = found_pile
                adj_goals = set()
                for ar, ac in neighbors4(new_pr, new_pc):
                    if warehouse[ar][ac] == 0 and (ar, ac) not in robot_positions:
                        adj_goals.add((ar, ac))

                if not adj_goals:
                    # no hay celda adyacente libre -> fallback
                    self.carrying = False
                    self.target_pile = None
                    self.state = "search"
                    return

                # calcular ruta hacia una celda adyacente nueva
                new_route = bfs((self.r, self.c), adj_goals, robot_positions, warehouse)
                if new_route:
                    self.path = new_route
                    self.target_pile = (new_pr, new_pc)
                    self.state = "going_drop"
                    return
                else:
                    # esperar e intentar en el siguiente tick
                    return

        # STATE: FORM (ir a fila superior)
        if self.state == "form":
            goal = (0, self.id)
            if not self.path:
                route = bfs((self.r, self.c), [goal], robot_positions, warehouse)
                if route:
                    self.path = route

            if self.path:
                nr, nc = self.path[0]
                self.x += (nc*CELL - self.x)*MOVE_SPEED
                self.y += (nr*CELL - self.y)*MOVE_SPEED
                if abs(self.x - nc*CELL) < 1 and abs(self.y - nr*CELL) < 1:
                    self.r, self.c = nr, nc
                    self.path.pop(0)

# -----------------------------------------
# SIMULACIÓN
# -----------------------------------------
robots = [Robot(i) for i in range(N_ROBOTS)]
running = True
finished = False
total_moves = 0
frames = 0

# TIMER: 90 segundos
start_time_ms = pygame.time.get_ticks()
TIME_LIMIT_MS = 90_000

def show_result_popup(success, frames, moves):
    # overlay simple
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(220)
    overlay.fill((20,20,20))
    screen.blit(overlay, (0,0))

    font = pygame.font.SysFont(None, 36)
    small = pygame.font.SysFont(None, 24)

    if success:
        msg = "TAREA COMPLETADA"
    else:
        msg = "TIEMPO AGOTADO"

    txt = font.render(msg, True, (255,255,255))
    screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 80))

    s1 = small.render(f"Tiempo (frames): {frames}", True, (255,255,255))
    s2 = small.render(f"Movimientos totales: {moves}", True, (255,255,255))

    screen.blit(s1, (WIDTH//2 - s1.get_width()//2, HEIGHT//2 - 20))
    screen.blit(s2, (WIDTH//2 - s2.get_width()//2, HEIGHT//2 + 20))

    prompt = small.render("Presiona cualquier tecla o clic para salir", True, (180,180,180))
    screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, HEIGHT//2 + 80))

    pygame.display.flip()

# main loop
while running:
    frames += 1
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # check timer
    elapsed_ms = pygame.time.get_ticks() - start_time_ms
    time_up = elapsed_ms >= TIME_LIMIT_MS

    # comprobar si quedan cajas fuera del destino
    remaining_boxes = any(
        warehouse[r][c] > 0 and (r, c) not in destination_cells
        for r in range(GRID_H)
        for c in range(GRID_W)
    )

    all_full = all(warehouse[GRID_H - 1][c] == 5 for c in range(GRID_W))

    # si no quedan cajas, forzar formación
    if not remaining_boxes and all_full:
        for rb in robots:
            rb.state = "form"

    # actualizar robots (solo si no terminado ni time_up)
    if not finished and not time_up:
        for rb in robots:
            prev = (rb.r, rb.c)
            rb.update(robots)
            if (rb.r, rb.c) != prev:
                total_moves += 1

        formed = all(rb.state == "form" and not rb.path for rb in robots)

        if all_full and formed:
            finished = True
            success = True
            # mostrar popup final
            show_result_popup(success, frames, total_moves)
            # esperar interacción del usuario para cerrar
            waiting = True
            while waiting:
                for e in pygame.event.get():
                    if e.type == pygame.QUIT:
                        waiting = False
                        running = False
                    if e.type == pygame.KEYDOWN or e.type == pygame.MOUSEBUTTONDOWN:
                        waiting = False
                        running = False
                clock.tick(10)
            break

    # si tiempo agotado -> mostrar popup con estado y stats
    if time_up and not finished:
        success = all_full and not remaining_boxes
        show_result_popup(success, frames, total_moves)
        waiting = True
        while waiting:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    waiting = False
                    running = False
                if e.type == pygame.KEYDOWN or e.type == pygame.MOUSEBUTTONDOWN:
                    waiting = False
                    running = False
            clock.tick(10)
        break

    # DIBUJADO
    screen.fill((30,30,30))

    for r in range(GRID_H):
        for c in range(GRID_W):
            if warehouse[r][c] > 0:
                pygame.draw.rect(screen, (200,150,50),
                                 (c*CELL+6, r*CELL+6, CELL-12, CELL-12))
                font = pygame.font.SysFont(None, 18)
                txt = font.render(str(warehouse[r][c]), True, (0,0,0))
                screen.blit(txt, (c*CELL+12, r*CELL+6))

    for rb in robots:
        color = (80,180,255) if not rb.carrying else (255,180,80)
        pygame.draw.rect(screen, color,
                         (rb.x+4, rb.y+4, CELL-8, CELL-8))

    # dibujar timer arriba a la izquierda
    elapsed_s = (pygame.time.get_ticks() - start_time_ms) // 1000
    font = pygame.font.SysFont(None, 20)
    timer_txt = font.render(f"Timer: {elapsed_s}s / 60s", True, (255,255,255))
    screen.blit(timer_txt, (8,8))

    pygame.display.flip()

pygame.quit()
