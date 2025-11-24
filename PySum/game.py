# game.py
import pygame
import random
from warehouse import create_warehouse, GRID_H, GRID_W, CELL, get_walls
from robot import Robot

pygame.init()
screen = pygame.display.set_mode((GRID_W * CELL, GRID_H * CELL))
clock = pygame.time.Clock()

# cargar escenario de fondo
background_img = pygame.image.load("sources/scenario.jpg").convert()
background_img = pygame.transform.scale(background_img, (GRID_W * CELL, GRID_H * CELL))

# cargar sprite de la caja
box_img = pygame.image.load("sources/box.png").convert_alpha()
box_img = pygame.transform.scale(box_img, (CELL, CELL))


# create warehouse and destination cells
warehouse, destination_cells = create_warehouse(initial_boxes=30, max_stack_initial=1)
walls = get_walls()

# spawn robots in empty cells (not in walls)
NUM_ROBOTS = 5
robots = []
colors = [(200,50,50),(50,200,50),(50,50,200),(200,200,50),(200,50,200)]

for i in range(NUM_ROBOTS):
    placed = False
    for attempt in range(500):
        r = random.randint(0, GRID_H - 2)  # avoid bottom row spawn
        c = random.randint(0, GRID_W - 1)
        if (
            warehouse[r][c] == 0
            and (r, c) not in [(rb.r, rb.c) for rb in robots]
            and (r, c) not in walls
        ):
            robots.append(Robot(i, r, c, warehouse, destination_cells, colors[i]))
            placed = True
            break

    if not placed:
        for rr in range(GRID_H - 1):
            for cc in range(GRID_W):
                if (
                    warehouse[rr][cc] == 0
                    and (rr, cc) not in [(rb.r, rb.c) for rb in robots]
                    and (rr, cc) not in walls
                ):
                    robots.append(Robot(i, rr, cc, warehouse, destination_cells, colors[i]))
                    placed = True
                    break
            if placed:
                break

# initialize robots
for rb in robots:
    rb.update(robots, {})

TIME_LIMIT_MS = 100_000  # 100 seconds
start_time_ms = pygame.time.get_ticks()
finished = False
total_moves = 0

font_small = pygame.font.SysFont(None, 20)
font_big = pygame.font.SysFont(None, 36)


def draw_scene():
    screen.blit(background_img, (0, 0))

    # draw grid & boxes
    for r in range(GRID_H):
        for c in range(GRID_W):
            x = c * CELL
            y = r * CELL
            rect = (x, y, CELL, CELL)

            pygame.draw.rect(screen, (70, 70, 70), rect, 1)

            if warehouse[r][c] > 0:
                # dibujar la caja
                screen.blit(box_img, (x, y))

                # número de cajas (centrado)
                txt = font_small.render(str(warehouse[r][c]), True, (0, 0, 0))
                tx = x + CELL // 2 - txt.get_width() // 2
                ty = y + CELL // 2 - txt.get_height() // 2
                screen.blit(txt, (tx, ty))

    # robots
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


# ---------------- MAIN LOOP ----------------
running = True
while running:
    dt = clock.tick(30)

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False

    # resolve movement intentions
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

    # ---------------- CHECK COMPLETION ----------------
    # 1) ¿Quedan cajas fuera de la fila destino?
    remaining_outside = any(
        warehouse[r][c] > 0 and (r, c) not in destination_cells
        for r in range(GRID_H)
        for c in range(GRID_W)
    )

    # 2) ¿Algún robot sigue cargando caja?
    robots_carrying = any(rb.carrying for rb in robots)

    # 3) ¿Ya están formados?
    formed = all(rb.state == "form" and not rb.path for rb in robots)

    # Step 1:
    # Si ya NO hay cajas fuera de la fila destino,
    # los robots que NO traen caja se pueden ir a formar
    if not remaining_outside:
        for rb in robots:
            if not rb.carrying and rb.state != "form":
                rb.state = "form"
                rb.path = []

    # Step 2:
    # Cuando ya no hay cajas fuera, nadie trae caja y todos se formaron → éxito
    if not remaining_outside and not robots_carrying and formed and not finished:
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

    # ---------------- TIME LIMIT ----------------
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
