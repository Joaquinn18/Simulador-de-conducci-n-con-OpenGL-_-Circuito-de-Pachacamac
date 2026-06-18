
import math
import pygame
from OpenGL.GL import *
from text_renderer import draw_text


# ─────────────────────────────────────────────────────────────────────────────
# MODO 2D
# ─────────────────────────────────────────────────────────────────────────────

def begin_2d(W, H):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix(); glLoadIdentity()
    glOrtho(0, W, 0, H, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix(); glLoadIdentity()
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_FOG)


def end_2d():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_FOG)
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW);  glPopMatrix()


# ─────────────────────────────────────────────────────────────────────────────
# PRIMITIVAS 2D
# ─────────────────────────────────────────────────────────────────────────────

def _rect(x, y, w, h, col):
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(*col)
    glBegin(GL_QUADS)
    glVertex2f(x, y); glVertex2f(x+w, y)
    glVertex2f(x+w, y+h); glVertex2f(x, y+h)
    glEnd(); glDisable(GL_BLEND)


def _border(x, y, w, h, col, lw=1.5):
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(*col); glLineWidth(lw)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x, y); glVertex2f(x+w, y)
    glVertex2f(x+w, y+h); glVertex2f(x, y+h)
    glEnd(); glLineWidth(1.0); glDisable(GL_BLEND)


def _rrect(x, y, w, h, col, r=8):
    """Rectángulo con esquinas redondeadas."""
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(*col)
    # Centro + 2 laterales
    glBegin(GL_QUADS)
    glVertex2f(x+r,y); glVertex2f(x+w-r,y)
    glVertex2f(x+w-r,y+h); glVertex2f(x+r,y+h)
    glEnd()
    glBegin(GL_QUADS)
    glVertex2f(x,y+r); glVertex2f(x+r,y+r)
    glVertex2f(x+r,y+h-r); glVertex2f(x,y+h-r)
    glEnd()
    glBegin(GL_QUADS)
    glVertex2f(x+w-r,y+r); glVertex2f(x+w,y+r)
    glVertex2f(x+w,y+h-r); glVertex2f(x+w-r,y+h-r)
    glEnd()
    for cx,cy,a0,a1 in [
        (x+r,   y+r,   math.pi,     1.5*math.pi),
        (x+w-r, y+r,   1.5*math.pi, 2*math.pi),
        (x+w-r, y+h-r, 0,           .5*math.pi),
        (x+r,   y+h-r, .5*math.pi,  math.pi),
    ]:
        glBegin(GL_POLYGON); glVertex2f(cx,cy)
        for i in range(9):
            a = a0+(a1-a0)*i/8
            glVertex2f(cx+r*math.cos(a), cy+r*math.sin(a))
        glEnd()
    glDisable(GL_BLEND)


def _circle(cx, cy, r, col, n=24):
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(*col)
    glBegin(GL_POLYGON)
    for i in range(n):
        a = 2*math.pi*i/n
        glVertex2f(cx+r*math.cos(a), cy+r*math.sin(a))
    glEnd(); glDisable(GL_BLEND)


# ─────────────────────────────────────────────────────────────────────────────
# PANEL DE GUÍA LATERAL  (ocultable con H)
# ─────────────────────────────────────────────────────────────────────────────
# Layout: panel fijo en lado derecho, debajo de penalización
# Muestra: nombre del CP actual, instrucción, detalle, tecla H para ocultar

def draw_guide_panel(W, H, cp_dict, guide_visible, cp_done, fonts):
    """
    Panel lateral derecho con la instrucción del CP actual.
    Si guide_visible=False sólo muestra un botón pequeño [H] para reabrirlo.
    cp_done: lista de bool para la barra de progreso interna.
    """
    # Posición: lado derecho, debajo del panel de penalización
    pen_h  = int(H * 0.115)
    pw     = int(W * 0.22)
    pad    = 10
    margin = 12
    px     = W - pw - margin

    if not guide_visible:
        # Botón compacto: sólo muestra "[H] Guía"
        btn_h = 28
        btn_y = H - pen_h - margin - btn_h - 4
        _rrect(px, btn_y, pw, btn_h, (0.04, 0.06, 0.10, 0.88), r=6)
        _border(px, btn_y, pw, btn_h, (0.30, 0.35, 0.45, 0.80), 1.2)
        draw_text(px + pw//2, btn_y + btn_h - 5,
                  "[H]  Mostrar guia", fonts['label'],
                  color=(140, 160, 175), anchor="topcenter")
        return

    # Panel completo
    col    = cp_dict.get("color", (0.30, 0.65, 0.95))
    r, g, b = col
    title_col = (min(255,int(r*310)), min(255,int(g*310)), min(255,int(b*310)))

    # Calcular altura necesaria: título + línea + tip + detalle + barra progreso + btn ocultar
    line_h = max(15, int(H * 0.022))
    ph = line_h * 6 + pad * 3 + 20

    py = H - pen_h - margin - ph - 4
    if py < int(H * 0.25):   # no tapar la escena en pantallas muy pequeñas
        py = int(H * 0.25)

    # Fondo
    _rrect(px, py, pw, ph, (0.04, 0.06, 0.10, 0.93), r=10)
    # Franja de color izquierda
    _rrect(px, py, 5, ph, (r, g, b, 1.0), r=3)
    # Borde sutil
    _border(px, py, pw, ph, (r*0.5, g*0.5, b*0.5, 0.60), 1.2)

    cx = px + pw // 2
    ty = py + ph - pad

    # Título CP
    draw_text(cx, ty, cp_dict["name"], fonts['title'],
              color=title_col, anchor="topcenter")
    ty -= line_h + 4

    # Separador
    _rect(px+10, ty, pw-20, 1, (r, g, b, 0.40))
    ty -= 6

    # Instrucción principal
    # Partido en 2 líneas si es muy largo (>35 chars)
    tip = cp_dict.get("tip","")
    if len(tip) > 36:
        mid = tip[:36].rfind(' ')
        if mid < 20: mid = 36
        lines = [tip[:mid], tip[mid:].strip()]
    else:
        lines = [tip]
    for line in lines:
        draw_text(cx, ty, line, fonts['body'],
                  color=(215, 222, 215), anchor="topcenter")
        ty -= line_h + 2

    ty -= 2
    # Detalle pequeño
    detail = cp_dict.get("detail","")
    if len(detail) > 38:
        mid = detail[:38].rfind('|')
        if mid < 5: mid = 38
        dlines = [detail[:mid].strip(), detail[mid:].strip().lstrip('|').strip()]
    else:
        dlines = [detail]
    for dl in dlines:
        draw_text(cx, ty, dl, fonts['small'],
                  color=(140, 148, 145), anchor="topcenter")
        ty -= line_h

    ty -= 4
    # Barra de progreso de checkpoints (compacta)
    n_cp  = len(cp_done)
    done  = sum(1 for d in cp_done if d)
    dr    = max(5, int(H * 0.008))
    gap   = max(10, int(pw / (n_cp + 1)))
    total_w_dots = n_cp * dr*2 + (n_cp-1) * gap
    sx = cx - total_w_dots//2
    for i in range(n_cp):
        dcx = sx + i*(dr*2+gap) + dr
        dcy = ty - dr
        _circle(dcx, dcy, dr, (0.15,0.82,0.30,0.95) if cp_done[i] else (0.18,0.20,0.26,0.85))
        if cp_done[i]:
            _border(dcx-dr, dcy-dr, dr*2, dr*2, (0.20,0.95,0.40,0.85), 1.2)
        draw_text(dcx, dcy+dr, str(i+1), fonts['label'],
                  color=(200,235,200) if cp_done[i] else (100,108,118), anchor="topcenter")
    draw_text(cx + total_w_dots//2 + 10, ty - dr,
              f"{done}/{n_cp}", fonts['label'],
              color=(150,158,155), anchor="midleft")

    # Botón [H] ocultar en la parte inferior
    ty -= dr*2 + 8
    draw_text(cx, ty, "[H] Ocultar", fonts['label'],
              color=(90, 100, 110), anchor="topcenter")


# ─────────────────────────────────────────────────────────────────────────────
# PANEL DE PENALIZACIÓN  (esquina superior derecha, siempre visible)
# ─────────────────────────────────────────────────────────────────────────────

def draw_penalty_hud(W, H, penalty_pts, cones_hit, fonts, tick):
    pw = int(W * 0.22)
    ph = int(H * 0.115)
    px = W - pw - 12
    py = H - ph - 12

    danger = 2 if penalty_pts >= 40 else 1 if penalty_pts >= 25 else 0
    bgs = [(0.04,0.05,0.09,0.88),(0.28,0.14,0.02,0.92),(0.42,0.04,0.02,0.95)]
    _rrect(px, py, pw, ph, bgs[danger], r=10)
    if danger == 2 and (tick//15)%2==0:
        _border(px, py, pw, ph, (0.95,0.10,0.05,0.90), 2)
    elif danger == 1:
        _border(px, py, pw, ph, (0.90,0.55,0.05,0.70), 1.5)

    cx = px + pw//2
    draw_text(cx, py+ph-6, "PENALIZACION", fonts['label'],
              color=(150,155,165), anchor="topcenter")
    pen_col = [(230,60,50),(255,165,45),(255,65,50)][danger]
    draw_text(cx, py+ph//2+2, f"{penalty_pts} pts", fonts['big_num'],
              color=pen_col, anchor="topcenter")
    cone_col = (195,135,55) if cones_hit>0 else (120,128,135)
    draw_text(cx, py+8, f"Conos: {cones_hit}  |  Max: 50 pts",
              fonts['small'], color=cone_col, anchor="bottomcenter")
    # Barra progreso penalización
    bx, bw = px+12, pw-24
    ratio = min(penalty_pts/50.0, 1.0)
    fill_col = [(0.85,0.10,0.08,1.0),(0.88,0.58,0.04,1.0),(0.88,0.10,0.04,1.0)][danger]
    _rect(bx, py+4, bw, 5, (0.08,0.09,0.12,1.0))
    if ratio > 0:
        _rect(bx, py+4, int(bw*ratio), 5, fill_col)


# ─────────────────────────────────────────────────────────────────────────────
# FEEDBACK  —  un solo mensaje a la vez, centrado, bien visible
# ─────────────────────────────────────────────────────────────────────────────

def draw_feedback_flash(W, H, feedbacks, fonts):
    """
    Muestra el feedback más reciente activo en el centro-inferior de la
    pantalla (justo encima del tablero). Un solo mensaje a la vez para
    evitar superposiciones. El mensaje permanece visible más tiempo y hace
    fade-out suave al final.
    """
    if not feedbacks:
        return

    # Sólo el más reciente (último de la lista)
    fb = feedbacks[-1]
    if not fb.active:
        return

    dash_h = int(H * 0.22)
    msg_h  = max(32, int(H * 0.052))
    pw     = int(W * 0.50)
    px     = W//2 - pw//2
    py     = H - 12 - msg_h

    alpha  = fb.alpha
    r_col, g_col, b_col = [c/255.0 for c in fb.color]

    # Fondo con borde de color
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(0.04, 0.05, 0.09, 0.90 * alpha)
    glBegin(GL_QUADS)
    glVertex2f(px,py); glVertex2f(px+pw,py)
    glVertex2f(px+pw,py+msg_h); glVertex2f(px,py+msg_h)
    glEnd()
    glColor4f(r_col, g_col, b_col, 0.85 * alpha)
    glLineWidth(2.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(px,py); glVertex2f(px+pw,py)
    glVertex2f(px+pw,py+msg_h); glVertex2f(px,py+msg_h)
    glEnd()
    glLineWidth(1.0); glDisable(GL_BLEND)

    draw_text(W//2, py+msg_h-6, fb.text, fonts['feedback'],
              color=fb.color, anchor="topcenter", alpha=alpha)


# ─────────────────────────────────────────────────────────────────────────────
# INDICADOR DE ZONA BLOQUEADA
# ─────────────────────────────────────────────────────────────────────────────

def draw_zone_barrier(W, H, barrier_msg, fonts, tick):
    """
    Cuando el vehículo intenta avanzar a una zona no desbloqueada,
    muestra una pantalla de aviso prominente en el centro.
    barrier_msg: string con el mensaje, o None si no hay barrera activa.
    """
    if not barrier_msg:
        return

    # Overlay rojo pulsante en los bordes
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    pulse = 0.22 + 0.10 * math.sin(tick * 0.20)
    for bx, bw in [(0, W*0.055), (W*0.945, W*0.055)]:
        glColor4f(0.88, 0.05, 0.02, pulse)
        glBegin(GL_QUADS)
        glVertex2f(bx,0); glVertex2f(bx+bw,0)
        glVertex2f(bx+bw,H); glVertex2f(bx,H)
        glEnd()
    glDisable(GL_BLEND)

    # Panel central de aviso
    pw, ph = int(W*0.52), int(H*0.18)
    px = W//2 - pw//2
    py = H//2 - ph//2
    _rrect(px, py, pw, ph, (0.60, 0.04, 0.02, 0.95), r=12)
    _border(px, py, pw, ph, (0.95, 0.10, 0.05, 0.95), 2.5)

    cx = W//2
    draw_text(cx, py+ph-10, "ZONA BLOQUEADA", fonts['title'],
              color=(255, 220, 60), anchor="topcenter")
    draw_text(cx, py+ph//2+4, barrier_msg, fonts['body'],
              color=(255, 240, 200), anchor="topcenter")
    draw_text(cx, py+12, "Completa la zona actual primero",
              fonts['small'], color=(210, 185, 155), anchor="bottomcenter")


# ─────────────────────────────────────────────────────────────────────────────
# VELOCÍMETRO DIGITAL
# ─────────────────────────────────────────────────────────────────────────────

def draw_speed_digital(W, H, speed_kmh, fonts):
    dash_h = int(H * 0.22)
    cx = int(W * 0.22)
    cy = dash_h + int(H * 0.07)
    pw = int(W * 0.10)
    ph = int(H * 0.075)
    px = cx - pw//2; py = cy - ph//2
    _rrect(px, py, pw, ph, (0.04,0.05,0.08,0.90), r=8)
    spd_col = (60,230,90) if speed_kmh < 40 else (255,200,50) if speed_kmh < 60 else (255,70,55)
    draw_text(cx, py+ph-6, f"{int(speed_kmh):3d}", fonts['speed_num'],
              color=spd_col, anchor="topcenter")
    draw_text(cx, py+10, "km/h", fonts['small'],
              color=(140,148,145), anchor="bottomcenter")


# ─────────────────────────────────────────────────────────────────────────────
# INDICADOR DE MARCHA
# ─────────────────────────────────────────────────────────────────────────────

def draw_gear_indicator(W, H, speed, is_reversing, fonts, gear=1, rpm=900):
    dash_h = int(H * 0.22)
    cx = int(W * 0.10)
    cy = dash_h + int(H * 0.07)
    pw = int(W * 0.07)
    ph = int(H * 0.075)
    px = cx - pw//2; py = cy - ph//2
    if gear == -1:
        letter, col, bg = "R", (255,80,60),   (0.28,0.05,0.04,0.92)
    elif gear == 0:
        letter, col, bg = "N", (220,200,80),  (0.20,0.18,0.02,0.92)
    else:
        letter = str(gear)
        if rpm > 5500:
            col, bg = (255,120,40), (0.24,0.10,0.02,0.92)
        else:
            col, bg = (60,210,90),  (0.04,0.18,0.06,0.92)
    _rrect(px, py, pw, ph, bg, r=8)
    draw_text(cx, py+ph-6, "MARCHA", fonts['label'], color=(140,148,145), anchor="topcenter")
    draw_text(cx, py+10, letter, fonts['big_num'], color=col, anchor="bottomcenter")


# ─────────────────────────────────────────────────────────────────────────────
# ADVERTENCIA DE CONO
# ─────────────────────────────────────────────────────────────────────────────

def draw_cone_warning(W, H, cone_nearby, fonts, tick):
    if not cone_nearby: return
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    pulse = 0.32 + 0.14*math.sin(tick*0.25)
    for bx, bw in [(0, W*0.06), (W*0.94, W*0.06)]:
        glColor4f(0.90,0.05,0.02,pulse)
        glBegin(GL_QUADS)
        glVertex2f(bx,0); glVertex2f(bx+bw,0)
        glVertex2f(bx+bw,H); glVertex2f(bx,H)
        glEnd()
    glDisable(GL_BLEND)
    ph = max(36, int(H*0.055))
    pw = int(W*0.38)
    py = int(H*0.76)-ph//2
    px = W//2-pw//2
    _rrect(px, py, pw, ph, (0.80,0.04,0.02,0.92), r=8)
    draw_text(W//2, py+ph-6, "!  CUIDADO — CONO CERCANO",
              fonts['warning'], color=(255,242,55), anchor="topcenter")


# ─────────────────────────────────────────────────────────────────────────────
# LEYENDA DE CONTROLES  (izquierda superior)
# ─────────────────────────────────────────────────────────────────────────────

def draw_controls_legend(W, H, fonts):
    lines = [
        ("W/UP",    "Acelerar"),
        ("S/DOWN",  "Frenar/Rev"),
        ("A/D",     "Girar"),
        ("Q",       "Subir marcha"),
        ("E",       "Bajar marcha"),
        ("ENTER",   "Confirmar estac."),
        ("H",       "Ocultar/mostrar guia"),
        ("F3",      "Rendimiento PC"),
        ("F11",     "Pantalla completa"),
        ("ESC",     "Salir"),
    ]
    lh  = max(16, int(H * 0.024))
    pad = 8
    pw  = int(W * 0.175)
    ph  = lh * len(lines) + pad*2 + lh
    px  = 10
    py  = H - ph - 10
    _rrect(px, py, pw, ph, (0.04,0.05,0.08,0.78), r=8)
    draw_text(px+pw//2, py+ph-pad, "CONTROLES", fonts['label'],
              color=(145,150,145), anchor="topcenter")
    for i,(key,desc) in enumerate(lines):
        ry = py+ph-pad-lh*(i+1)-4
        # Resaltar teclas de marcha en azul claro
        kcol = (130,200,255) if key in ("Q","E") else \
               (255,230,80)  if key == "ENTER"   else \
               (160,220,160) if key == "F3"      else (200,192,115)
        draw_text(px+10, ry+lh, key, fonts['small'], color=kcol, anchor="topleft")
        draw_text(px+int(pw*0.42), ry+lh, desc, fonts['small'],
                  color=(168,174,170), anchor="topleft")


# ─────────────────────────────────────────────────────────────────────────────
# MINIMAPA
# ─────────────────────────────────────────────────────────────────────────────

def draw_minimap(W, H, vehicle_x, vehicle_z, vehicle_angle, cp_done, fonts):
    """
    Minimapa con zonas coloreadas por estado:
      gris = asfalto normal
      amarillo = zona paralelo
      naranja  = zona diagonal
      verde claro = zona actual (próximo CP)
      verde oscuro = CP ya completado
    cp_done: lista de bool (6 elementos)
    """
    dash_h = int(H * 0.22)
    map_w, map_h = 155, 135
    pad = 8
    mx = W - map_w - 12
    my = dash_h + 12

    _rrect(mx, my, map_w, map_h, (0.04,0.06,0.10,0.92), r=7)
    _border(mx, my, map_w, map_h, (0.18,0.24,0.32,0.85), 1)
    draw_text(mx+map_w//2, my+map_h-4, "CIRCUITO - RUTA A",
              fonts['label'], color=(115,130,140), anchor="topcenter")

    wx0, wx1 = -53.0, 47.0
    wz0, wz1 = -45.0, 36.0
    dw = map_w - pad*2
    dh = map_h - pad*2 - 14
    sx = dw / (wx1-wx0)
    sz = dh / (wz1-wz0)

    def w2m(wx, wz):
        return mx+pad+(wx-wx0)*sx, my+pad+(wz-wz0)*sz

    # Césped
    tx, ty = w2m(wx0, wz0)
    _rect(tx, ty, dw, dh, (0.15,0.34,0.10,1.0))

    # Asfalto: mismas zonas que scene.py
    asp = (0.28,0.28,0.30,1.0)

    def road(x1,z1,x2,z2,col=None):
        ax,ay = w2m(x1,z1); bx,by = w2m(x2,z2)
        if bx>ax and by>ay:
            _rect(ax,ay,bx-ax,by-ay, col or asp)

    road(31,-45,46,35)
    road(-22,-45,46,-32)
    road(-53,-32,-32,22)
    road(-14,-9,38,8)
    road(-14,8,6,35)

    # Óvalo (círculo)
    ocx,ocy = w2m(-36.0, 10.0)
    or_out = 13.0*sx
    or_in  = 5.5*sx
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(*asp)
    glBegin(GL_POLYGON)
    for i in range(32):
        a = 2*math.pi*i/32
        glVertex2f(ocx+or_out*math.cos(a), ocy+or_out*math.sin(a))
    glEnd()
    glColor4f(0.15,0.40,0.10,1.0)
    glBegin(GL_POLYGON)
    for i in range(32):
        a = 2*math.pi*i/32
        glVertex2f(ocx+or_in*math.cos(a), ocy+or_in*math.sin(a))
    glEnd()
    glDisable(GL_BLEND)

    # Zonas con color según estado cp_done
    # CP0=start, CP1=trocha, CP2=paralelo, CP3=recta-O, CP4=ovalo, CP5=diagonal, CP6=salida
    # cp_done tiene 6 elementos: indices 0..5 = CP1..CP6
    zone_colors = {
        1: (0.55,0.48,0.02,0.80),   # paralelo: amarillo
        4: (0.55,0.28,0.02,0.75),   # diagonal: naranja
    }
    zone_done_col   = (0.10,0.50,0.18,0.65)
    zone_active_col = (0.15,0.70,0.30,0.50)

    def zone_col(eval_idx):
        """Color de relleno según si está done, activo o pendiente."""
        if eval_idx < len(cp_done) and cp_done[eval_idx]:
            return zone_done_col
        # Buscar si es el próximo activo
        for i,d in enumerate(cp_done):
            if not d:
                if i == eval_idx:
                    return zone_active_col
                break
        return zone_colors.get(eval_idx, asp)

    road(-20,-45,37,-36, zone_col(1))    # paralelo (cp_done[1])
    road(-14,-9,37,6, zone_col(4))       # diagonal (cp_done[4])

    # Línea de salida (roja)
    lx,ly = w2m(35,28); lx2,_ = w2m(46,28)
    _rect(lx, ly-1, lx2-lx, 2, (0.90,0.10,0.10,1.0))

    # Vehículo
    vx, vy = w2m(vehicle_x, vehicle_z)
    vx = max(mx+pad, min(mx+map_w-pad, vx))
    vy = max(my+pad, min(my+map_h-pad-14, vy))
    _circle(vx+1, vy-1, 5, (0,0,0,0.45))
    _circle(vx,   vy,   4, (0.12,0.92,0.28,1.0))

    # Flecha dirección
    am = math.radians(vehicle_angle)
    al = 10
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(1.0,1.0,1.0,0.92); glLineWidth(2.0)
    glBegin(GL_LINES)
    glVertex2f(vx, vy)
    glVertex2f(vx + al*math.sin(am)*sx/sx, vy + al*math.cos(am)*sz/sz)
    glEnd()
    glLineWidth(1.0); glDisable(GL_BLEND)


# ─────────────────────────────────────────────────────────────────────────────
# OVERLAY DE RENDIMIENTO  (F3)
# ─────────────────────────────────────────────────────────────────────────────

def _perf_bar(x, y, w, h, ratio, col_fill, label, val_txt, fonts):
    _rect(x, y, w, h, (0.06,0.07,0.10,1.0))
    _rect(x, y, max(2,int(w*min(ratio,1.0))), h, col_fill)
    _border(x, y, w, h, (0.18,0.20,0.26,0.90), 1.0)
    draw_text(x+5,   y+h, label,   fonts['small'], color=(140,148,158), anchor="bottomleft")
    draw_text(x+w-4, y+h, val_txt, fonts['small'], color=(210,218,225), anchor="bottomright")


def draw_perf_overlay(W, H, perf_data, fonts):
    pw=int(W*0.28); lh=max(16,int(H*0.026)); pad=10
    ph=lh*9+pad*3+14; px=pad; py=H-ph-pad
    _rrect(px,py,pw,ph,(0.03,0.04,0.09,0.93),r=10)
    _border(px,py,pw,ph,(0.28,0.35,0.48,0.90),1.8)
    cx=px+pw//2; bw=pw-pad*2-2; bh=max(8,int(lh*0.55))
    ty=py+ph-8
    draw_text(cx,ty,"RENDIMIENTO  [ F3 ]",fonts['label'],color=(170,185,200),anchor="topcenter")
    ty-=lh+4; _border(px+6,ty+lh-2,pw-12,1,(0.20,0.25,0.35,0.70),1.0); ty-=4
    # FPS
    fps=perf_data.get('fps',0.0); ft=perf_data.get('fps_target',60); fr=fps/max(ft,1)
    fc=(0.20,0.85,0.30,1.0) if fr>0.75 else (0.88,0.70,0.05,1.0) if fr>0.45 else (0.88,0.12,0.06,1.0)
    _perf_bar(px+pad,ty-bh,bw,bh,fr,fc,"FPS",f"{fps:.0f} / {ft}",fonts); ty-=lh
    # CPU
    cp=perf_data.get('cpu_pct',0.0)
    cc=(0.20,0.80,0.28,1.0) if cp<50 else (0.88,0.68,0.05,1.0) if cp<80 else (0.88,0.12,0.06,1.0)
    _perf_bar(px+pad,ty-bh,bw,bh,cp/100,cc,"CPU",f"{cp:.1f}%",fonts); ty-=lh
    # RAM
    rp=perf_data.get('ram_pct',0.0); rm=perf_data.get('ram_mb',0.0)
    rc=(0.20,0.80,0.28,1.0) if rp<60 else (0.88,0.68,0.05,1.0) if rp<85 else (0.88,0.12,0.06,1.0)
    _perf_bar(px+pad,ty-bh,bw,bh,rp/100,rc,"RAM",f"{rm:.0f} MB ({rp:.0f}%)",fonts); ty-=lh
    # GPU
    gp=perf_data.get('gpu_pct',-1); gv=perf_data.get('gpu_vram_mb',-1)
    if gp>=0:
        gc=(0.20,0.80,0.28,1.0) if gp<60 else (0.88,0.68,0.05,1.0) if gp<85 else (0.88,0.12,0.06,1.0)
        _perf_bar(px+pad,ty-bh,bw,bh,gp/100,gc,"GPU",
                  f"{gp:.0f}%  {gv:.0f}MB VRAM" if gv>=0 else f"{gp:.0f}%",fonts)
    else:
        _perf_bar(px+pad,ty-bh,bw,bh,0,(0.20,0.22,0.28,1.0),"GPU","No disponible",fonts)
    ty-=lh+4; _border(px+6,ty+lh,pw-12,1,(0.20,0.25,0.35,0.70),1.0); ty-=2
    mc=int(bw/6.5)
    for lbl,val in [("SO",  perf_data.get('os_name','—')),
                    ("CPU", perf_data.get('cpu_name','—')),
                    ("GPU", perf_data.get('gpu_name','—') or 'No detectada'),
                    ("RAM", f"{perf_data.get('ram_total',0.0):.1f} GB total")]:
        draw_text(px+pad+2, ty, lbl+":", fonts['small'], color=(145,158,170), anchor="topcenter")
        vd=val if len(val)<=mc else val[:mc-1]+"…"
        draw_text(px+pad+int(bw*0.28), ty, vd, fonts['small'], color=(200,210,220), anchor="topleft")
        ty-=lh


# ─────────────────────────────────────────────────────────────────────────────
# ESTACIONAMIENTO  (confirmar con ENTER)
# ─────────────────────────────────────────────────────────────────────────────

def parking_penalty_from_quality(quality):
    if quality >= 0.80: return 0
    if quality >= 0.60: return 5
    if quality >= 0.40: return 10
    return 15


def draw_parking_hud(W, H, parking_state, fonts):
    if not parking_state or not parking_state.get('active', False):
        return
    quality  = parking_state.get('quality',  0.0)
    in_slot  = parking_state.get('in_slot',  False)
    speed_ok = parking_state.get('speed_ok', False)
    angle_ok = parking_state.get('angle_ok', False)
    slot_lbl = parking_state.get('slot_label','—')
    pk_type  = parking_state.get('type',     'parallel')
    confirmed= parking_state.get('confirmed', False)
    penalty  = parking_penalty_from_quality(quality)

    pw=int(W*0.27); ph=int(H*0.23)
    px=W//2-pw//2;  py=H-ph-int(H*0.24)

    if quality>=0.80:   bc=(0.10,0.88,0.30,0.95); tc=(80,240,110)
    elif quality>=0.60: bc=(0.92,0.72,0.05,0.88); tc=(255,210,60)
    elif quality>=0.40: bc=(0.92,0.50,0.05,0.88); tc=(255,155,50)
    else:               bc=(0.90,0.12,0.06,0.88); tc=(255,75,55)

    _rrect(px,py,pw,ph,(0.03,0.04,0.08,0.93),r=10)
    _border(px,py,pw,ph,bc,2.0)
    cx=px+pw//2; lh=max(16,int(H*0.024))
    tn="PARALELO" if pk_type=='parallel' else "DIAGONAL"
    draw_text(cx,py+ph-7,f"ESTACIONAMIENTO {tn}",
              fonts['label'],color=(155,165,175),anchor="topcenter")
    draw_text(cx,py+ph-7-lh-2,slot_lbl,fonts['title'],color=tc,anchor="topcenter")

    iy=py+ph-7-lh*2-10; ind_w=pw//3
    for i,(lbl,ok,txt) in enumerate([
            ("Espacio", in_slot,  "✓ Dentro"  if in_slot  else "✗ Fuera"),
            ("Angulo",  angle_ok, "✓ OK"      if angle_ok else "✗ Corregir"),
            ("Detenido",speed_ok, "✓ Parado"  if speed_ok else "✗ Frena")]):
        ix=px+8+i*ind_w
        draw_text(ix+ind_w//2,iy,lbl,fonts['small'],color=(120,128,138),anchor="topcenter")
        draw_text(ix+ind_w//2,iy-lh+2,txt,fonts['small'],
                  color=(80,230,110) if ok else (240,70,55),anchor="topcenter")

    bx=px+10; by=py+38; bw2=pw-20; bh2=10
    _rect(bx,by,bw2,bh2,(0.08,0.09,0.12,1.0))
    if quality>0:
        rc=0.88 if quality<0.5 else 0.88*(1.0-quality)*2
        gc=quality*1.6 if quality<0.5 else 0.78
        _rect(bx,by,int(bw2*quality),bh2,(rc,gc,0.05,1.0))
    _border(bx,by,bw2,bh2,(0.20,0.22,0.28,0.80),1.0)
    draw_text(bx+bw2+6,by+bh2,f"{int(quality*100)}%",
              fonts['small'],color=tc,anchor="bottomleft")
    pt=f"Confirmando ahora: -{penalty} pts" if penalty>0 else "Confirmando ahora: sin penalización"
    draw_text(cx,by-3,pt,fonts['small'],
              color=(230,100,60) if penalty>0 else (80,220,100),anchor="bottomcenter")
    btn="[ ENTER ]  Confirmar estacionamiento" if not confirmed else "✓ Confirmado — sal del espacio"
    draw_text(cx,py+6,btn,fonts['label'],
              color=(255,230,80) if not confirmed else (80,230,110),anchor="bottomcenter")


# ─────────────────────────────────────────────────────────────────────────────
# PANTALLA FINAL
# ─────────────────────────────────────────────────────────────────────────────

def draw_finish_screen(W, H, penalty_pts, cones_hit, fonts):
    grade  = max(0, 100 - penalty_pts)
    passed = grade >= 50
    _rect(0, 0, W, H, (0,0,0,0.68))
    pw, ph = 560, int(H*0.44)
    px = W//2 - pw//2; py = H//2 - ph//2
    bg = (0.04,0.22,0.07,0.96) if passed else (0.22,0.04,0.04,0.96)
    _rrect(px, py, pw, ph, bg, r=16)
    bc = (0.15,0.80,0.25,0.90) if passed else (0.85,0.12,0.08,0.90)
    _border(px, py, pw, ph, bc, 3)
    cx = W//2
    draw_text(cx, py+ph-18, "EXAMEN COMPLETADO",
              fonts['finish_title'], color=(228,232,228), anchor="topcenter")
    rc = (80,245,112) if passed else (240,68,58)
    draw_text(cx, py+int(ph*0.72), "APROBADO" if passed else "DESAPROBADO",
              fonts['finish_result'], color=rc, anchor="topcenter")
    draw_text(cx, py+int(ph*0.50), f"Calificacion:  {grade} / 100 puntos",
              fonts['body'], color=(212,218,212), anchor="topcenter")
    draw_text(cx, py+int(ph*0.36), f"Conos golpeados: {cones_hit}",
              fonts['body'], color=(172,180,175), anchor="topcenter")
    draw_text(cx, py+int(ph*0.22), f"Puntos penalizacion: {penalty_pts}",
              fonts['body'], color=(172,180,175), anchor="topcenter")
    draw_text(cx, py+int(ph*0.10), "Presiona ESC para salir",
              fonts['small'], color=(118,126,122), anchor="topcenter")
