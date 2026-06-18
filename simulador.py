

import sys
import math
import platform as sys_platform
import pygame
from pygame.locals import (DOUBLEBUF, OPENGL, QUIT, KEYDOWN,
                            K_ESCAPE, K_F11, K_F3, K_h, K_q, K_e, K_RETURN,
                            RESIZABLE, FULLSCREEN)
from OpenGL.GL import *

from vehicle_physics import VehiclePhysics, RPM_MAX_DISPLAY
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
                              draw_perf_overlay,
                              parking_penalty_from_quality)
from text_renderer   import clear_text_cache

try:
    import psutil;  _HAS_PSUTIL = True
except ImportError: _HAS_PSUTIL = False
try:
    import GPUtil;  _HAS_GPUTIL = True
except ImportError: _HAS_GPUTIL = False

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
    {"block_x":(-53.0,-22.0),"block_z":(-2.0,24.0),"requires":1,
     "msg":"Completa primero el ESTACIONAMIENTO EN PARALELO"},
    {"block_x":(-14.0,38.0),"block_z":(-9.0,8.0),"requires":2,
     "msg":"Completa primero el OVALO / ROTONDA"},
    {"block_x":(-14.0,10.0),"block_z":(20.0,35.0),"requires":3,
     "msg":"Completa primero el ESTACIONAMIENTO DIAGONAL"},
]


def in_zone(vx, vz, cp):
    return cp["x"][0] <= vx <= cp["x"][1] and cp["z"][0] <= vz <= cp["z"][1]

def crossed_finish(vx, vz):
    return FINISH_X[0] <= vx <= FINISH_X[1] and FINISH_Z[0] <= vz <= FINISH_Z[1]

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
    return v.rpm


# ═══════════════════════════════════════════════════════════════════════════
# ESTACIONAMIENTO
# ═══════════════════════════════════════════════════════════════════════════

_EP_X1=-18.0; _EP_SEP=5.5
_PARALLEL_SLOTS=[(_EP_X1+i*_EP_SEP+2.75,-42.8,-36.8,2.3) for i in range(7)]
_DIAGONAL_SLOTS=[(5.0+i*4.5-16.0+1.25,-7.5,-2.0,2.0) for i in range(7)]
_PARALLEL_ANGLES=[0.0,180.0]; _DIAGONAL_ANGLES=[24.4,204.4]

def _adiff(a,b):
    d=abs(a-b)%360; return d if d<=180 else 360-d
def _aerr(va,ts):
    return min(_adiff(va,t) for t in ts)

def evaluate_parking(vehicle, zone_type):
    vx,vz=vehicle.x,vehicle.z
    sl,ta,at=(_PARALLEL_SLOTS,_PARALLEL_ANGLES,20.0) if zone_type=='parallel' \
              else (_DIAGONAL_SLOTS,_DIAGONAL_ANGLES,18.0)
    bi,bd=0,float('inf')
    for i,(cx,zn,zx,hw) in enumerate(sl):
        d=abs(vx-cx)+(0.0 if zn<=vz<=zx else 4.0)
        if d<bd: bd,bi=d,i
    cx,zn,zx,hw=sl[bi]
    pxq=max(0.0,1.0-abs(vx-cx)/hw)
    pzq=1.0 if zn<=vz<=zx else max(0.0,1.0-min(abs(vz-zn),abs(vz-zx))/2.5)
    ae=_aerr(vehicle.angle,ta); sq=max(0.0,1.0-abs(vehicle.speed)/1.5)
    q=max(0.0,min(1.0,(pxq*pzq)*0.50+max(0.0,1.0-ae/at)*0.35+sq*0.15))
    return {'active':True,'type':zone_type,'quality':q,
            'in_slot':(abs(vx-cx)<hw*1.15 and zn<=vz<=zx),
            'speed_ok':abs(vehicle.speed)<0.3,'angle_ok':ae<at,
            'slot_label':f"Espacio {bi+1}",'confirmed':False}


# ═══════════════════════════════════════════════════════════════════════════
# RENDIMIENTO
# ═══════════════════════════════════════════════════════════════════════════

def _get_cpu_name():
    try:
        if sys_platform.system()=="Windows":
            import winreg
            k=winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(k,"ProcessorNameString")[0].strip()
        elif sys_platform.system()=="Darwin":
            import subprocess
            return subprocess.check_output(["sysctl","-n","machdep.cpu.brand_string"],
                                           stderr=subprocess.DEVNULL).decode().strip()
        else:
            for l in open("/proc/cpuinfo"):
                if "model name" in l: return l.split(":",1)[1].strip()
    except Exception: pass
    return sys_platform.machine() or "CPU Desconocido"

_perf_cache={}; _perf_timer=0.0

def collect_perf(dt, fps):
    global _perf_cache, _perf_timer
    if 'cpu_name' not in _perf_cache:
        _perf_cache['cpu_name']=_get_cpu_name()
        _perf_cache['os_name']=f"{sys_platform.system()} {sys_platform.release()}"
        _perf_cache['ram_total']=(psutil.virtual_memory().total/1024**3 if _HAS_PSUTIL else 0.0)
        _perf_cache['gpu_name']=''
        if _HAS_GPUTIL:
            try:
                gs=GPUtil.getGPUs()
                if gs: _perf_cache['gpu_name']=gs[0].name
            except: pass
    _perf_timer+=dt
    if _perf_timer>=0.5:
        _perf_timer=0.0
        if _HAS_PSUTIL:
            vm=psutil.virtual_memory()
            _perf_cache['cpu_pct']=psutil.cpu_percent(interval=None)
            _perf_cache['ram_pct']=vm.percent
            _perf_cache['ram_mb']=vm.used/1024**2
        else:
            _perf_cache.setdefault('cpu_pct',0.0)
            _perf_cache.setdefault('ram_pct',0.0)
            _perf_cache.setdefault('ram_mb',0.0)
        if _HAS_GPUTIL:
            try:
                gs=GPUtil.getGPUs()
                if gs: _perf_cache['gpu_pct']=gs[0].load*100; _perf_cache['gpu_vram_mb']=gs[0].memoryUsed
                else:  _perf_cache['gpu_pct']=-1; _perf_cache['gpu_vram_mb']=-1
            except: _perf_cache['gpu_pct']=-1; _perf_cache['gpu_vram_mb']=-1
        else:
            _perf_cache.setdefault('gpu_pct',-1)
            _perf_cache.setdefault('gpu_vram_mb',-1)
    _perf_cache['fps']=fps; _perf_cache['fps_target']=TARGET_FPS
    return _perf_cache


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

    barrier_msg       = None
    barrier_timer     = 0.0
    perf_visible      = False
    perf_data         = {}
    _PARKING_CPS      = {2:'parallel', 4:'diagonal'}
    parking_state     = None
    parking_confirmed = False
    _q_prev = False; _e_prev = False

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
                elif event.key == K_F3:
                    perf_visible = not perf_visible
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

            # Q = subir marcha, E = bajar marcha (antirebote)
            q_now = keys[K_q]; e_now = keys[K_e]
            if q_now and not _q_prev:
                if vehicle.shift_up():
                    enqueue(f"Marcha {vehicle.gear_label}  ↑", (160,220,255), 1.5)
            if e_now and not _e_prev:
                if vehicle.shift_down():
                    enqueue(f"Marcha {vehicle.gear_label}  ↓", (255,200,120), 1.5)
            _q_prev = q_now; _e_prev = e_now

            clamp_to_track(vehicle)

            # Evaluación de estacionamiento
            if cp_index in _PARKING_CPS and cp_entered:
                new_ps = evaluate_parking(vehicle, _PARKING_CPS[cp_index])
                if parking_state is not None:
                    new_ps['confirmed'] = parking_state.get('confirmed', False)
                parking_state = new_ps
            else:
                parking_state = None

            # ENTER: confirmar estacionamiento
            if (keys[K_RETURN] and parking_state
                    and not parking_state.get('confirmed', False)):
                parking_state['confirmed'] = True
                parking_confirmed = True
                quality = parking_state.get('quality', 0.0)
                pen = parking_penalty_from_quality(quality)
                q_pct = int(quality * 100)
                if pen > 0:
                    total_penalty += pen
                    vehicle.penalty_pts = total_penalty
                    enqueue(f"Estacionamiento {q_pct}%  -{pen} pts  (total: {total_penalty})",
                            (255,145,50), 5.0)
                else:
                    enqueue(f"¡Estacionamiento perfecto {q_pct}%!  sin penalización",
                            (80,240,110), 5.0)

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

            # Checkpoints enter/exit
            if cp_index < len(CHECKPOINTS):
                cp     = CHECKPOINTS[cp_index]
                inside = in_zone(vehicle.x, vehicle.z, cp)
                if inside and not cp_entered:
                    cp_entered = True; parking_confirmed = False
                    parking_state = None; current_cp = cp
                    enqueue(f"Zona: {cp['name']}", (120,200,255), 4.0)
                elif cp_entered and not inside:
                    is_parking = cp_index in _PARKING_CPS
                    if is_parking and not parking_confirmed:
                        vehicle.speed *= -0.35
                        if vehicle.x < cp["x"][0]: vehicle.x = cp["x"][0]+0.5
                        elif vehicle.x > cp["x"][1]: vehicle.x = cp["x"][1]-0.5
                        if vehicle.z < cp["z"][0]: vehicle.z = cp["z"][0]+0.5
                        elif vehicle.z > cp["z"][1]: vehicle.z = cp["z"][1]-0.5
                        enqueue("Presiona ENTER para confirmar el estacionamiento",
                                (255,210,50), 3.0)
                    else:
                        eval_idx = cp_index - 1
                        if 0 <= eval_idx < len(cp_done): cp_done[eval_idx] = True
                        enqueue(f"Completado: {cp['name']}", (80,230,100), 4.0)
                        print(f"  CP {cp_index} completado: {cp['name']}")
                        cp_index += 1; cp_entered = False
                        parking_confirmed = False; parking_state = None
                        if cp_index < len(CHECKPOINTS):
                            current_cp = CHECKPOINTS[cp_index]
                            enqueue(f"Siguiente → {CHECKPOINTS[cp_index]['name']}",
                                    (180,210,255), 4.0)

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
        perf_data = collect_perf(dt, clock.get_fps())

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
            rpm_val=min(calc_rpm(vehicle), RPM_MAX_DISPLAY),
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
        draw_gear_indicator(W, H, vehicle.speed, vehicle.is_reversing, fonts,
                            gear=vehicle.gear, rpm=vehicle.rpm)

        # Minimapa (inferior derecho, encima tablero)
        draw_minimap(W, H, vehicle.x, vehicle.z, vehicle.angle, cp_done, fonts)

        # Advertencia de cono (bordes rojos)
        draw_cone_warning(W, H, cone_warning, fonts, tick)

        # Barrera de zona bloqueada
        draw_zone_barrier(W, H, barrier_msg, fonts, tick)

        # Feedback (1 mensaje a la vez, centro inferior)
        draw_feedback_flash(W, H, [fb_current] if fb_current else [], fonts)

        # Controles
        draw_controls_legend(W, H, fonts)

        # Estacionamiento
        draw_parking_hud(W, H, parking_state, fonts)

        # Rendimiento (F3)
        if perf_visible:
            draw_perf_overlay(W, H, perf_data, fonts)

        if finished:
            draw_finish_screen(W, H, total_penalty, len(cones_hit_set), fonts)

        end_2d()
        pygame.display.flip()

    clear_text_cache()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
