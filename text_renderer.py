
import pygame
from OpenGL.GL import *

# Cache global: (text, color_tuple, font_id) → (tex_id, w, h)
_TEXT_CACHE: dict = {}


def _get_or_create_texture(text: str, color: tuple, font: pygame.font.Font):
    """
    Devuelve (tex_id, width, height) para el texto dado.
    Si ya existe en cache, lo reutiliza. Si no, lo crea.
    """
    key = (text, color, id(font))
    if key in _TEXT_CACHE:
        return _TEXT_CACHE[key]

    # Renderizar con pygame (antialiasing ON)
    surf = font.render(text, True, color)
    surf = surf.convert_alpha()
    w, h = surf.get_size()

    # Voltear verticalmente: pygame Y=0 arriba, OpenGL Y=0 abajo
    surf = pygame.transform.flip(surf, False, True)
    data = pygame.image.tostring(surf, "RGBA", False)

    # Crear textura en GPU
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, data)
    glBindTexture(GL_TEXTURE_2D, 0)

    _TEXT_CACHE[key] = (tex_id, w, h)
    return tex_id, w, h


def draw_text(x: float, y: float, text: str,
              font: pygame.font.Font,
              color: tuple = (255, 255, 255),
              anchor: str = "topleft",
              alpha: float = 1.0):
    
    if not text:
        return

    tex_id, w, h = _get_or_create_texture(text, tuple(color), font)

    # Calcular posición según anchor
    # En glOrtho(0, W, 0, H): Y=0 es ABAJO, Y=H es ARRIBA
    # 'anchor' describe dónde cae (x, y) respecto al rectángulo del texto
    if "right" in anchor:
        bx = x - w
    elif "center" in anchor:
        bx = x - w / 2
    else:  # left
        bx = x

    if "top" in anchor:
        # y es la coordenada del borde SUPERIOR del texto
        # En glOrtho Y=0 abajo, así que el borde superior = y_abajo + h
        by = y - h          # by = borde INFERIOR en coords OpenGL
    elif "mid" in anchor or anchor == "center":
        by = y - h / 2
    else:  # bottom
        by = y

    # Dibujar quad texturizado
    glEnable(GL_TEXTURE_2D)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(1.0, 1.0, 1.0, alpha)
    glBindTexture(GL_TEXTURE_2D, tex_id)

    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(bx,     by)
    glTexCoord2f(1, 0); glVertex2f(bx + w, by)
    glTexCoord2f(1, 1); glVertex2f(bx + w, by + h)
    glTexCoord2f(0, 1); glVertex2f(bx,     by + h)
    glEnd()

    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_TEXTURE_2D)
    glDisable(GL_BLEND)


def clear_text_cache():
    """Libera todas las texturas de texto de la GPU. Llamar al salir."""
    global _TEXT_CACHE
    for tex_id, w, h in _TEXT_CACHE.values():
        glDeleteTextures([tex_id])
    _TEXT_CACHE.clear()
