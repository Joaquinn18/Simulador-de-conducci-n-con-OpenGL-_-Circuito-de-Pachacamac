# collision.py  —  Versión 4.2
"""
Límites ampliados para permitir el giro completo del óvalo.
El óvalo tiene centro en x=-36 y radio exterior de 12m → llega a x=-48.
Ampliamos min_x a -53 con margen extra.
"""
import math

TRACK_BOUNDS = {
    'min_x': -53.0,   # antes -43 → cortaba el giro del óvalo en x≈-48
    'max_x':  47.0,
    'min_z': -45.0,
    'max_z':  36.0,
}

CONE_COLLISION_RADIUS = 0.55
CONE_PENALTY = 5


def check_cone_collision(vehicle_x, vehicle_z, cones):
    for i, (cx, cz) in enumerate(cones):
        dx = vehicle_x - cx
        dz = vehicle_z - cz
        if math.sqrt(dx*dx + dz*dz) < CONE_COLLISION_RADIUS:
            return True, i
    return False, -1


def clamp_to_track(vehicle):
    hit = False
    if vehicle.x < TRACK_BOUNDS['min_x']:
        vehicle.x = TRACK_BOUNDS['min_x']; hit = True
    elif vehicle.x > TRACK_BOUNDS['max_x']:
        vehicle.x = TRACK_BOUNDS['max_x']; hit = True
    if vehicle.z < TRACK_BOUNDS['min_z']:
        vehicle.z = TRACK_BOUNDS['min_z']; hit = True
    elif vehicle.z > TRACK_BOUNDS['max_z']:
        vehicle.z = TRACK_BOUNDS['max_z']; hit = True
    if hit:
        vehicle.speed *= 0.15
    return hit
