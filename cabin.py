
import math
import pygame
from OpenGL.GL import *

from text_renderer import draw_text


COL_FRAME    = (0.07, 0.065, 0.060, 1.00)
COL_DASH     = (0.09, 0.085, 0.075, 1.00)
COL_LEATHER  = (0.16, 0.120, 0.085, 1.00)
COL_CHROME   = (0.52, 0.480, 0.420, 1.00)
COL_GAUGE_BG = (0.050, 0.045, 0.040, 1.00)
COL_SKIN     = (0.83, 0.630, 0.460, 1.00)
COL_SLEEVE   = (0.18, 0.150, 0.130, 1.00)
COL_WHEEL    = (0.10, 0.085, 0.075, 1.00)


def _col3(t):
    return t[0], t[1], t[2]




def _filled_rect(x, y, w, h, col):
    glColor4f(*col) if len(col) == 4 else glColor3f(*col)
    glBegin(GL_QUADS)
    glVertex2f(x, y);         glVertex2f(x + w, y)
    glVertex2f(x + w, y + h); glVertex2f(x, y + h)
    glEnd()


def _filled_circle(cx, cy, r, col, n=40):
    glColor4f(*col) if len(col) == 4 else glColor3f(*col)
    glBegin(GL_POLYGON)
    for i in range(n):
        a = 2 * math.pi * i / n
        glVertex2f(cx + r * math.cos(a), cy + r * math.sin(a))
    glEnd()


def _ring(cx, cy, r_out, r_in, col, n=60):
    glColor4f(*col) if len(col) == 4 else glColor3f(*col)
    glBegin(GL_QUAD_STRIP)
    for i in range(n + 1):
        a = 2 * math.pi * i / n
        glVertex2f(cx + r_out * math.cos(a), cy + r_out * math.sin(a))
        glVertex2f(cx + r_in  * math.cos(a), cy + r_in  * math.sin(a))
    glEnd()


def _polygon(pts, col):
    glColor4f(*col) if len(col) == 4 else glColor3f(*col)
    glBegin(GL_POLYGON)
    for x, y in pts:
        glVertex2f(x, y)
    glEnd()


def _line(x0, y0, x1, y1, col, width=1.0):
    glColor4f(*col) if len(col) == 4 else glColor3f(*col)
    glLineWidth(width)
    glBegin(GL_LINES)
    glVertex2f(x0, y0); glVertex2f(x1, y1)
    glEnd()
    glLineWidth(1.0)



# Arco: de 225° (izq, 7h) a -45° (der, 5h) = 270° de barrido
ARC_START = 225   # grados
ARC_SWEEP = 270   # grados totales


def _draw_analog_gauge(cx, cy, r, value, max_val, labels, unit,
                       gauge_font, color_zones=True, red_zone_ratio=0.78):
    """
    Instrumento analógico con números visibles.

    Parámetros:
        cx, cy       : centro del instrumento en píxeles
        r            : radio en píxeles
        value        : valor actual
        max_val      : valor máximo (fondo de escala)
        labels       : lista de valores donde poner números, ej: [0,20,40,60,80]
        unit         : cadena de unidad, ej: "km/h"
        gauge_font   : pygame.font para los números
        color_zones  : True = arco con colores verde/amarillo/rojo
        red_zone_ratio: fracción del arco donde empieza la zona roja
    """
    # ── Fondo ────────────────────────────────────────────────────────────
    _filled_circle(cx, cy, r, COL_GAUGE_BG)

    # Aro cromo exterior
    _ring(cx, cy, r, r * 0.94, COL_CHROME)

    # ── Arco de color ────────────────────────────────────────────────────
    arc_n = 90
    r_in  = r * 0.80
    r_out = r * 0.92
    for i in range(arc_n):
        t0 = i / arc_n
        t1 = (i + 1) / arc_n
        a0 = math.radians(ARC_START - t0 * ARC_SWEEP)
        a1 = math.radians(ARC_START - t1 * ARC_SWEEP)

        if color_zones:
            if t0 < 0.55:
                c = (0.08, 0.78, 0.22)
            elif t0 < red_zone_ratio:
                c = (0.90, 0.72, 0.04)
            else:
                c = (0.88, 0.08, 0.05)
        else:
            c = (0.28, 0.52, 0.90)

        glColor3f(*c)
        glBegin(GL_QUADS)
        glVertex2f(cx + r_in  * math.cos(a0), cy + r_in  * math.sin(a0))
        glVertex2f(cx + r_out * math.cos(a0), cy + r_out * math.sin(a0))
        glVertex2f(cx + r_out * math.cos(a1), cy + r_out * math.sin(a1))
        glVertex2f(cx + r_in  * math.cos(a1), cy + r_in  * math.sin(a1))
        glEnd()

    # ── Marcas de escala ─────────────────────────────────────────────────
    label_set = set(labels)
    # Marcas menores cada step_minor
    step_minor = max_val / 40
    v = 0
    while v <= max_val + 0.01:
        t = v / max_val
        a = math.radians(ARC_START - t * ARC_SWEEP)
        is_major = any(abs(v - lv) < step_minor * 0.6 for lv in labels)
        ri = r * (0.70 if is_major else 0.78)
        ro = r * 0.80
        glColor3f(0.80 if is_major else 0.50,
                  0.80 if is_major else 0.50,
                  0.80 if is_major else 0.50)
        glLineWidth(2.5 if is_major else 1.0)
        glBegin(GL_LINES)
        glVertex2f(cx + ri * math.cos(a), cy + ri * math.sin(a))
        glVertex2f(cx + ro * math.cos(a), cy + ro * math.sin(a))
        glEnd()
        v += step_minor
    glLineWidth(1.0)

    # ── Números de la escala ─────────────────────────────────────────────
    # Los números se posicionan ligeramente hacia adentro del arco
    # Usamos draw_text con anchor="center"
    num_r = r * 0.60   # radio donde van los números
    for lv in labels:
        t = lv / max_val
        a = math.radians(ARC_START - t * ARC_SWEEP)
        nx = cx + num_r * math.cos(a)
        ny = cy + num_r * math.sin(a)
        label_str = str(int(lv)) if lv < 1000 else f"{int(lv//1000)}k"
        draw_text(nx, ny, label_str, gauge_font,
                  color=(200, 205, 200), anchor="center")

    # ── Unidad debajo del centro ─────────────────────────────────────────
    draw_text(cx, cy - r * 0.28, unit, gauge_font,
              color=(140, 148, 145), anchor="center")

    # ── Aguja ────────────────────────────────────────────────────────────
    norm = min(max(value / max_val, 0.0), 1.0)
    needle_a = math.radians(ARC_START - norm * ARC_SWEEP)
    nl = r * 0.72

    # Sombra
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(0, 0, 0, 0.35)
    glLineWidth(5)
    glBegin(GL_LINES)
    glVertex2f(cx + 2, cy - 2)
    glVertex2f(cx + 2 + nl * math.cos(needle_a), cy - 2 + nl * math.sin(needle_a))
    glEnd()
    glDisable(GL_BLEND)

    # Aguja (roja)
    glColor3f(0.96, 0.14, 0.04)
    glLineWidth(3)
    glBegin(GL_LINES)
    glVertex2f(cx, cy)
    glVertex2f(cx + nl * math.cos(needle_a), cy + nl * math.sin(needle_a))
    glEnd()
    # Cola
    glColor3f(0.38, 0.35, 0.32)
    glLineWidth(2)
    glBegin(GL_LINES)
    glVertex2f(cx, cy)
    glVertex2f(cx - nl * 0.18 * math.cos(needle_a),
               cy - nl * 0.18 * math.sin(needle_a))
    glEnd()
    glLineWidth(1)

    # Pivote central
    _filled_circle(cx, cy, r * 0.10, (0.20, 0.18, 0.16))
    _filled_circle(cx, cy, r * 0.055, COL_CHROME)


# ─────────────────────────────────────────────────────────────────────────────
# TABLERO INFERIOR
# ─────────────────────────────────────────────────────────────────────────────

def _draw_dashboard(W, H, speed_kmh, rpm_val, is_braking, fonts):
    """
    Tablero inferior (22% inferior de la pantalla).
    Contiene velocímetro analógico con números, RPM, y pantalla LCD central.
    """
    dash_h = int(H * 0.22)

    # Fondo trapezoidal del tablero
    _polygon([
        (0, 0), (W, 0), (W, dash_h), (0, dash_h)
    ], COL_DASH)

    # Franja de cuero en el borde superior
    _filled_rect(0, dash_h - 2, W, 10, COL_LEATHER)

    # Degradado de luz en la parte superior del tablero
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glBegin(GL_QUADS)
    glColor4f(0.45, 0.38, 0.28, 0.40)
    glVertex2f(0, dash_h + 8);  glVertex2f(W, dash_h + 8)
    glColor4f(0.45, 0.38, 0.28, 0.0)
    glVertex2f(W, dash_h + 38); glVertex2f(0, dash_h + 38)
    glEnd()
    glDisable(GL_BLEND)

    # ── VELOCÍMETRO (izquierdo) ──────────────────────────────────────────
    spd_cx = int(W * 0.215)
    spd_cy = int(dash_h * 0.45)
    spd_r  = int(min(dash_h * 0.82, W * 0.095))

    _draw_analog_gauge(
        cx=spd_cx, cy=spd_cy, r=spd_r,
        value=speed_kmh, max_val=80,
        labels=[0, 20, 40, 60, 80],
        unit="km/h",
        gauge_font=fonts['gauge'],
        color_zones=True,
        red_zone_ratio=0.78,
    )

    # ── RPM / TACÓMETRO (derecho) ────────────────────────────────────────
    rpm_cx = int(W * 0.785)
    rpm_cy = spd_cy
    rpm_r  = spd_r

    _draw_analog_gauge(
        cx=rpm_cx, cy=rpm_cy, r=rpm_r,
        value=rpm_val, max_val=8000,
        labels=[0, 2000, 4000, 6000, 8000],
        unit="RPM",
        gauge_font=fonts['gauge'],
        color_zones=True,
        red_zone_ratio=0.80,
    )

    # ── PANTALLA LCD CENTRAL ─────────────────────────────────────────────
    lcd_w = int(W * 0.20)
    lcd_h = int(dash_h * 0.55)
    lcd_x = W // 2 - lcd_w // 2
    lcd_y = int(dash_h * 0.18)

    # Marco
    _filled_rect(lcd_x - 5, lcd_y - 5, lcd_w + 10, lcd_h + 10,
                 (0.07, 0.065, 0.06))
    # Fondo LCD
    _filled_rect(lcd_x, lcd_y, lcd_w, lcd_h, (0.025, 0.07, 0.035))

    # Velocidad digital grande en el LCD
    spd_text = f"{int(speed_kmh):3d}"
    draw_text(lcd_x + lcd_w//2, lcd_y + lcd_h - 6,
              spd_text, fonts['lcd_num'],
              color=(60, 230, 80), anchor="topcenter")

    draw_text(lcd_x + lcd_w//2, lcd_y + 10,
              "km/h", fonts['gauge'],
              color=(45, 160, 55), anchor="bottomcenter")

    # Barras de temperatura y combustible
    _draw_lcd_bars(lcd_x, lcd_y, lcd_w, lcd_h, speed_kmh, fonts)

    # ── INDICADOR DE FRENO ───────────────────────────────────────────────
    if is_braking:
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.70, 0.04, 0.02, 0.12)
        glBegin(GL_QUADS)
        glVertex2f(0, 0); glVertex2f(W, 0)
        glVertex2f(W, dash_h + 20); glVertex2f(0, dash_h + 20)
        glEnd()
        glDisable(GL_BLEND)


def _draw_lcd_bars(lx, ly, lw, lh, speed, fonts):
    """Barras de temperatura y combustible con etiquetas."""
    bar_w  = lw * 0.80
    bar_h  = 7
    bx     = lx + lw * 0.10
    label_x = lx + lw * 0.06

    # Temperatura (fija ~62%)
    temp_ratio = 0.62
    _filled_rect(bx, ly + lh * 0.72, bar_w, bar_h, (0.04, 0.09, 0.045))
    _filled_rect(bx, ly + lh * 0.72, bar_w * temp_ratio, bar_h,
                 (0.10, 0.80, 0.28))
    draw_text(lx + lw//2, ly + lh * 0.72 + bar_h + 1,
              "TEMP", fonts['lcd_label'],
              color=(45, 160, 55), anchor="bottomcenter")

    # Combustible (baja con la velocidad)
    fuel = max(0.04, 1.0 - speed / 220.0)
    fuel_col = (0.90, 0.55, 0.04) if fuel > 0.25 else (0.90, 0.10, 0.04)
    _filled_rect(bx, ly + lh * 0.48, bar_w, bar_h, (0.04, 0.09, 0.045))
    _filled_rect(bx, ly + lh * 0.48, bar_w * fuel, bar_h, fuel_col)
    draw_text(lx + lw//2, ly + lh * 0.48 + bar_h + 1,
              "COMB", fonts['lcd_label'],
              color=(45, 160, 55), anchor="bottomcenter")


# ─────────────────────────────────────────────────────────────────────────────
# MARCO DEL PARABRISAS
# ─────────────────────────────────────────────────────────────────────────────

def _draw_windshield_frame(W, H):
    """Marco negro del parabrisas: techo, pilares A y espejos."""
    F = COL_FRAME

    # Techo
    _filled_rect(0, H * 0.78, W, H * 0.22, F)

    # Pilar A izquierdo (trapezoidal)
    _polygon([(0, 0), (W*0.148, 0), (W*0.118, H*0.78), (0, H*0.78)], F)
    _polygon([
        (W*0.143, 0), (W*0.158, 0),
        (W*0.128, H*0.78), (W*0.113, H*0.78),
    ], COL_LEATHER)

    # Pilar A derecho
    _polygon([(W, 0), (W*0.852, 0), (W*0.882, H*0.78), (W, H*0.78)], F)
    _polygon([
        (W*0.857, 0), (W*0.842, 0),
        (W*0.872, H*0.78), (W*0.887, H*0.78),
    ], COL_LEATHER)

    # Degradado oscuro del techo sobre el parabrisas
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glBegin(GL_QUADS)
    glColor4f(0.05, 0.048, 0.044, 0.92)
    glVertex2f(W * 0.118, H * 0.78); glVertex2f(W * 0.882, H * 0.78)
    glColor4f(0.05, 0.048, 0.044, 0.0)
    glVertex2f(W * 0.80, H * 0.67);  glVertex2f(W * 0.20, H * 0.67)
    glEnd()
    glDisable(GL_BLEND)

    _draw_rearview_mirror(W, H)
    _draw_side_mirror(W, H, -1)
    _draw_side_mirror(W, H,  1)


def _draw_rearview_mirror(W, H):
    mx  = W * 0.5
    my  = H * 0.790
    mw  = W * 0.190
    mh  = H * 0.062

    # Soporte
    _line(mx, my + mh, mx, my + mh + H * 0.028, (0.14, 0.12, 0.10), 3)

    # Marco
    _filled_rect(mx - mw/2 - 5, my - 4, mw + 10, mh + 8, (0.09, 0.08, 0.07))

    # Cielo
    _filled_rect(mx - mw/2, my + mh/2, mw, mh/2, (0.44, 0.60, 0.82))
    # Asfalto
    _filled_rect(mx - mw/2, my, mw, mh/2, (0.34, 0.34, 0.37))

    # Carretera en perspectiva
    rb, rt = mw * 0.30, mw * 0.12
    _polygon([
        (mx - rb/2, my), (mx + rb/2, my),
        (mx + rt/2, my + mh/2), (mx - rt/2, my + mh/2),
    ], (0.40, 0.40, 0.44))

    # Líneas de carril
    for xoff in [-mw*0.04, mw*0.04]:
        _line(mx + xoff, my + mh*0.07,
              mx + xoff*0.38, my + mh*0.48,
              (0.86, 0.86, 0.86), 1.4)

    # Borde cromo
    glColor3f(*_col3(COL_CHROME))
    glLineWidth(2.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(mx - mw/2, my);      glVertex2f(mx + mw/2, my)
    glVertex2f(mx + mw/2, my + mh); glVertex2f(mx - mw/2, my + mh)
    glEnd()
    glLineWidth(1.0)


def _draw_side_mirror(W, H, side):
    cx = W * 0.158 if side == -1 else W * 0.842
    cy = H * 0.520
    mw = W * 0.10
    mh = H * 0.078

    _filled_rect(cx - mw/2 - 3, cy - 3, mw + 6, mh + 6, (0.08, 0.07, 0.065))
    _filled_rect(cx - mw/2, cy + mh/2, mw, mh/2, (0.44, 0.60, 0.82))
    _filled_rect(cx - mw/2, cy, mw, mh/2, (0.34, 0.34, 0.37))
    rb, rt = mw * 0.34, mw * 0.14
    _polygon([
        (cx - rb/2, cy), (cx + rb/2, cy),
        (cx + rt/2, cy + mh/2), (cx - rt/2, cy + mh/2),
    ], (0.38, 0.38, 0.42))
    glColor3f(*_col3(COL_CHROME))
    glLineWidth(1.5)
    glBegin(GL_LINE_LOOP)
    glVertex2f(cx - mw/2, cy);      glVertex2f(cx + mw/2, cy)
    glVertex2f(cx + mw/2, cy + mh); glVertex2f(cx - mw/2, cy + mh)
    glEnd()
    glLineWidth(1.0)


# ─────────────────────────────────────────────────────────────────────────────
# VOLANTE
# ─────────────────────────────────────────────────────────────────────────────

def _draw_steering_wheel(W, H, steer_norm, bob_phase):
    dash_h = int(H * 0.22)
    wCx    = int(W * 0.415)
    wCy    = dash_h + int(H * 0.125)
    wR     = int(min(H * 0.172, W * 0.118))

    wCy += int(math.sin(bob_phase) * wR * 0.04)

    rot_deg = steer_norm * 40.0

    glPushMatrix()
    glTranslatef(wCx, wCy, 0)
    glRotatef(rot_deg, 0, 0, 1)

    # Sombra
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    _ring_alpha(0, -5, wR * 1.06, wR * 0.70, (0, 0, 0, 0.40))
    glDisable(GL_BLEND)

    # Aro exterior (cuero)
    _ring(0, 0, wR, wR * 0.76, (0.09, 0.075, 0.065))

    # Detalle de costura dorada
    _ring(0, 0, wR * 0.88, wR * 0.865, (0.48, 0.36, 0.14))

    # Aro cromo interior
    _ring(0, 0, wR * 0.76, wR * 0.72, COL_CHROME)

    # 3 radios
    for ang in [90, 210, 330]:
        a = math.radians(ang)
        x0, y0 = wR * 0.22 * math.cos(a), wR * 0.22 * math.sin(a)
        x1, y1 = wR * 0.96 * math.cos(a), wR * 0.96 * math.sin(a)
        glColor3f(0.10, 0.088, 0.075)
        glLineWidth(10)
        glBegin(GL_LINES); glVertex2f(x0, y0); glVertex2f(x1, y1); glEnd()
        glColor3f(0.32, 0.28, 0.22)
        glLineWidth(3)
        glBegin(GL_LINES); glVertex2f(x0, y0); glVertex2f(x1, y1); glEnd()
    glLineWidth(1)

    # Hub central
    _filled_circle(0, 0, wR * 0.22, (0.13, 0.11, 0.095))
    _filled_circle(0, 0, wR * 0.16, (0.36, 0.28, 0.20))
    _filled_circle(0, 0, wR * 0.09, (0.78, 0.62, 0.10))
    _filled_circle(0, 0, wR * 0.04, (0.06, 0.055, 0.050))

    glPopMatrix()

    # Manos (sin rotación del volante)
    _draw_hand(wCx, wCy, wR, steer_norm, -1)
    _draw_hand(wCx, wCy, wR, steer_norm,  1)


def _ring_alpha(cx, cy, r_out, r_in, col_rgba, n=48):
    glColor4f(*col_rgba)
    glBegin(GL_QUAD_STRIP)
    for i in range(n + 1):
        a = 2 * math.pi * i / n
        glVertex2f(cx + r_out * math.cos(a), cy + r_out * math.sin(a))
        glVertex2f(cx + r_in  * math.cos(a), cy + r_in  * math.sin(a))
    glEnd()


def _draw_hand(wCx, wCy, wR, steer_norm, side):
    base_ang = 210 if side == -1 else 330
    base_ang += steer_norm * 40.0
    a = math.radians(base_ang)
    hx = wCx + wR * 0.87 * math.cos(a)
    hy = wCy + wR * 0.87 * math.sin(a)
    hw, hh = wR * 0.22, wR * 0.40

    glPushMatrix()
    glTranslatef(hx, hy, 0)
    glRotatef(base_ang + 90, 0, 0, 1)

    _filled_rect(-hw*0.5, -hh*0.70, hw, hh*0.30, COL_SLEEVE)
    _filled_rect(-hw*0.5, -hh*0.40, hw, hh*0.62, COL_SKIN)
    _line(-hw*0.45, -hh*0.05, hw*0.45, -hh*0.05, (0.70, 0.52, 0.38), 1.2)
    _filled_rect(-hw*0.5, hh*0.18, hw, hh*0.10, (0.72, 0.54, 0.40))

    fw, fh = hw * 0.18, hh * 0.32
    for fi in range(4):
        fx = -hw*0.38 + fi * fw * 1.18
        _filled_rect(fx, hh*0.25, fw*0.85, fh*0.50, COL_SKIN)
        _filled_rect(fx, hh*0.25+fh*0.48, fw*0.85, fh*0.08, (0.68, 0.50, 0.36))
        _filled_rect(fx+fw*0.05, hh*0.25+fh*0.54, fw*0.75, fh*0.44, COL_SKIN)
        _filled_rect(fx+fw*0.08, hh*0.25+fh*0.70, fw*0.60, fh*0.24, (0.80, 0.65, 0.58))

    tx = hw*0.36 if side == 1 else -hw*0.52
    _polygon([
        (tx, -hh*0.10), (tx+hw*0.22*side, -hh*0.18),
        (tx+hw*0.20*side, hh*0.18), (tx, hh*0.14),
    ], COL_SKIN)

    glPopMatrix()




def draw_cabin_2d(screen_w, screen_h, steer_norm, speed_kmh, rpm_val,
                  is_braking, bob_phase, fonts):
    """
    Dibuja la cabina completa en modo 2D.
    Llamar DESPUÉS de draw_full_scene() y ANTES de begin_2d() del HUD.

    Parámetros nuevos vs v2:
        rpm_val  : valor de RPM (calculado en simulador.py)
        fonts    : diccionario de fuentes con claves:
                   'gauge', 'lcd_num', 'lcd_label'
    """
    W, H = screen_w, screen_h

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, W, 0, H, -1, 1)   # Y=0 abajo

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_FOG)

    # Dibujar en orden (de atrás hacia adelante)
    _draw_dashboard(W, H, speed_kmh, rpm_val, is_braking, fonts)
    _draw_steering_wheel(W, H, steer_norm, bob_phase)
    _draw_windshield_frame(W, H)

    # Restaurar
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_FOG)

    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
