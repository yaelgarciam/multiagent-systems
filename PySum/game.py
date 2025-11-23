# game.py
import pygame
import random
from warehouse import create_warehouse, GRID_H, GRID_W, CELL
from robot import Robot
from bfs import bfs

pygame.init()
screen = pygame.display.set_mode((GRID_W * CELL, GRID_H * CELL))
clock = pygame.time.Clock()

# cargar escenario de fondo
background_img = pygame.image.load("sources/scenario.jpg").convert()
background_img = pygame.transform.scale(background_img, (GRID_W * CELL, GRID_H * CELL))

# create warehouse and destination cells
warehouse, destination_cells = create_warehouse(initial_boxes=30, max_stack_initial=1)

# spawn robots in empty cells
NUM_ROBOTS = 5
robots = []
colors = [(200,50,50),(50,200,50),(50,50,200),(200,200,50),(200,50,200)]

for i in range(NUM_ROBOTS):
    placed = False
    for attempt in range(500):
        r = random.randint(0, GRID_H - 2)  # avoid bottom row spawn
        c = random.randint(0, GRID_W - 1)
        if warehouse[r][c] == 0 and (r, c) not in [(rb.r, rb.c) for rb in robots]:
            robots.append(Robot(i, r, c, warehouse, destination_cells, colors[i]))
            placed = True
            break
    if not placed:
        for rr in range(GRID_H - 1):
            for cc in range(GRID_W):
                if warehouse[rr][cc] == 0 and (rr, cc) not in [(rb.r, rb.c) for rb in robots]:
                    robots.append(Robot(i, rr, cc, warehouse, destination_cells, colors[i]))
                    placed = True
                    break
            if placed:
                break

# initial paths
for rb in robots:
    rb.update(robots, {})

TIME_LIMIT_MS = 90_000  # 90 seconds
start_time_ms = pygame.time.get_ticks()
finished = False
total_moves = 0

font_small = pygame.font.SysFont(None, 20)
font_big = pygame.font.SysFont(None, 36)


def draw_scene():
    # fondo del escenario
    screen.blit(background_img, (0, 0))

    # draw grid & boxes
    for r in range(GRID_H):
        for c in range(GRID_W):
            x = c * CELL
            y = r * CELL
            rect = (x, y, CELL, CELL)

            pygame.draw.rect(screen, (70, 70, 70), rect, 1)

            if warehouse[r][c] > 0:
                pygame.draw.rect(screen, (190, 140, 60), (x + 4, y + 4, CELL - 8, CELL - 8))
                txt = font_small.render(str(warehouse[r][c]), True, (0, 0, 0))
                screen.blit(txt, (x + 6, y + 4))

    # draw robots
    for rb in robots:
        rb.draw(screen)

    # timer
    elapsed_ms = pygame.time.get_ticks() - start_time_ms
    elapsed_s = elapsed_ms // 1000
    total_s = TIME_LIMIT_MS // 1000

    timer_txt = font_small.render(f"Timer: {elapsed_s}s / {total_s}s", True, (255, 255, 255))
    screen.blit(timer_txt, (8, 8))


def show_popup(success, time_s, moves):
    overlay = pygame.Surface((GRID_W * CELL, GRID_H * CELL))
    overlay.set_alpha(220)
    overlay.fill((10, 10, 10))
    screen.blit(overlay, (0, 0))

    msg = "TAREA COMPLETADA" if success else "TIEMPO AGOTADO"

    t1 = font_big.render(msg, True, (255, 255, 255))
    t2 = font_small.render(f"Tiempo (s): {time_s:.2f}", True, (255, 255, 255))
    t3 = font_small.render(f"Movimientos: {moves}", True, (255, 255, 255))

    screen.blit(t1, (GRID_W * CELL // 2 - t1.get_width() // 2, GRID_H * CELL // 2 - 40))
    screen.blit(t2, (GRID_W * CELL // 2 - t2.get_width() // 2, GRID_H * CELL // 2 + 10))
    screen.blit(t3, (GRID_W * CELL // 2 - t3.get_width() // 2, GRID_H * CELL // 2 + 40))

    pygame.display.flip()


# main loop
running = True
while running:
    dt = clock.tick(30)

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False

    intentions = {}
    for rb in robots:
        if rb.path:
            target = tuple(rb.path[0])
            intentions.setdefault(target, []).append(rb)

    allowed_map = {}
    for cell, lst in intentions.items():
        if len(lst) == 1:
            allowed_map[cell] = lst[0].id
        else:
            chosen = min(lst, key=lambda r: r.id)
            allowed_map[cell] = chosen.id

    # update robots
    for rb in robots:
        prev_pos = (rb.r, rb.c)
        rb.update(robots, allowed_map)
        if (rb.r, rb.c) != prev_pos:
            total_moves += 1

    # check completion
    remaining_outside = any(
        warehouse[r][c] > 0 and (r, c) not in destination_cells
        for r in range(GRID_H) for c in range(GRID_W)
    )

    all_full = all(warehouse[GRID_H - 1][c] == 5 for c in range(GRID_W))
    formed = all(rb.state == "form" and not rb.path for rb in robots)

    if not remaining_outside and all_full:
        for rb in robots:
            if rb.state != "form":
                rb.state = "form"
                rb.path = []

    if all_full and not remaining_outside and formed and not finished:
        finished = True
        elapsed_s = (pygame.time.get_ticks() - start_time_ms) / 1000.0

        show_popup(True, elapsed_s, total_moves)

        waiting = True
        while waiting:
            for ev in pygame.event.get():
                if ev.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    waiting = False
                    running = False
            clock.tick(10)
        break

    if (pygame.time.get_ticks() - start_time_ms) >= TIME_LIMIT_MS and not finished:
        finished = True
        elapsed_s = TIME_LIMIT_MS / 1000.0
        show_popup(False, elapsed_s, total_moves)

        waiting = True
        while waiting:
            for ev in pygame.event.get():
                if ev.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    waiting = False
                    running = False
            clock.tick(10)
        break

    draw_scene()
    pygame.display.flip()

pygame.quit()
