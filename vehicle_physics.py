# vehicle_physics.py
"""
Física del vehículo para el simulador de conducción.
Modelo cinemático de bicicleta (Ackermann simplificado):
- El giro no es instantáneo: depende de la velocidad y el ángulo de rueda
- Hay inercia: el auto no frena ni acelera de golpe
- La velocidad en reversa es limitada (como un auto real)
"""

import math

class VehiclePhysics:
    # Dimensiones del vehículo (en metros, escala 1:1 con OpenGL)
    WHEELBASE    = 2.70   # distancia entre ejes (largo del auto)
    WIDTH        = 1.80   # ancho del auto (para colisiones)
    LENGTH       = 4.20   # largo del auto (para colisiones)

    # Límites de velocidad
    MAX_SPEED_FWD = 8.0   # m/s adelante (~29 km/h, suficiente para la pista)
    MAX_SPEED_REV = 2.5   # m/s reversa
    MAX_STEER_DEG = 30.0  # ángulo máximo de volante en grados

    # Física
    ACCEL_RATE    = 3.5   # m/s² al presionar gas
    BRAKE_RATE    = 7.0   # m/s² al frenar (más fuerte que el gas)
    DRAG_RATE     = 2.0   # m/s² de fricción natural al soltar el gas
    STEER_RATE    = 80.0  # grados/segundo de giro del volante
    STEER_RETURN  = 120.0 # grados/segundo de retorno al centro

    def __init__(self, start_x=0.0, start_z=5.0, start_angle=0.0):
        # Posición y orientación en el mundo
        self.x     = start_x      # posición X en el plano
        self.z     = start_z      # posición Z en el plano
        self.angle = start_angle  # ángulo de orientación en grados (0 = mirando hacia -Z)

        # Estado dinámico
        self.speed        = 0.0   # velocidad actual en m/s (positivo=adelante, negativo=reversa)
        self.steer_angle  = 0.0   # ángulo actual del volante en grados
        self.is_braking   = False  # ¿está pisando el freno?
        self.is_reversing = False  # ¿está en reversa?

        # Para suavizar la cámara (bob y vibración)
        self.wheel_rotation = 0.0  # rotación acumulada de las ruedas (para animación)

        # Estado del examen (para mostrar al usuario qué hacer)
        self.exam_phase    = 0     # fase actual del recorrido
        self.cones_hit     = 0     # cuántos conos tocó
        self.penalty_pts   = 0     # puntos de penalización acumulados

    def update(self, keys_pressed, dt):
        """
        Actualiza el estado del vehículo en base a las teclas presionadas.
        keys_pressed es el dict de pygame.key.get_pressed()
        dt es el delta de tiempo en segundos desde el último frame.
        """
        from pygame.locals import K_w, K_s, K_a, K_d, K_UP, K_DOWN, K_LEFT, K_RIGHT

        gas    = keys_pressed[K_w] or keys_pressed[K_UP]
        brake  = keys_pressed[K_s] or keys_pressed[K_DOWN]
        left   = keys_pressed[K_a] or keys_pressed[K_LEFT]
        right  = keys_pressed[K_d] or keys_pressed[K_RIGHT]

        # ── Lógica de aceleración / freno / reversa ──────────────────────
        self.is_braking   = False
        self.is_reversing = False

        if gas:
            if self.speed >= 0:
                # Acelerar hacia adelante
                self.speed = min(self.speed + self.ACCEL_RATE * dt, self.MAX_SPEED_FWD)
            else:
                # Estábamos en reversa, el gas actúa como freno
                self.speed = min(self.speed + self.BRAKE_RATE * dt, 0.0)
                self.is_braking = True

        elif brake:
            if self.speed > 0.05:
                # Frenar estando en movimiento hacia adelante
                self.speed = max(self.speed - self.BRAKE_RATE * dt, 0.0)
                self.is_braking = True
            elif self.speed <= 0.05:
                # Entrar en reversa
                self.speed = max(self.speed - self.ACCEL_RATE * dt, -self.MAX_SPEED_REV)
                self.is_reversing = True

        else:
            # Sin input: fricción natural desacelera
            if self.speed > 0:
                self.speed = max(self.speed - self.DRAG_RATE * dt, 0.0)
            elif self.speed < 0:
                self.speed = min(self.speed + self.DRAG_RATE * dt, 0.0)

        # ── Lógica del volante ───────────────────────────────────────────
        if left:
            self.steer_angle = max(self.steer_angle - self.STEER_RATE * dt,
                                   -self.MAX_STEER_DEG)
        elif right:
            self.steer_angle = min(self.steer_angle + self.STEER_RATE * dt,
                                    self.MAX_STEER_DEG)
        else:
            # El volante vuelve al centro solo (más rápido si va más rápido)
            speed_factor = min(abs(self.speed) / self.MAX_SPEED_FWD + 0.3, 1.0)
            return_speed = self.STEER_RETURN * speed_factor * dt
            if self.steer_angle > 0:
                self.steer_angle = max(self.steer_angle - return_speed, 0.0)
            elif self.steer_angle < 0:
                self.steer_angle = min(self.steer_angle + return_speed, 0.0)

        # ── Modelo cinemático de bicicleta (Ackermann) ───────────────────
        # A mayor velocidad, menos efecto del volante (comportamiento real)
        if abs(self.speed) > 0.01:
            steer_rad = math.radians(self.steer_angle)

            # Radio de giro basado en el largo del auto y el ángulo del volante
            if abs(steer_rad) > 0.001:
                turn_radius = self.WHEELBASE / math.tan(steer_rad)
                # Velocidad angular del chasis (rad/s)
                angular_velocity = self.speed / turn_radius
            else:
                angular_velocity = 0.0

            # Actualizar ángulo de orientación
            self.angle += math.degrees(angular_velocity) * dt

            # Mover el vehículo en la dirección que apunta
            angle_rad = math.radians(self.angle)
            self.x += self.speed * math.sin(angle_rad) * dt
            self.z -= self.speed * math.cos(angle_rad) * dt

        # Rotación de ruedas para animación
        self.wheel_rotation += self.speed * dt * 30.0  # 30 = escala visual

    @property
    def speed_kmh(self):
        """Velocidad en km/h para mostrar en el velocímetro."""
        return abs(self.speed) * 3.6

    def get_corners(self):
        """
        Devuelve las 4 esquinas del vehículo en el mundo (para colisiones AABB).
        Necesario para detectar si el auto tocó un cono o salió de la pista.
        """
        hw = self.WIDTH / 2
        hl = self.LENGTH / 2
        angle_rad = math.radians(self.angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Las 4 esquinas relativas al centro del auto
        local_corners = [
            (-hw, -hl), ( hw, -hl),
            ( hw,  hl), (-hw,  hl)
        ]

        world_corners = []
        for lx, lz in local_corners:
            wx = self.x + lx * cos_a - lz * sin_a
            wz = self.z + lx * sin_a + lz * cos_a
            world_corners.append((wx, wz))

        return world_corners