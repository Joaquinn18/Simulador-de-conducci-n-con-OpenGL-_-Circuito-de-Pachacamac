# simulador.py  —  Versión 4.3
"""
Simulador de Conducción – Touring y Automóvil Club del Perú (Ruta A)
Proyecto Final – Computación Gráfica y Visual – UPN 2026-1

CAMBIOS v4.3:
  - Panel de guía OCULTABLE con tecla H
  - Feedback: 1 mensaje a la vez, duración más larga, no se superpone
  - Barrera de zona: el vehículo NO puede avanzar al siguiente bloque
    si no completó el anterior (rebote físico + aviso en pantalla)
  - Óvalo conectado a la recta Oeste (scene.py)
  - Banderines y franjas de color delimitan cada maniobra visualmente
  - Minimapa muestra estado de cada zona con color

CONTROLES:
  W/↑  Avanzar    S/↓  Frenar/Rev    A/←  Izq    D/→  Der
  H    Ocultar/mostrar panel de guía
  F11  Pantalla completa
  ESC  Salir
"""

import sys
import math
import pygame
from pygame.locals import (DOUBLEBUF, OPENGL, QUIT, KEYDOWN,
                            K_ESCAPE, K_F11, K_h, RESIZABLE, FULLSCREEN)
from OpenGL.GL import *

from vehicle_physics import VehiclePhysics
from camera          import Camera
from scene           import (draw_full_scene, ALL_CONES, cone_hit_states,
                              init_lighting)
from collision       import (check_cone_collision, clamp_to_track, CONE_PENALTY)
from cabin           import draw_cabin_2d
from hud             import (begin_2d, end_2d,
                              draw_guide_panel,
                              draw_penalty_hud,
                              draw_speed_digital,
                              draw_cone_warning,
                              draw_controls_legend,
                              draw_finish_screen,
                              draw_gear_indicator,
                              draw_minimap,
                              draw_feedback_flash,
                              draw_zone_barrier,
                              draw_parking_hud,
                              parking_penalty_from_quality)
from text_renderer   import clear_text_cache

BASE_W, BASE_H = 1280, 720
TARGET_FPS     = 60

# ═══════════════════════════════════════════════════════════════════════════
# CHECKPOINTS
# ═══════════════════════════════════════════════════════════════════════════
CHECKPOINTS = [
    {
        "name":   "ENTRADA AL CIRCUITO",
        "tip":    "Avanza hacia el norte con W",
        "detail": "Carril derecho | vel. max 35 km/h",
        "color":  (0.20, 0.85, 0.35),
        "x":      (30.0,  46.0), "z": (5.0,  35.0),
        "start":  True,
    },
    {
        "name":   "ZONA HABILIDAD 35 KPH",
        "tip":    "Zigzaguea entre los conos sin tocarlos",
        "detail": "Vel. max 35 km/h | cono golpeado = -5 pts",
        "color":  (0.95, 0.65, 0.05),
        "x":      (30.0,  46.0), "z": (-33.0, -14.0),
    },
    {
        "name":   "ESTACIONAMIENTO EN PARALELO",
        "tip":    "Llega a la recta norte y estaciona en reversa",
        "detail": "Entra en uno de los 7 espacios amarillos",
        "color":  (0.30, 0.65, 0.95),
        "x":      (-22.0, 38.0), "z": (-43.0, -33.0),
    },
    {
        "name":   "OVALO / ROTONDA",
        "tip":    "Gira en sentido horario dentro del ovalo",
        "detail": "Vuelta completa | sal hacia el sur-este",
        "color":  (0.70, 0.30, 0.95),
        "x":      (-53.0, -22.0), "z": (-2.0,  24.0),
    },
    {
        "name":   "ESTACIONAMIENTO DIAGONAL",
        "tip":    "Estaciona en diagonal en uno de los 7 espacios",
        "detail": "Entra en angulo | sin pisar la linea frontal",
        "color":  (0.90, 0.45, 0.10),
        "x":      (-14.0,  38.0), "z": (-9.0,   8.0),
    },
    {
        "name":   "ZONA DE SALIDA",
        "tip":    "Dirígete al sur hacia la linea VERDE de SALIDA",
        "detail": "Detente sobre la linea | espera al veedor",
        "color":  (0.20, 0.90, 0.40),
        "x":      (-14.0,  10.0), "z": (20.0,  35.0),
    },
]

FINISH_X = (-8.0, 6.0)
FINISH_Z  = (29.0, 35.0)
EVAL_CPS  = [cp for cp in CHECKPOINTS if not cp.get("start", False)]


# ── Zonas permitidas según CPs completados ───────────────────────────────────
# BARRIER_ZONES[i] = zona que está BLOQUEADA si cp_done[i-1] es False
# (i = índice en EVAL_CPS, basado 0)
# El vehículo NO puede entrar en la zona i+1 si no completó la i.
# Cada barrera tiene: la caja que rebota, el mensaje, y qué cp_done index exige
BARRIERS = [
    # cp_done[0] = trocha completada → puedes ir a paralelo
    {
        "block_x": (-22.0, 38.0), "block_z": (-43.0, -33.0),  # zona paralelo
        "requires": 0,            # necesita cp_done[0] (trocha)
        "msg": "Completa primero la ZONA HABILIDAD 35 KPH",
    },
    # cp_done[1] = paralelo → puedes ir al óvalo (recta oeste es zona libre)
    {
        "block_x": (-53.0, -22.0), "block_z": (-2.0, 24.0),
        "requires": 1,
        "msg": "Completa primero el ESTACIONAMIENTO EN PARALELO",
    },
    # cp_done[2] = óvalo → puedes ir a diagonal
    {
        "block_x": (-14.0, 38.0), "block_z": (-9.0, 8.0),
        "requires": 2,
        "msg": "Completa primero el OVALO / ROTONDA",
    },
    # cp_done[3] = diagonal → puedes ir a salida
    {
        "block_x": (-14.0, 10.0), "block_z": (20.0, 35.0),
        "requires": 3,
        "msg": "Completa primero el ESTACIONAMIENTO DIAGONAL",
    },
]


def in_zone(vx, vz, cp):
    return cp["x"][0] <= vx <= cp["x"][1] and cp["z"][0] <= vz <= cp["z"][1]

def crossed_finish(vx, vz):
    return FINISH_X[0] <= vx <= FINISH_X[1] and FINISH_Z[0] <= vz <= FINISH_Z[1]

# ═══════════════════════════════════════════════════════════════════════════
# LÓGICA DE ESTACIONAMIENTO
# ═══════════════════════════════════════════════════════════════════════════

_EP_X1  = -18.0
_EP_SEP =  5.5
_PARALLEL_SLOTS = [
    (_EP_X1 + i * _EP_SEP + 2.75, -42.8, -36.8, 2.3)
    for i in range(7)
]
_DIAGONAL_SLOTS = [
    (5.0 + i * 4.5 - 16.0 + 1.25, -7.5, -2.0, 2.0)
    for i in range(7)
]
_PARALLEL_ANGLES = [0.0, 180.0]
_DIAGONAL_ANGLES = [24.4, 204.4]


def _angle_diff(a, b):
    d = abs(a - b) % 360
    return d if d <= 180 else 360 - d


def _nearest_angle_err(vehicle_angle, targets):
    return min(_angle_diff(vehicle_angle, t) for t in targets)


def evaluate_parking(vehicle, zone_type):
    vx, vz = vehicle.x, vehicle.z
    if zone_type == 'parallel':
        slots, target_angles, angle_tol = _PARALLEL_SLOTS, _PARALLEL_ANGLES, 20.0
    else:
        slots, target_angles, angle_tol = _DIAGONAL_SLOTS, _DIAGONAL_ANGLES, 18.0

    best_idx, best_dist = 0, float('inf')
    for i, (cx, zmin, zmax, hw) in enumerate(slots):
        dist = abs(vx - cx) + (0.0 if zmin <= vz <= zmax else 4.0)
        if dist < best_dist:
            best_dist, best_idx = dist, i

    cx, zmin, zmax, hw = slots[best_idx]
    in_slot_x  = abs(vx - cx) < hw * 1.15
    in_slot_z  = zmin <= vz <= zmax
    in_slot    = in_slot_x and in_slot_z
    pos_x_qual = max(0.0, 1.0 - abs(vx - cx) / hw)
    pos_z_qual = 1.0 if in_slot_z else max(0.0, 1.0 - min(abs(vz-zmin), abs(vz-zmax)) / 2.5)
    pos_quality = pos_x_qual * pos_z_qual

    angle_err  = _nearest_angle_err(vehicle.angle, target_angles)
    angle_ok   = angle_err < angle_tol
    angle_qual = max(0.0, 1.0 - angle_err / angle_tol)

    speed_ok   = abs(vehicle.speed) < 0.3
    speed_qual = max(0.0, 1.0 - abs(vehicle.speed) / 1.5)

    quality = max(0.0, min(1.0,
        pos_quality * 0.50 + angle_qual * 0.35 + speed_qual * 0.15))

    return {
        'active':     True,
        'type':       zone_type,
        'quality':    quality,
        'in_slot':    in_slot,
        'speed_ok':   speed_ok,
        'angle_ok':   angle_ok,
        'slot_label': f"Espacio {best_idx + 1}",
        'confirmed':  False,   # se pone True al presionar ENTER
    }


def check_barriers(vehicle, cp_done):
    """
    Verifica si el vehículo está intentando entrar en una zona bloqueada.
    Si es así, lo devuelve a donde vino (rebote) y devuelve el mensaje.
    """
    for b in BARRIERS:
        bx, bz = b["block_x"], b["block_z"]
        req = b["requires"]
        if req >= len(cp_done) or cp_done[req]:
            continue   # zona desbloqueada, no hay barrera
        # ¿está dentro de la zona bloqueada?
        if bx[0] <= vehicle.x <= bx[1] and bz[0] <= vehicle.z <= bz[1]:
            # Rebote: invertir velocidad y empujar hacia afuera
            vehicle.speed *= -0.4
            # Empujar hacia el borde más cercano
            mid_x = (bx[0]+bx[1])/2
            mid_z = (bz[0]+bz[1])/2
            push = 0.8
            if abs(vehicle.x - bx[0]) < abs(vehicle.x - bx[1]):
                vehicle.x = bx[0] - push
            else:
                vehicle.x = bx[1] + push
            return b["msg"]
    return None


# ═══════════════════════════════════════════════════════════════════════════
# FUENTES
# ═══════════════════════════════════════════════════════════════════════════
def build_fonts(scale=1.0):
    def sz(s): return max(8, int(s * scale))
    try:
        base = "consolas"
        return {
            'title':         pygame.font.SysFont(base, sz(17), bold=True),
            'body':          pygame.font.SysFont(base, sz(14)),
            'small':         pygame.font.SysFont(base, sz(12)),
            'label':         pygame.font.SysFont(base, sz(11), bold=True),
            'big_num':       pygame.font.SysFont(base, sz(26), bold=True),
            'speed_num':     pygame.font.SysFont(base, sz(30), bold=True),
            'gauge':         pygame.font.SysFont(base, sz(11)),
            'lcd_num':       pygame.font.SysFont(base, sz(28), bold=True),
            'lcd_label':     pygame.font.SysFont(base, sz(10)),
            'warning':       pygame.font.SysFont(base, sz(16), bold=True),
            'finish_title':  pygame.font.SysFont(base, sz(26), bold=True),
            'finish_result': pygame.font.SysFont(base, sz(34), bold=True),
            'feedback':      pygame.font.SysFont(base, sz(16), bold=True),
            'checkpoint':    pygame.font.SysFont(base, sz(11), bold=True),
        }
    except Exception:
        def sf(s, b=False): return pygame.font.SysFont(None, sz(s), bold=b)
        return {k: sf(v[0], v[1]) for k,v in {
            'title':(17,True),'body':(14,False),'small':(12,False),
            'label':(11,True),'big_num':(26,True),'speed_num':(30,True),
            'gauge':(11,False),'lcd_num':(28,True),'lcd_label':(10,False),
            'warning':(16,True),'finish_title':(26,True),'finish_result':(34,True),
            'feedback':(16,True),'checkpoint':(11,True),
        }.items()}


# ═══════════════════════════════════════════════════════════════════════════
# VENTANA / GL
# ═══════════════════════════════════════════════════════════════════════════
def create_window(fullscreen=False):
    if fullscreen:
        info = pygame.display.Info()
        W, H = info.current_w, info.current_h
        surf = pygame.display.set_mode((W, H), DOUBLEBUF|OPENGL|FULLSCREEN)
    else:
        W, H = BASE_W, BASE_H
        surf = pygame.display.set_mode((W, H), DOUBLEBUF|OPENGL|RESIZABLE)
    return surf, W, H

def setup_gl(W, H):
    glViewport(0, 0, W, H)
    glEnable(GL_DEPTH_TEST);  glDepthFunc(GL_LEQUAL)
    glEnable(GL_NORMALIZE);   glShadeModel(GL_SMOOTH)
    glClearColor(0.68, 0.84, 0.96, 1.0)
    glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
    glEnable(GL_FOG);  glFogi(GL_FOG_MODE, GL_LINEAR)
    glFogfv(GL_FOG_COLOR, [0.68, 0.84, 0.96, 1.0])
    glFogf(GL_FOG_START, 65.0);  glFogf(GL_FOG_END, 220.0)
    init_lighting()

def calc_rpm(v):
    return 900 + 4600 * min(abs(v.speed)/v.MAX_SPEED_FWD, 1.0)


# ═══════════════════════════════════════════════════════════════════════════
# FEEDBACK  (cola simple, 1 activo a la vez)
# ═══════════════════════════════════════════════════════════════════════════
class FeedbackMsg:
    def __init__(self, text, color, duration=4.0):
        self.text     = text
        self.color    = color
        self.duration = duration
        self.elapsed  = 0.0
        self.active   = True

    def update(self, dt):
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.active = False

    @property
    def alpha(self):
        fade = self.duration * 0.70
        if self.elapsed < fade: return 1.0
        return max(0.0, 1.0 - (self.elapsed-fade)/(self.duration*0.30))


# ═══════════════════════════════════════════════════════════════════════════
# LOOP PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════
def main():
    pygame.init()
    surf, W, H = create_window(False)
    pygame.display.set_caption(
        "Simulador de Conduccion – Touring y Automovil Club del Peru  v4.3")
    setup_gl(W, H)

    clock       = pygame.time.Clock()
    scale       = H / BASE_H
    fonts       = build_fonts(scale)
    fullscreen  = False
    guide_visible = True   # H alterna esto

    vehicle = VehiclePhysics(start_x=40.0, start_z=24.0, start_angle=0.0)
    camera  = Camera()
    camera.smooth_x   = vehicle.x
    camera.smooth_z   = vehicle.z
    camera.smooth_ang = vehicle.angle

    total_penalty = 0
    cones_hit_set = set()
    cone_warning  = False
    finished      = False
    tick          = 0

    # Checkpoints
    cp_index   = 1
    cp_done    = [False] * len(EVAL_CPS)
    cp_entered = False
    current_cp = CHECKPOINTS[0]

    # Feedback: cola; mostramos 1 a la vez
    fb_queue   = []   # mensajes pendientes
    fb_current = None # el que está en pantalla ahora

    barrier_msg      = None
    barrier_timer    = 0.0

    # CP indices: 0=ENTRADA,1=ZIGZAG,2=PARALELO,3=OVALO,4=DIAGONAL,5=SALIDA
    _PARKING_CPS    = {2: 'parallel', 4: 'diagonal'}
    parking_state   = None    # dict de evaluate_parking(), con 'confirmed'
    parking_confirmed = False  # True cuando ENTER fue presionado en esta zona

    def enqueue(text, color, duration=4.0):
        """Añade un mensaje a la cola; no se acumulan más de 4."""
        if len(fb_queue) < 4:
            fb_queue.append(FeedbackMsg(text, color, duration))

    enqueue("¡Circuito iniciado! Avanza hacia el norte", (80, 220, 100), 5.0)

    print("="*62)
    print("  SIMULADOR TOURING PACHACAMAC  v4.3")
    print("  H = ocultar/mostrar guia  |  F11 = pantalla completa")
    print("="*62)

    running = True
    while running:
        dt   = min(clock.tick(TARGET_FPS)/1000.0, 0.05)
        tick += 1

        # ── Eventos ────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                elif event.key == K_F11:
                    fullscreen = not fullscreen
                    surf, W, H = create_window(fullscreen)
                    scale = H/BASE_H
                    fonts = build_fonts(scale)
                    setup_gl(W, H)
                    clear_text_cache()
                elif event.key == K_h:
                    guide_visible = not guide_visible
            elif event.type == pygame.VIDEORESIZE:
                W, H = event.w, event.h
                surf  = pygame.display.set_mode((W,H), DOUBLEBUF|OPENGL|RESIZABLE)
                scale = H/BASE_H
                fonts = build_fonts(scale)
                setup_gl(W, H)
                clear_text_cache()

        # ── Física ─────────────────────────────────────────────────────
        if not finished:
            keys = pygame.key.get_pressed()
            vehicle.update(keys, dt)
            clamp_to_track(vehicle)

            # ── Barreras de zona ──────────────────────────────────────
            bmsg = check_barriers(vehicle, cp_done)
            if bmsg:
                barrier_msg   = bmsg
                barrier_timer = 3.0    # mostrar 3 segundos
            if barrier_timer > 0:
                barrier_timer -= dt
                if barrier_timer <= 0:
                    barrier_msg = None

            # ── Colisión conos ─────────────────────────────────────────
            cone_hit, cone_idx = check_cone_collision(
                vehicle.x, vehicle.z, ALL_CONES)
            cone_warning = False
            if cone_hit and cone_idx not in cones_hit_set:
                cones_hit_set.add(cone_idx)
                cone_hit_states[cone_idx] = True
                total_penalty += CONE_PENALTY
                vehicle.penalty_pts = total_penalty
                vehicle.cones_hit   = len(cones_hit_set)
                enqueue(
                    f"¡Cono golpeado! -{CONE_PENALTY} pts  (total: {total_penalty})",
                    (255, 70, 55), 3.5)
                print(f"  Cono {cone_idx} | +{CONE_PENALTY}pts → {total_penalty}")

            for cx2, cz2 in ALL_CONES:
                if math.sqrt((vehicle.x-cx2)**2+(vehicle.z-cz2)**2) < 1.20:
                    cone_warning = True; break

            # ── Evaluación de estacionamiento en tiempo real ───────────
            if cp_index in _PARKING_CPS and cp_entered:
                new_state = evaluate_parking(vehicle, _PARKING_CPS[cp_index])
                if parking_state is None:
                    parking_state = new_state
                else:
                    # Preservar 'confirmed' si ya se confirmó
                    new_state['confirmed'] = parking_state.get('confirmed', False)
                    parking_state = new_state
            elif not (cp_index in _PARKING_CPS and cp_entered):
                parking_state = None

            # ── ENTER: confirmar estacionamiento ──────────────────────
            from pygame.locals import K_RETURN
            if (keys[K_RETURN]
                    and parking_state
                    and parking_state.get('active', False)
                    and not parking_state.get('confirmed', False)):
                parking_state['confirmed'] = True
                parking_confirmed = True
                quality = parking_state.get('quality', 0.0)
                pen     = parking_penalty_from_quality(quality)
                q_pct   = int(quality * 100)
                if pen > 0:
                    total_penalty          += pen
                    vehicle.penalty_pts     = total_penalty
                    enqueue(
                        f"Estacionamiento {q_pct}%  -{pen} pts  (total: {total_penalty})",
                        (255, 145, 50), 5.0)
                else:
                    enqueue(
                        f"¡Estacionamiento perfecto {q_pct}%!  sin penalización",
                        (80, 240, 110), 5.0)
                print(f"  Parking confirmado calidad={quality:.2f} ({q_pct}%) → -{pen}pts")

            # ── Checkpoints enter/exit ─────────────────────────────────
            if cp_index < len(CHECKPOINTS):
                cp     = CHECKPOINTS[cp_index]
                inside = in_zone(vehicle.x, vehicle.z, cp)

                if inside and not cp_entered:
                    cp_entered        = True
                    parking_confirmed = False
                    parking_state     = None
                    current_cp        = cp
                    enqueue(f"Zona: {cp['name']}", (120, 200, 255), 4.0)

                elif cp_entered and not inside:
                    is_parking = cp_index in _PARKING_CPS

                    # Bloquear salida si es zona de parking y no se confirmó con ENTER
                    if is_parking and not parking_confirmed:
                        vehicle.speed *= -0.35
                        if vehicle.x < cp["x"][0]: vehicle.x = cp["x"][0] + 0.5
                        elif vehicle.x > cp["x"][1]: vehicle.x = cp["x"][1] - 0.5
                        if vehicle.z < cp["z"][0]: vehicle.z = cp["z"][0] + 0.5
                        elif vehicle.z > cp["z"][1]: vehicle.z = cp["z"][1] - 0.5
                        enqueue("Presiona ENTER para confirmar el estacionamiento",
                                (255, 210, 50), 3.0)
                    else:
                        # CP completado normalmente
                        eval_idx = cp_index - 1
                        if 0 <= eval_idx < len(cp_done):
                            cp_done[eval_idx] = True
                        enqueue(f"Completado: {cp['name']}", (80, 230, 100), 4.0)
                        print(f"  CP {cp_index} completado: {cp['name']}")
                        cp_index          += 1
                        cp_entered         = False
                        parking_confirmed  = False
                        parking_state      = None
                        if cp_index < len(CHECKPOINTS):
                            current_cp = CHECKPOINTS[cp_index]
                            enqueue(f"Siguiente → {CHECKPOINTS[cp_index]['name']}",
                                    (180, 210, 255), 4.0)

            # ── Meta ──────────────────────────────────────────────────
            if all(cp_done) and crossed_finish(vehicle.x, vehicle.z) and not finished:
                finished = True
                grade    = max(0, 100 - total_penalty)
                result   = "APROBADO" if grade >= 50 else "DESAPROBADO"
                enqueue(f"¡EXAMEN COMPLETADO!  {result}  ({grade}/100)",
                        (80, 240, 110), 99)
                print(f"\n  EXAMEN COMPLETADO – {result}")
                print(f"  Conos: {len(cones_hit_set)} | Penaliz: {total_penalty} | Nota: {grade}/100\n")

            # ── Avanzar feedback en cola ──────────────────────────────
            # Si el actual terminó, sacar el siguiente de la cola
            if fb_current is None or not fb_current.active:
                if fb_queue:
                    fb_current = fb_queue.pop(0)
                else:
                    fb_current = None
            if fb_current is not None:
                fb_current.update(dt)

        camera.update(vehicle, dt)

        # ── RENDER ─────────────────────────────────────────────────────
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # 1. Escena 3D
        camera.apply(W, H)
        draw_full_scene()

        # 2. Cabina 2D
        steer_norm = vehicle.steer_angle / vehicle.MAX_STEER_DEG
        draw_cabin_2d(
            screen_w=W, screen_h=H,
            steer_norm=steer_norm,
            speed_kmh=vehicle.speed_kmh,
            rpm_val=calc_rpm(vehicle),
            is_braking=vehicle.is_braking,
            bob_phase=camera.bob_phase,
            fonts=fonts,
        )

        # 3. HUD 2D
        begin_2d(W, H)

        # Panel de guía (ocultable con H) — lateral derecho
        draw_guide_panel(W, H, current_cp, guide_visible, cp_done, fonts)

        # Penalización (siempre visible, esquina superior derecha)
        draw_penalty_hud(W, H, total_penalty, len(cones_hit_set), fonts, tick)

        # Velocímetro digital y marcha (izquierda encima tablero)
        draw_speed_digital(W, H, vehicle.speed_kmh, fonts)
        draw_gear_indicator(W, H, vehicle.speed, vehicle.is_reversing, fonts)

        # Minimapa (inferior derecho, encima tablero)
        draw_minimap(W, H, vehicle.x, vehicle.z, vehicle.angle, cp_done, fonts)

        # Advertencia de cono (bordes rojos)
        draw_cone_warning(W, H, cone_warning, fonts, tick)

        # Barrera de zona bloqueada
        draw_zone_barrier(W, H, barrier_msg, fonts, tick)

        # Feedback (1 mensaje a la vez, centro inferior)
        draw_feedback_flash(W, H, [fb_current] if fb_current else [], fonts)

        # Controles (izquierda superior)
        draw_controls_legend(W, H, fonts)

        # Recuadro de estacionamiento (solo en zonas paralelo y diagonal)
        draw_parking_hud(W, H, parking_state, fonts)

        if finished:
            draw_finish_screen(W, H, total_penalty, len(cones_hit_set), fonts)

        end_2d()
        pygame.display.flip()

    clear_text_cache()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
