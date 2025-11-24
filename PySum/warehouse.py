# warehouse.py
import random

GRID_W = 27
GRID_H = 15
CELL = 32

def get_walls():
    """
    Regresa un set de celdas que son pared dentro del grid lógico.
    - Fila 0 completa (borde superior)
    - Columna 0 y columna GRID_W-1 (bordes laterales),
      excluyendo la última fila que es el destino.
    """
    walls = set()

    # fila superior completa
    for c in range(GRID_W):
        walls.add((0, c))

    # columnas izquierda y derecha (todas menos la fila destino)
    for r in range(GRID_H - 1):   # excluimos la última fila
        walls.add((r, 0))
        walls.add((r, GRID_W - 1))

    return walls

def create_warehouse(initial_boxes=30, max_stack_initial=1):
    """
    Crea y devuelve (warehouse, destination_cells)
    warehouse: matriz GRID_H x GRID_W con counts de cajas por celda
    destination_cells: lista de celdas en la fila inferior (destino)
    """
    warehouse = [[0 for _ in range(GRID_W)] for _ in range(GRID_H)]
    walls = get_walls()

    placed = 0
    attempts = 0
    # queremos exactamente `initial_boxes` cajas, sin apilar (max_stack_initial=1)
    while placed < initial_boxes and attempts < initial_boxes * 50:
        r = random.randint(0, GRID_H - 5)   # evitar fila destino
        c = random.randint(0, GRID_W - 1)

        if (r, c) in walls:
            attempts += 1
            continue
        
        if warehouse[r][c] < max_stack_initial:
            # si max_stack_initial == 1 esto asegura no apilar
            if warehouse[r][c] == 0:
                warehouse[r][c] += 1
                placed += 1
        attempts += 1

    destination_cells = [(GRID_H - 1, x) for x in range(GRID_W)]
    return warehouse, destination_cells
