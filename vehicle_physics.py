
import math


GEAR_TABLE = {
    -1: (2.5,  800, 2500, 0.70),   # Reversa
     0: (0.0,  800,  800, 0.00),   # Neutro
     1: (3.2, 1000, 3500, 1.10),   # 1ª
     2: (5.5, 1200, 4000, 1.00),   # 2ª
     3: (8.0, 1400, 4500, 0.95),   # 3ª
     4: (11.0,1600, 5000, 0.88),   # 4ª
     5: (14.5,1800, 5500, 0.80),   # 5ª
     6: (19.0,2000, 6000, 0.72),   # 6ª
}
RPM_IDLE        = 850
RPM_REDLINE     = 6500
RPM_MAX_DISPLAY = 8000


class VehiclePhysics:
    WHEELBASE    = 2.70
    WIDTH        = 1.80
    LENGTH       = 4.20
    MAX_SPEED_FWD = 8.0
    MAX_SPEED_REV = 2.5
    MAX_STEER_DEG = 30.0
    BRAKE_RATE    = 7.0
    DRAG_RATE     = 1.8
    STEER_RATE    = 80.0
    STEER_RETURN  = 120.0

    def __init__(self, start_x=0.0, start_z=5.0, start_angle=0.0):
        self.x     = start_x
        self.z     = start_z
        self.angle = start_angle
        self.speed        = 0.0
        self.steer_angle  = 0.0
        self.is_braking   = False
        self.is_reversing = False
        self.wheel_rotation = 0.0
        self.exam_phase  = 0
        self.cones_hit   = 0
        self.penalty_pts = 0
        # Transmisión manual
        self.gear = 1
        self.rpm  = RPM_IDLE

    def shift_up(self):
        if self.gear < 6:
            self.gear += 1
            return True
        return False

    def shift_down(self):
        if self.gear > -1:
            self.gear -= 1
            return True
        return False

    @property
    def gear_label(self):
        if self.gear ==  0: return "N"
        if self.gear == -1: return "R"
        return str(self.gear)

    def update(self, keys_pressed, dt):
        from pygame.locals import K_w, K_s, K_a, K_d, K_UP, K_DOWN, K_LEFT, K_RIGHT
        gas   = keys_pressed[K_w] or keys_pressed[K_UP]
        brake = keys_pressed[K_s] or keys_pressed[K_DOWN]
        left  = keys_pressed[K_a] or keys_pressed[K_LEFT]
        right = keys_pressed[K_d] or keys_pressed[K_RIGHT]

        self.is_braking   = False
        self.is_reversing = self.gear == -1

        if self.gear == 0:
            if self.speed > 0:  self.speed = max(self.speed - self.DRAG_RATE * dt, 0.0)
            elif self.speed < 0: self.speed = min(self.speed + self.DRAG_RATE * dt, 0.0)

        elif self.gear == -1:
            if gas:
                self.speed = max(self.speed - 2.5 * dt, -self.MAX_SPEED_REV)
            elif brake:
                self.speed = min(self.speed + self.BRAKE_RATE * dt, 0.0)
                self.is_braking = True
            else:
                self.speed = min(self.speed + self.DRAG_RATE * dt, 0.0)

        else:
            g     = GEAR_TABLE[self.gear]
            smax  = g[0]; acf = g[3]
            rpml  = g[1]; rpmh = g[2]
            if rpml <= self.rpm <= rpmh:
                pf = 1.0
            elif self.rpm < rpml:
                pf = max(0.25, self.rpm / rpml)
            else:
                pf = max(0.10, 1.0 - (self.rpm - rpmh) / 2000)
            ar = 3.5 * acf * pf

            if gas:
                if self.speed < smax:
                    self.speed = min(self.speed + ar * dt, smax)
                elif self.speed > smax:
                    self.speed = max(self.speed - self.DRAG_RATE * 1.5 * dt, smax)
            elif brake:
                if self.speed > 0.05:
                    self.speed = max(self.speed - self.BRAKE_RATE * dt, 0.0)
                    self.is_braking = True
                else:
                    self.speed = 0.0
            else:
                drag = self.DRAG_RATE * (1.0 + (3 - min(self.gear, 3)) * 0.3)
                if self.speed > 0:  self.speed = max(self.speed - drag * dt, 0.0)
                elif self.speed < 0: self.speed = min(self.speed + drag * dt, 0.0)

        # RPM
        if self.gear == 0:
            target_rpm = RPM_IDLE
        elif self.gear == -1:
            target_rpm = RPM_IDLE + abs(self.speed) / max(self.MAX_SPEED_REV,0.001) * 2000
        else:
            g = GEAR_TABLE[self.gear]
            r = abs(self.speed) / max(g[0], 0.001)
            target_rpm = g[1] + r * (g[2] - g[1])
            if gas: target_rpm = min(target_rpm * 1.12, RPM_REDLINE)
        rpm_spd = 4000 * dt
        self.rpm = self.rpm + rpm_spd if target_rpm > self.rpm else self.rpm - rpm_spd * 0.6
        self.rpm = max(RPM_IDLE, min(self.rpm, RPM_REDLINE))

        # Volante
        if left:
            self.steer_angle = max(self.steer_angle - self.STEER_RATE * dt, -self.MAX_STEER_DEG)
        elif right:
            self.steer_angle = min(self.steer_angle + self.STEER_RATE * dt,  self.MAX_STEER_DEG)
        else:
            sf = min(abs(self.speed) / max(self.MAX_SPEED_FWD, 0.01) + 0.3, 1.0)
            rs = self.STEER_RETURN * sf * dt
            if self.steer_angle > 0:   self.steer_angle = max(self.steer_angle - rs, 0.0)
            elif self.steer_angle < 0: self.steer_angle = min(self.steer_angle + rs, 0.0)

        # Cinemática
        if abs(self.speed) > 0.01:
            sr = math.radians(self.steer_angle)
            av = (self.speed / (self.WHEELBASE / math.tan(sr))) if abs(sr) > 0.001 else 0.0
            self.angle += math.degrees(av) * dt
            ar2 = math.radians(self.angle)
            self.x += self.speed * math.sin(ar2) * dt
            self.z -= self.speed * math.cos(ar2) * dt
        self.wheel_rotation += self.speed * dt * 30.0

    @property
    def speed_kmh(self):
        return abs(self.speed) * 3.6

    def get_corners(self):
        hw = self.WIDTH / 2; hl = self.LENGTH / 2
        a  = math.radians(self.angle)
        ca = math.cos(a);  sa = math.sin(a)
        return [(self.x + lx*ca - lz*sa, self.z + lx*sa + lz*ca)
                for lx,lz in [(-hw,-hl),(hw,-hl),(hw,hl),(-hw,hl)]]
