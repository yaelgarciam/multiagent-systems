# bfs.py
from collections import deque

def neighbors4(r, c, H, W):
    for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < H and 0 <= nc < W:
            yield nr, nc

def bfs(start, goals, blocked, warehouse):
    """
    start: (r,c)
    goals: set/list of (r,c)
    blocked: set of (r,c) to avoid (robots positions + boxes)
    warehouse: matrix (only used for dimensions)
    Returns list of cells from next step..goal included, or None
    """
    H = len(warehouse)
    W = len(warehouse[0])
    if not goals:
        return None

    goals_set = set(goals)

    queue = deque([start])
    prev = {start: None}

    # allow starting cell even if blocked (so robot can leave)
    blocked_local = set(blocked)
    if start in blocked_local:
        blocked_local.remove(start)

    while queue:
        cur = queue.popleft()
        if cur in goals_set:
            # reconstruct path from start to cur (exclusive start)
            path = []
            node = cur
            while node != start:
                path.append(node)
                node = prev[node]
            path.reverse()
            return path

        for nr, nc in neighbors4(cur[0], cur[1], H, W):
            if (nr, nc) in prev:
                continue
            if (nr, nc) in blocked_local:
                continue
            prev[(nr, nc)] = cur
            queue.append((nr, nc))

    return None
