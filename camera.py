# camera.py  —  Versión 3.1  (bug de dirección corregido)
"""
Sistema de cámara en primera persona para el simulador.

══════════════════════════════════════════════════════════════
BUG CORREGIDO (v3.0 → v3.1)
══════════════════════════════════════════════════════════════
PROBLEMA:
  La versión anterior calculaba el punto de mira así:
      look_x = eye_x - sin_a      ← SIGNO INCORRECTO en X
      look_z = eye_z - cos_a

  El vector forward del VEHÍCULO es  (sin_a, -cos_a) en XZ.
  El vector forward que la CÁMARA usaba era (-sin_a, -cos_a).
  → El componente X estaba invertido.
  → Resultado: al arrancar desde angle=0 (Norte) todo parecía
    correcto, pero al girar a la derecha (angle→90, Este) la
    cámara miraba hacia el Oeste. El usuario veía que al presionar
    W el auto "retrocedía" visualmente.

CORRECCIÓN:
      look_x = eye_x + sin_a      ← POSITIVO (coincide con forward)
      look_z = eye_z - cos_a      ← sin cambio

  Tabla de verificación con los 4 ángulos cardinales:
    angle=  0 (Norte -Z):  forward_veh=( 0,-1)  forward_cam=( 0,-1) ✓
    angle= 90 (Este  +X):  forward_veh=(+1, 0)  forward_cam=(+1, 0) ✓
    angle=180 (Sur   +Z):  forward_veh=( 0,+1)  forward_cam=( 0,+1) ✓
    angle=270 (Oeste -X):  forward_veh=(-1, 0)  forward_cam=(-1, 0) ✓

EYE OFFSET (posición del conductor):
  El conductor está 30 cm a la IZQUIERDA del eje central del auto.
  "Izquierda" relativa al frente del auto es la dirección
  perpendicular izquierda: (-cos_a, +sin_a) en XZ.
  Por tanto:
      eye_x = smooth_x + (-0.30) * cos_a    (no ±sin como antes)
      eye_z = smooth_z + (+0.30) * sin_a

══════════════════════════════════════════════════════════════
CONVENCIÓN DE ÁNGULOS (vehicle_physics.py):
  angle = 0   → el auto apunta hacia −Z (Norte del mapa)
  angle = 90  → el auto apunta hacia +X (Este)
  angle crece al girar a la derecha (sentido horario visto desde arriba)

  Movimiento:
      x += speed * sin(angle) * dt
      z -= speed * cos(angle) * dt
══════════════════════════════════════════════════════════════
"""

import math
from OpenGL.GL import *
from OpenGL.GLU import *


# ── Parámetros ajustables ────────────────────────────────────────────────────
EYE_HEIGHT        = 1.28    # altura de los ojos del conductor (metros)
EYE_OFFSET_LEFT   = 0.28    # distancia al eje izquierdo del auto (metros)
EYE_OFFSET_FWRD   = 0.20    # adelantar la cámara del centro del auto (metros)

# Bob (balanceo natural al caminar/conducir)
BOB_VERT_AMP      = 0.022   # amplitud vertical (metros)
BOB_LAT_AMP       = 0.008   # amplitud lateral  (metros)
BOB_SPEED_FACTOR  = 9.0     # frecuencia del bob

# Suavizado de la cámara
LERP_POSITION     = 14.0    # qué tan rápido sigue la posición del auto
LERP_ANGLE        = 10.0    # qué tan rápido sigue el ángulo del auto
                             # (menor = más suave al girar, mayor = más responsivo)

# Inclinación de la cámara al girar (efecto de "lean")
LEAN_AMPLITUDE    = 0.025   # radianes de inclinación máxima al girar

# Punto de mira ligeramente por delante del auto
LOOK_AHEAD        = 3.0     # metros adelante del ojo para el punto de mira
LOOK_DOWN_TILT    = 0.04    # inclinación hacia abajo (0 = horizonte exacto)
# ────────────────────────────────────────────────────────────────────────────


class Camera:
    def __init__(self):
        self.bob_phase  = 0.0

        # Estado suavizado (se inicializa en simulador.py con los valores del vehículo)
        self.smooth_x   = 0.0
        self.smooth_z   = 36.0
        self.smooth_ang = 0.0

        # Para el efecto de lean al girar
        self._lean      = 0.0

    # ─────────────────────────────────────────────────────────────────────
    def update(self, vehicle, dt):
        """
        Actualiza la cámara cada frame ANTES de llamar a apply().

        Parámetros:
            vehicle : instancia de VehiclePhysics
            dt      : delta de tiempo en segundos
        """
        # ── Bob ───────────────────────────────────────────────────────────
        speed_norm = abs(vehicle.speed) / max(vehicle.MAX_SPEED_FWD, 0.001)
        bob_rate   = max(speed_norm, 0.04)
        self.bob_phase += bob_rate * BOB_SPEED_FACTOR * dt

        # ── Suavizado de posición y ángulo (lerp) ─────────────────────────
        # El lerp es proporcional al dt para que sea frame-rate independiente
        t_pos = min(dt * LERP_POSITION, 1.0)
        t_ang = min(dt * LERP_ANGLE,    1.0)

        self.smooth_x   += (vehicle.x     - self.smooth_x)   * t_pos
        self.smooth_z   += (vehicle.z     - self.smooth_z)   * t_pos
        self.smooth_ang += _angle_lerp(self.smooth_ang, vehicle.angle, t_ang)

        # ── Lean (inclinación al girar) ───────────────────────────────────
        # steer_norm es -1..+1 (izq..der). A mayor velocidad más lean.
        steer_norm  = vehicle.steer_angle / max(vehicle.MAX_STEER_DEG, 1.0)
        target_lean = steer_norm * speed_norm * LEAN_AMPLITUDE
        self._lean += (target_lean - self._lean) * min(dt * 6.0, 1.0)

    # ─────────────────────────────────────────────────────────────────────
    def apply(self, window_w, window_h):
        """
        Configura la proyección y la vista OpenGL para este frame.
        Llamar al principio del render 3D, ANTES de dibujar la escena.
        """
        # ── Proyección perspectiva ────────────────────────────────────────
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(
            63.0,                        # FOV vertical en grados
            window_w / window_h,         # aspect ratio
            0.08,                        # near clip
            500.0                        # far clip
        )

        # ── Vista (gluLookAt) ─────────────────────────────────────────────
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        a     = math.radians(self.smooth_ang)
        cos_a = math.cos(a)
        sin_a = math.sin(a)

        # ── Vectores del sistema de referencia del auto ───────────────────
        # Forward (hacia donde mira/avanza el auto):
        #   fx =  sin(a),   fz = -cos(a)
        # Right (hacia la derecha del auto, perpendicular al forward):
        #   rx =  cos(a),   rz =  sin(a)
        # Up: (0, 1, 0) — asumimos terreno plano

        fx, fz =  sin_a, -cos_a   # forward
        rx, rz =  cos_a,  sin_a   # right (perpendicular izquierdo al forward → *-1 para left)

        # ── Posición del ojo ──────────────────────────────────────────────
        # Centro del auto + desplazamiento a la izquierda + desplazamiento adelante
        bob_y   = math.sin(self.bob_phase)           * BOB_VERT_AMP
        bob_lat = math.sin(self.bob_phase * 0.85)    * BOB_LAT_AMP

        eye_x = (self.smooth_x
                 - EYE_OFFSET_LEFT * rx   # izquierda del auto (-rx porque rx apunta a la derecha)
                 + EYE_OFFSET_FWRD * fx   # ligeramente adelante
                 + bob_lat         * rx)  # bob lateral en eje derecha/izquierda
        eye_y = EYE_HEIGHT + bob_y
        eye_z = (self.smooth_z
                 - EYE_OFFSET_LEFT * rz
                 + EYE_OFFSET_FWRD * fz
                 + bob_lat         * rz)

        # ── Punto de mira ─────────────────────────────────────────────────
        # LOOK_AHEAD metros adelante del ojo, en la dirección forward del auto
        look_x = eye_x + LOOK_AHEAD * fx
        look_y = eye_y - LOOK_DOWN_TILT
        look_z = eye_z + LOOK_AHEAD * fz

        # ── Vector "arriba" con lean al girar ─────────────────────────────
        # Inclinar ligeramente la cámara hacia el lado de la curva
        up_x = math.sin(self._lean)   # componente X del vector up
        up_y = math.cos(self._lean)   # componente Y del vector up (≈1)
        up_z = 0.0

        gluLookAt(
            eye_x,  eye_y,  eye_z,    # posición del ojo
            look_x, look_y, look_z,   # punto de mira
            up_x,   up_y,   up_z      # vector "arriba" (con lean)
        )


# ── Utilidad ─────────────────────────────────────────────────────────────────

def _angle_lerp(current, target, t):
    """
    Interpola el ángulo más corto entre current y target.
    Evita el salto de 359°→0° que haría girar la cámara 360°.
    """
    diff = target - current
    while diff >  180: diff -= 360
    while diff < -180: diff += 360
    return diff * t
