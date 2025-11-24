# warehouse.py
import random

GRID_W = 27
GRID_H = 15
CELL = 32

def get_walls():
    """
    Celdas que corresponden al borde de ladrillos:
    - Fila 0 (arriba)
    - Fila GRID_H - 1 (abajo)
    - Columna 0 (izquierda)
    - Columna GRID_W - 1 (derecha)
    """
    walls = set()

    # filas de arriba y abajo
    for c in range(GRID_W):
        walls.add((0, c))              # borde superior de ladrillos
        walls.add((GRID_H - 1, c))     # borde inferior de ladrillos

    # columnas izquierda y derecha
    for r in range(GRID_H):
        walls.add((r, 0))              # borde izquierdo
        walls.add((r, GRID_W - 1))     # borde derecho

    return walls


def create_warehouse(initial_boxes=30, max_stack_initial=1):
    """
    Crea y devuelve (warehouse, destination_cells)
    warehouse: matriz GRID_H x GRID_W con counts de cajas por celda
    destination_cells: lista de celdas en la fila inferior (destino)
    """
    warehouse = [[0 for _ in range(GRID_W)] for _ in range(GRID_H)]
    walls = get_walls()  # para no poner cajas en el borde

    placed = 0
    attempts = 0

    # cajas iniciales solo en el área interior (no en la fila destino ni en paredes)
    while placed < initial_boxes and attempts < initial_boxes * 50:
        r = random.randint(0, GRID_H - 5)   # evitar zona de destino
        c = random.randint(0, GRID_W - 1)

        # NO poner cajas en el borde de ladrillos
        if (r, c) in walls:
            attempts += 1
            continue

        if warehouse[r][c] < max_stack_initial:
            if warehouse[r][c] == 0:
                warehouse[r][c] += 1
                placed += 1
        attempts += 1

    # las pilas de destino siguen siendo la fila inferior del grid
    destination_cells = [(GRID_H - 1, x) for x in range(GRID_W)]
    return warehouse, destination_cells
