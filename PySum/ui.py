
import pygame

def show_popup(screen, success, time_s, moves):
    overlay = pygame.Surface(screen.get_size())
    overlay.set_alpha(220)
    overlay.fill((30,30,30))

    font_big = pygame.font.SysFont(None, 48)
    font_small = pygame.font.SysFont(None, 28)

    msg = "TAREA COMPLETADA" if success else "TIEMPO AGOTADO"

    text_main = font_big.render(msg, True, (255,255,255))
    text_time = font_small.render(f"Tiempo: {time_s:.2f} segundos", True, (255,255,255))
    text_moves = font_small.render(f"Movimientos: {moves}", True, (255,255,255))
    prompt = font_small.render("Presiona cualquier tecla para salir", True, (180,180,180))

    overlay.blit(text_main, (screen.get_width()//2 - text_main.get_width()//2, 200))
    overlay.blit(text_time, (screen.get_width()//2 - text_time.get_width()//2, 260))
    overlay.blit(text_moves, (screen.get_width()//2 - text_moves.get_width()//2, 300))
    overlay.blit(prompt, (screen.get_width()//2 - prompt.get_width()//2, 360))

    screen.blit(overlay, (0,0))
    pygame.display.flip()
