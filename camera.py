# camera.py  —  Versión 3.1  (bug de dirección corregido)


import math
from OpenGL.GL import *
from OpenGL.GLU import *



EYE_HEIGHT        = 1.28    # altura de los ojos del conductor (metros)
EYE_OFFSET_LEFT   = 0.28    # distancia al eje izquierdo del auto (metros)
EYE_OFFSET_FWRD   = 0.20    # adelantar la cámara del centro del auto (metros)

BOB_VERT_AMP      = 0.022   # amplitud vertical (metros)
BOB_LAT_AMP       = 0.008   # amplitud lateral  (metros)
BOB_SPEED_FACTOR  = 9.0     # frecuencia del bob

# Suavizado de la cámara
LERP_POSITION     = 14.0    # qué tan rápido sigue la posición del auto
LERP_ANGLE        = 10.0    # qué tan rápido sigue el ángulo del auto
                             # (menor = más suave al girar, mayor = más responsivo)


LEAN_AMPLITUDE    = 0.025   # radianes de inclinación máxima al girar

# Punto de mira ligeramente por delante del auto
LOOK_AHEAD        = 3.0     # metros adelante del ojo para el punto de mira
LOOK_DOWN_TILT    = 0.04    # inclinación hacia abajo (0 = horizonte exacto)



class Camera:
    def __init__(self):
        self.bob_phase  = 0.0

       
        self.smooth_x   = 0.0
        self.smooth_z   = 36.0
        self.smooth_ang = 0.0

       
        self._lean      = 0.0


    def update(self, vehicle, dt):
        """
        Actualiza la cámara cada frame ANTES de llamar a apply().

        Parámetros:
            vehicle : instancia de VehiclePhysics
            dt      : delta de tiempo en segundos
        """
       
        speed_norm = abs(vehicle.speed) / max(vehicle.MAX_SPEED_FWD, 0.001)
        bob_rate   = max(speed_norm, 0.04)
        self.bob_phase += bob_rate * BOB_SPEED_FACTOR * dt

        
        t_pos = min(dt * LERP_POSITION, 1.0)
        t_ang = min(dt * LERP_ANGLE,    1.0)

        self.smooth_x   += (vehicle.x     - self.smooth_x)   * t_pos
        self.smooth_z   += (vehicle.z     - self.smooth_z)   * t_pos
        self.smooth_ang += _angle_lerp(self.smooth_ang, vehicle.angle, t_ang)

      
        steer_norm  = vehicle.steer_angle / max(vehicle.MAX_STEER_DEG, 1.0)
        target_lean = steer_norm * speed_norm * LEAN_AMPLITUDE
        self._lean += (target_lean - self._lean) * min(dt * 6.0, 1.0)

   
    def apply(self, window_w, window_h):
        """
        Configura la proyección y la vista OpenGL para este frame.
        Llamar al principio del render 3D, ANTES de dibujar la escena.
        """
       
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(
            63.0,                        # FOV vertical en grados
            window_w / window_h,         # aspect ratio
            0.08,                        # near clip
            500.0                        # far clip
        )

       
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        a     = math.radians(self.smooth_ang)
        cos_a = math.cos(a)
        sin_a = math.sin(a)

      

        fx, fz =  sin_a, -cos_a   # forward
        rx, rz =  cos_a,  sin_a   # right (perpendicular izquierdo al forward → *-1 para left)

       
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

        
        look_x = eye_x + LOOK_AHEAD * fx
        look_y = eye_y - LOOK_DOWN_TILT
        look_z = eye_z + LOOK_AHEAD * fz

        
        up_x = math.sin(self._lean)   # componente X del vector up
        up_y = math.cos(self._lean)   # componente Y del vector up (≈1)
        up_z = 0.0

        gluLookAt(
            eye_x,  eye_y,  eye_z,    # posición del ojo
            look_x, look_y, look_z,   # punto de mira
            up_x,   up_y,   up_z      # vector "arriba" (con lean)
        )




def _angle_lerp(current, target, t):
    """
    Interpola el ángulo más corto entre current y target.
    Evita el salto de 359°→0° que haría girar la cámara 360°.
    """
    diff = target - current
    while diff >  180: diff -= 360
    while diff < -180: diff += 360
    return diff * t
