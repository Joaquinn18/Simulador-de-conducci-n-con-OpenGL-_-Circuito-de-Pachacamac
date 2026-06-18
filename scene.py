
import math
from OpenGL.GL import *
from OpenGL.GLU import *

# ─────────────────────────────────────────────────────────────────────────────
ROAD_W  = 7.0
HALF_W  = ROAD_W / 2.0
CURB_W  = 0.50
Y_ROAD  = 0.005
Y_MARK  = 0.010
Y_CURB  = 0.012

# ─────────────────────────────────────────────────────────────────────────────
# CONOS
# ─────────────────────────────────────────────────────────────────────────────
CONES_TROCHA = [
    (35.5,-18.0),(38.0,-20.5),(35.5,-23.0),
    (38.0,-25.5),(35.5,-28.0),
]
CONES_PARALELO = []
_EP_Z=-37.0; _EP_X1=-18.0; _EP_SEP=5.5
for _i in range(8):
    _cx = _EP_X1 + _i*_EP_SEP
    CONES_PARALELO += [(_cx,_EP_Z),(_cx,_EP_Z+6.5)]

CONES_DIAGONAL = []
_ED_CX=5.0; _ED_Z=-2.0
for _i in range(8):
    _cx = _ED_CX+_i*4.5-16.0
    CONES_DIAGONAL += [(_cx,_ED_Z),(_cx+2.5,_ED_Z-5.5)]

CONES_INTERSECTION = [
    (0.0,4.0),(3.5,4.0),(-3.5,4.0),(0.0,-0.5),
]

ALL_CONES = CONES_TROCHA+CONES_PARALELO+CONES_DIAGONAL+CONES_INTERSECTION
cone_hit_states = [False]*len(ALL_CONES)


# ─────────────────────────────────────────────────────────────────────────────
def init_lighting():
    glEnable(GL_LIGHTING); glEnable(GL_LIGHT0); glEnable(GL_LIGHT1)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glShadeModel(GL_SMOOTH)
    glLightfv(GL_LIGHT0,GL_POSITION,[0.55,1.0,0.35,0.0])
    glLightfv(GL_LIGHT0,GL_AMBIENT, [0.32,0.30,0.27,1.0])
    glLightfv(GL_LIGHT0,GL_DIFFUSE, [0.95,0.90,0.78,1.0])
    glLightfv(GL_LIGHT0,GL_SPECULAR,[0.50,0.45,0.35,1.0])
    glLightfv(GL_LIGHT1,GL_POSITION,[-0.3,0.8,-0.6,0.0])
    glLightfv(GL_LIGHT1,GL_AMBIENT, [0.07,0.09,0.16,1.0])
    glLightfv(GL_LIGHT1,GL_DIFFUSE, [0.10,0.14,0.26,1.0])
    glLightfv(GL_LIGHT1,GL_SPECULAR,[0.0,0.0,0.0,1.0])
    glMaterialfv(GL_FRONT_AND_BACK,GL_SPECULAR,[0.12,0.11,0.09,1.0])
    glMaterialf(GL_FRONT_AND_BACK,GL_SHININESS,22.0)


# ─────────────────────────────────────────────────────────────────────────────
# CIELO
# ─────────────────────────────────────────────────────────────────────────────
def draw_skybox():
    glDisable(GL_LIGHTING); glDisable(GL_DEPTH_TEST)
    S = 500.0
    glBegin(GL_QUADS); glColor3f(0.27,0.50,0.88)
    for v in [(-S,S,-S),(S,S,-S),(S,S,S),(-S,S,S)]: glVertex3f(*v)
    glEnd()
    sky=(0.27,0.50,0.88); horiz=(0.72,0.86,0.97)
    walls=[
        [(-S,-S,-S),(S,-S,-S),(S,S,-S),(-S,S,-S)],
        [(S,-S,S),(-S,-S,S),(-S,S,S),(S,S,S)],
        [(-S,-S,S),(-S,-S,-S),(-S,S,-S),(-S,S,S)],
        [(S,-S,-S),(S,-S,S),(S,S,S),(S,S,-S)],
    ]
    for w in walls:
        glBegin(GL_QUADS)
        glColor3f(*horiz); glVertex3f(*w[0])
        glColor3f(*horiz); glVertex3f(*w[1])
        glColor3f(*sky);   glVertex3f(*w[2])
        glColor3f(*sky);   glVertex3f(*w[3])
        glEnd()
    glPushMatrix(); glTranslatef(60,110,-300)
    glColor3f(1.0,0.97,0.84)
    glBegin(GL_POLYGON)
    for i in range(32):
        a=2*math.pi*i/32; glVertex3f(16*math.cos(a),16*math.sin(a),0)
    glEnd(); glPopMatrix()
    glEnable(GL_DEPTH_TEST); glEnable(GL_LIGHTING)


# ─────────────────────────────────────────────────────────────────────────────
# SUELO Y PISTA
# ─────────────────────────────────────────────────────────────────────────────
def _asp(x1,z1,x2,z2,y=Y_ROAD,col=(0.34,0.34,0.36)):
    glColor3f(*col); glNormal3f(0,1,0)
    glBegin(GL_QUADS)
    glVertex3f(x1,y,z1); glVertex3f(x2,y,z1)
    glVertex3f(x2,y,z2); glVertex3f(x1,y,z2)
    glEnd()

def _island(x1,x2,z1,z2,col=(0.22,0.58,0.14)):
    glColor3f(*col); glNormal3f(0,1,0)
    glBegin(GL_QUADS)
    glVertex3f(x1,0.002,z1); glVertex3f(x2,0.002,z1)
    glVertex3f(x2,0.002,z2); glVertex3f(x1,0.002,z2)
    glEnd()


def draw_ground():
    # Césped base
    glColor3f(0.28,0.52,0.18); glNormal3f(0,1,0)
    glBegin(GL_QUADS)
    glVertex3f(-90,0,-70); glVertex3f(90,0,-70)
    glVertex3f(90,0,60);   glVertex3f(-90,0,60)
    glEnd()

    # Isletas interiores verdes
    _island(-32.0,-8.0, -38.0, 8.0)
    _island(-16.0, 37.0,-38.0,-32.0)    # isleta norte (sobre paralelo)
    _island(-16.0,-8.0,   6.0,30.0)    # isleta salida

    # ── Asfalto principal ──────────────────────────────────────────────
    _asp(31.0, -45.0, 46.0, 35.0)       # recta Este completa
    _asp(-22.0,-45.0, 46.0,-32.0)       # recta Norte
    _asp(-53.0,-32.0,-32.0, 22.0)       # recta Oeste AMPLIADA hasta -53 para óvalo
    _asp(-14.0, -9.0, 38.0,  8.0)       # intersección
    _asp(-14.0,  8.0,  6.0, 35.0)       # salida sur

    # Transición NW → Óvalo: rellena el hueco entre recta oeste y el anillo
    _asp(-53.0, -5.0, -22.0, 25.0)      # zona amplia del óvalo

    # Zona estacionamiento paralelo
    _asp(-20.0,-45.0, 37.0,-36.0)

    # Zona estacionamiento diagonal
    _asp(-14.0, -9.5, 37.0,  7.0)

    # Zona trocha
    glColor3f(0.32,0.32,0.34); glNormal3f(0,1,0)
    glBegin(GL_QUADS)
    glVertex3f(31.0,Y_ROAD+0.001,-32.0); glVertex3f(45.0,Y_ROAD+0.001,-32.0)
    glVertex3f(45.0,Y_ROAD+0.001,-16.0); glVertex3f(31.0,Y_ROAD+0.001,-16.0)
    glEnd()

    # Via de entrada/salida
    _asp(35.0,28.0,46.0,48.0)
    _asp(-8.0,28.0, 6.0,48.0)

    # ── Marcas y bordillos ─────────────────────────────────────────────
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_POLYGON_OFFSET_FILL); glPolygonOffset(-1,-1)
    _draw_markings()
    _draw_curbs()
    _draw_zone_delimiters()   # ← NUEVO: franjas de color por zona
    glDisable(GL_POLYGON_OFFSET_FILL)
    glEnable(GL_DEPTH_TEST); glEnable(GL_LIGHTING)


def _mark(x1,z1,x2,z2,y=Y_MARK):
    glBegin(GL_QUADS)
    glVertex3f(x1,y,z1); glVertex3f(x2,y,z1)
    glVertex3f(x2,y,z2); glVertex3f(x1,y,z2)
    glEnd()


def _draw_markings():
    glColor3f(0.94,0.94,0.94)
    # Línea central recta Este
    z=-31.5
    while z<27.0:
        _mark(37.88,z,38.12,z+2.5); z+=5.5
    # Línea central recta Norte
    x=-20.0
    while x<36.0:
        _mark(x,-37.12,x+2.5,-36.88); x+=5.5
    # Línea central recta Oeste
    # La recta va de x=-53 a x=-32 → centro real en x=-42.5
    z=-30.0
    while z<20.0:
        _mark(-42.62,z,-42.38,z+2.5); z+=5.5

    # Flechas de dirección en la Recta Oeste (apuntan hacia el Sur, hacia el óvalo)
    glColor3f(0.94,0.94,0.94)
    for arrow_z in [-24.0, -10.0, 4.0, 16.0]:
        # Cuerpo de la flecha (rectángulo estrecho)
        _mark(-43.2, arrow_z, -41.8, arrow_z + 3.5)
        # Punta triangular (simulada con dos quads oblicuos)
        glBegin(GL_TRIANGLES)
        glVertex3f(-44.2, Y_MARK+0.001, arrow_z)      # izquierda base
        glVertex3f(-40.8, Y_MARK+0.001, arrow_z)      # derecha base
        glVertex3f(-42.5, Y_MARK+0.001, arrow_z-2.2)  # punta al sur
        glEnd()
    # Línea de llegada (roja)
    glColor3f(0.90,0.08,0.08)
    _mark(-8.0,29.8,6.0,30.5)
    # Cebra en la intersección
    glColor3f(0.94,0.94,0.94)
    for i in range(4):
        z0=-6.0+i*2.2
        _mark(-6.0,z0,6.0,z0+1.1)
    # Zona trocha: bordes amarillos
    glColor3f(1.0,0.85,0.0)
    _mark(31.0,-32.12,45.0,-31.88)
    _mark(31.0,-16.12,45.0,-15.88)
    # Divisiones paralelo
    glColor3f(1.0,0.88,0.0)
    for i in range(8):
        cx=_EP_X1+i*_EP_SEP
        _mark(cx-0.08,-43.5,cx+0.08,-36.0)
    # Divisiones diagonal (a 45°)
    glColor3f(1.0,0.88,0.0)
    for i in range(8):
        cx=-10.0+i*6.5
        x0,z0=cx,-7.5; x1,z1=cx+5.0,5.5
        dx=x1-x0; dz=z1-z0; ln=math.sqrt(dx*dx+dz*dz)
        nx=-dz/ln*0.10; nz=dx/ln*0.10
        glBegin(GL_QUADS)
        glVertex3f(x0-nx,Y_MARK+0.002,z0-nz); glVertex3f(x0+nx,Y_MARK+0.002,z0+nz)
        glVertex3f(x1+nx,Y_MARK+0.002,z1+nz); glVertex3f(x1-nx,Y_MARK+0.002,z1-nz)
        glEnd()
    # Bandera cuadros en llegada
    for col_i in range(14):
        for row_i in range(2):
            if (col_i+row_i)%2==0: glColor3f(0.10,0.10,0.10)
            else:                   glColor3f(0.95,0.95,0.95)
            x0=-8.0+col_i*1.0; z0=-36.5+row_i*1.0
            _mark(x0,z0,x0+1.0,z0+1.0)


def _draw_curbs():
    seg=1.5
    def cz(x1,x2,zs,ze):
        n=int(abs(ze-zs)/seg)
        s=1 if ze>zs else -1
        for i in range(n):
            z0=zs+i*seg*s; z1=z0+seg*s
            glColor3f(0.96,0.96,0.96) if i%2==0 else glColor3f(0.86,0.13,0.10)
            glNormal3f(0,1,0); glBegin(GL_QUADS)
            glVertex3f(x1,Y_CURB,z0); glVertex3f(x2,Y_CURB,z0)
            glVertex3f(x2,Y_CURB,z1); glVertex3f(x1,Y_CURB,z1)
            glEnd()
    def cx(xs,xe,z1,z2):
        n=int(abs(xe-xs)/seg)
        s=1 if xe>xs else -1
        for i in range(n):
            x0=xs+i*seg*s; x1=x0+seg*s
            glColor3f(0.96,0.96,0.96) if i%2==0 else glColor3f(0.86,0.13,0.10)
            glNormal3f(0,1,0); glBegin(GL_QUADS)
            glVertex3f(x0,Y_CURB,z1); glVertex3f(x1,Y_CURB,z1)
            glVertex3f(x1,Y_CURB,z2); glVertex3f(x0,Y_CURB,z2)
            glEnd()
    cz(44.5,45.0,-45.0,35.0)
    cz(31.0,31.5,-45.0,35.0)
    cx(-22.0,46.0,-42.5,-42.0)
    cx(-22.0,46.0,-32.5,-32.0)
    cz(-53.0,-52.5,-32.0,22.0)
    cz(-32.5,-32.0,-32.0,22.0)


def _draw_zone_delimiters():
    """
    Franjas delgadas de color en los bordes de cada zona para que el
    conductor sepa dónde empieza/termina cada maniobra.
    Amarillo = estac. paralelo, Naranja = diagonal, Cian = trocha,
    Violeta = óvalo, Verde = salida.
    """
    def stripe(x1,z1,x2,z2,col):
        glColor3f(*col)
        _mark(x1,z1,x2,z2,y=Y_MARK+0.003)

    # Recta Oeste: franja cian en borde norte (entrada) y sur (llegada al óvalo)
    stripe(-53.0,-32.5,-32.0,-32.0,(0.10,0.85,0.90))   # entrada norte
    stripe(-53.0, 22.0,-32.0, 22.5,(0.10,0.85,0.90))   # salida sur (óvalo)
    # Trocha: bordes cian
    stripe(30.5,-32.0,31.5,-32.0,(0.10,0.85,0.90))
    stripe(30.5,-16.0,31.5,-16.0,(0.10,0.85,0.90))
    # Paralelo: bordes amarillos anchos
    stripe(-20.5,-43.5,37.5,-43.0,(1.0,0.85,0.0))
    stripe(-20.5,-36.5,37.5,-36.0,(1.0,0.85,0.0))
    # Diagonal: bordes naranja
    stripe(-14.5,-9.5,37.5,-9.0,(1.0,0.55,0.0))
    stripe(-14.5,6.5,37.5,7.0,(1.0,0.55,0.0))
    # Salida: línea verde
    stripe(-8.5,29.5,6.5,30.0,(0.15,0.90,0.35))
    # Entrada óvalo (borde violeta)
    stripe(-53.0,-3.0,-32.0,-2.5,(0.65,0.25,0.90))
    stripe(-53.0,22.5,-32.0,23.0,(0.65,0.25,0.90))


# ─────────────────────────────────────────────────────────────────────────────
# ÓVALO COMPLETO
# ─────────────────────────────────────────────────────────────────────────────
def _draw_ovalo():
    """
    Óvalo con calzada anular, isleta central, bordillos, ramales de
    entrada/salida completamente conectados con la recta Oeste.
    """
    cx, cz  = -36.0, 10.0
    r_road  = 13.0
    r_inner = 5.5
    n       = 64

    # Fondo verde de área
    glColor3f(0.22,0.58,0.14); glNormal3f(0,1,0)
    glBegin(GL_POLYGON)
    r_area = r_road+4.0
    for i in range(n):
        a=2*math.pi*i/n
        glVertex3f(cx+r_area*math.cos(a),0.002,cz+r_area*math.sin(a))
    glEnd()

    # Isleta central
    glColor3f(0.20,0.62,0.14); glNormal3f(0,1,0)
    glBegin(GL_POLYGON)
    for i in range(n):
        a=2*math.pi*i/n
        glVertex3f(cx+r_inner*math.cos(a),0.004,cz+r_inner*math.sin(a))
    glEnd()

    # Calzada anular
    glColor3f(0.34,0.34,0.36); glNormal3f(0,1,0)
    glBegin(GL_QUAD_STRIP)
    for i in range(n+1):
        a=2*math.pi*i/n
        glVertex3f(cx+r_road *math.cos(a),Y_ROAD,cz+r_road *math.sin(a))
        glVertex3f(cx+r_inner*math.cos(a),Y_ROAD,cz+r_inner*math.sin(a))
    glEnd()

    # Ramal Este: conecta el anillo con la recta Oeste (x=-32)
    # El anillo llega hasta cx+r_road = -36+13 = -23; la recta oeste baja hasta x=-32
    # Necesitamos asfalto en x=-32..-23 para la franja que viene del norte
    _asp(-36.0, cz-r_road, -22.0, cz+r_road)   # relleno entre anillo y recta oeste

    # Ramal Sur: salida hacia estacionamiento diagonal
    _asp(-38.0, cz-2.0, -14.0, cz+r_road+2.0)

    # Ramal Norte completo: viene de la curva NW
    # La curva NW conecta en x=-32, z=-32; el óvalo está en cz=10
    # Necesitamos asfalto continuo en x=-53..-32 de z=-32 hasta z=23
    _asp(-53.0, -32.0, -30.0, 23.0)    # corredor lateral que incluye todo el giro

    # Marcas viales del óvalo
    glDisable(GL_LIGHTING)
    r_mid=(r_road+r_inner)/2
    glColor3f(1.0,0.88,0.0); glLineWidth(2.0)
    for i in range(32):
        if i%2==0:
            a0=2*math.pi*i/32; a1=2*math.pi*(i+1)/32
            glBegin(GL_LINES)
            glVertex3f(cx+r_mid*math.cos(a0),Y_MARK,cz+r_mid*math.sin(a0))
            glVertex3f(cx+r_mid*math.cos(a1),Y_MARK,cz+r_mid*math.sin(a1))
            glEnd()
    glLineWidth(1.0)

    # Bordillo exterior rojo/blanco
    seg_a=2*math.pi/48
    for i in range(48):
        a0=i*seg_a; a1=(i+1)*seg_a
        glColor3f(0.96,0.96,0.96) if i%2==0 else glColor3f(0.86,0.13,0.10)
        r_ci=r_road; r_co=r_road+0.6
        glBegin(GL_QUADS); glNormal3f(0,1,0)
        glVertex3f(cx+r_ci*math.cos(a0),Y_CURB,cz+r_ci*math.sin(a0))
        glVertex3f(cx+r_co*math.cos(a0),Y_CURB,cz+r_co*math.sin(a0))
        glVertex3f(cx+r_co*math.cos(a1),Y_CURB,cz+r_co*math.sin(a1))
        glVertex3f(cx+r_ci*math.cos(a1),Y_CURB,cz+r_ci*math.sin(a1))
        glEnd()

    # Bordillo de la isleta (blanco)
    for i in range(32):
        a0=2*math.pi*i/32; a1=2*math.pi*(i+1)/32
        r_ci=r_inner; r_co=r_inner+0.4
        glColor3f(0.94,0.94,0.94)
        glBegin(GL_QUADS); glNormal3f(0,1,0)
        glVertex3f(cx+r_ci*math.cos(a0),Y_CURB,cz+r_ci*math.sin(a0))
        glVertex3f(cx+r_co*math.cos(a0),Y_CURB,cz+r_co*math.sin(a0))
        glVertex3f(cx+r_co*math.cos(a1),Y_CURB,cz+r_co*math.sin(a1))
        glVertex3f(cx+r_ci*math.cos(a1),Y_CURB,cz+r_ci*math.sin(a1))
        glEnd()

    glEnable(GL_LIGHTING)


def _draw_zona_paralelo():
    _asp(-20.0,-45.0,37.0,-36.0)
    glColor3f(1.0,0.88,0.0); glNormal3f(0,1,0)
    for i in range(8):
        cx=_EP_X1+i*_EP_SEP
        glBegin(GL_QUADS)
        glVertex3f(cx-0.08,Y_MARK+0.002,-43.5); glVertex3f(cx+0.08,Y_MARK+0.002,-43.5)
        glVertex3f(cx+0.08,Y_MARK+0.002,-36.0); glVertex3f(cx-0.08,Y_MARK+0.002,-36.0)
        glEnd()
    for i in range(7):
        cx2=_EP_X1+i*_EP_SEP+2.75
        col=(0.28,0.55,0.22) if i%2==0 else (0.22,0.45,0.55)
        glColor3f(*col); glNormal3f(0,1,0)
        glBegin(GL_QUADS)
        glVertex3f(cx2-2.3,0.003,-42.8); glVertex3f(cx2+2.3,0.003,-42.8)
        glVertex3f(cx2+2.3,0.003,-36.8); glVertex3f(cx2-2.3,0.003,-36.8)
        glEnd()


def _draw_zona_diagonal():
    _asp(-14.0,-8.5,37.0,6.5)
    glColor3f(1.0,0.88,0.0); glNormal3f(0,1,0)
    for i in range(8):
        cx2=-10.0+i*6.5
        x0,z0=cx2,-7.5; x1,z1=cx2+5.0,5.5
        dx=x1-x0; dz=z1-z0; ln=math.sqrt(dx*dx+dz*dz)
        nx=-dz/ln*0.10; nz=dx/ln*0.10
        glBegin(GL_QUADS)
        glVertex3f(x0-nx,Y_MARK+0.002,z0-nz); glVertex3f(x0+nx,Y_MARK+0.002,z0+nz)
        glVertex3f(x1+nx,Y_MARK+0.002,z1+nz); glVertex3f(x1-nx,Y_MARK+0.002,z1-nz)
        glEnd()


def _draw_entry_road():
    _asp(35.0,28.0,46.0,48.0)
    _asp(-8.0,28.0, 6.0,48.0)
    glColor3f(0.90,0.08,0.08)
    glBegin(GL_QUADS); glNormal3f(0,1,0)
    glVertex3f(35.0,Y_MARK,27.8); glVertex3f(46.0,Y_MARK,27.8)
    glVertex3f(46.0,Y_MARK,28.5); glVertex3f(35.0,Y_MARK,28.5)
    glEnd()


# ─────────────────────────────────────────────────────────────────────────────
# CONOS
# ─────────────────────────────────────────────────────────────────────────────
def draw_cone(cx, cz, is_hit=False):
    glPushMatrix(); glTranslatef(cx,0.0,cz)
    if is_hit: glRotatef(88.0,1,0,0)
    glColor3f(0.13,0.13,0.13); n=14
    glBegin(GL_POLYGON); glNormal3f(0,1,0)
    for i in range(n):
        a=2*math.pi*i/n; glVertex3f(0.22*math.cos(a),0.004,0.22*math.sin(a))
    glEnd()
    height,base_r,tip_r=0.72,0.16,0.013; nf=18
    for i in range(nf):
        a0=2*math.pi*i/nf; a1=2*math.pi*(i+1)/nf; mid=(a0+a1)/2
        glColor3f(0.97,0.42,0.03) if (i//3)%2==0 else glColor3f(0.97,0.96,0.94)
        glBegin(GL_TRIANGLES); glNormal3f(math.cos(mid)*0.9,0.38,math.sin(mid)*0.9)
        glVertex3f(base_r*math.cos(a0),0.006,base_r*math.sin(a0))
        glVertex3f(base_r*math.cos(a1),0.006,base_r*math.sin(a1))
        glVertex3f(tip_r*math.cos(mid),height,tip_r*math.sin(mid))
        glEnd()
    glPopMatrix()

def draw_all_cones():
    for i,(cx,cz) in enumerate(ALL_CONES):
        draw_cone(cx,cz,is_hit=cone_hit_states[i])


# ─────────────────────────────────────────────────────────────────────────────
# SEÑALES
# ─────────────────────────────────────────────────────────────────────────────
def _pole(x,z,h=2.8):
    glColor3f(0.46,0.46,0.50); n=8; r=0.045
    glBegin(GL_QUAD_STRIP)
    for i in range(n+1):
        a=2*math.pi*i/n; glNormal3f(math.cos(a),0,math.sin(a))
        glVertex3f(x+r*math.cos(a),0,z+r*math.sin(a))
        glVertex3f(x+r*math.cos(a),h,z+r*math.sin(a))
    glEnd()

def _semaforo(x,z):
    _pole(x,z,h=3.5)
    glPushMatrix(); glTranslatef(x,3.5,z)
    glColor3f(0.10,0.10,0.10)
    glBegin(GL_QUADS); glNormal3f(0,0,-1)
    for v in [(-0.18,-0.55,-0.08),(0.18,-0.55,-0.08),(0.18,0.55,-0.08),(-0.18,0.55,-0.08)]:
        glVertex3f(*v)
    glEnd()
    for ly,col in [(0.32,(0.90,0.08,0.08)),(0.00,(0.90,0.60,0.05)),(-0.32,(0.08,0.82,0.12))]:
        glColor3f(*col); glBegin(GL_POLYGON); glNormal3f(0,0,-1)
        for i in range(12):
            a=2*math.pi*i/12; glVertex3f(0.10*math.cos(a),ly+0.10*math.sin(a),-0.09)
        glEnd()
    glPopMatrix()

def _pare(x,z):
    _pole(x,z); glPushMatrix(); glTranslatef(x,2.8,z)
    glColor3f(0.86,0.06,0.06); n=8
    glBegin(GL_POLYGON); glNormal3f(0,0,-1)
    for i in range(n):
        a=math.pi/8+2*math.pi*i/n; glVertex3f(0.42*math.cos(a),0.42*math.sin(a),-0.02)
    glEnd()
    glColor3f(0.96,0.96,0.96); glLineWidth(3); glBegin(GL_LINE_LOOP)
    for i in range(n):
        a=math.pi/8+2*math.pi*i/n; glVertex3f(0.39*math.cos(a),0.39*math.sin(a),-0.025)
    glEnd(); glLineWidth(1); glPopMatrix()

def draw_signs():
    glDisable(GL_LIGHTING)
    _semaforo(30.5,8.0); _semaforo(-6.0,8.5)
    _semaforo(30.5,-15.5); _semaforo(-32.5,8.0)
    _pare(44.5,28.5); _pare(-5.0,35.0)
    glEnable(GL_LIGHTING)


# ─────────────────────────────────────────────────────────────────────────────
# BANDERINES DE ZONA (postes con banderita de color por maniobra)
# ─────────────────────────────────────────────────────────────────────────────
def _banderín(x, z, col):
    """Poste con banderita triangular de color."""
    glPushMatrix(); glTranslatef(x, 0, z)
    # Poste
    glColor3f(0.55,0.55,0.55); glLineWidth(2.5)
    glBegin(GL_LINES); glVertex3f(0,0,0); glVertex3f(0,2.5,0); glEnd()
    glLineWidth(1.0)
    # Banderita
    glColor3f(*col)
    glBegin(GL_TRIANGLES); glNormal3f(0,0,-1)
    glVertex3f(0,2.5,0); glVertex3f(0.8,2.2,0); glVertex3f(0,1.9,0)
    glEnd()
    glPopMatrix()

def draw_zone_flags():
    """Banderines en las esquinas de cada zona para delimitar visualmente."""
    glDisable(GL_LIGHTING)
    cy=(0.10,0.85,0.90)   # cian = trocha
    ya=(1.00,0.85,0.00)   # amarillo = paralelo
    or_=(1.00,0.55,0.00)  # naranja = diagonal
    vi=(0.65,0.25,0.90)   # violeta = óvalo
    gr=(0.15,0.90,0.35)   # verde = salida

    # Trocha
    _banderín(31.0,-32.5,cy); _banderín(45.0,-32.5,cy)
    _banderín(31.0,-15.5,cy); _banderín(45.0,-15.5,cy)
    # Paralelo
    _banderín(-20.0,-44.0,ya); _banderín(37.0,-44.0,ya)
    _banderín(-20.0,-36.0,ya); _banderín(37.0,-36.0,ya)
    # Diagonal
    _banderín(-14.0,-9.5,or_); _banderín(37.0,-9.5,or_)
    _banderín(-14.0,7.0,or_);  _banderín(37.0,7.0,or_)
    # Óvalo
    _banderín(-53.0,-2.5,vi); _banderín(-22.0,-2.5,vi)
    _banderín(-53.0,23.0,vi); _banderín(-22.0,23.0,vi)
    # Salida
    _banderín(-8.0,30.0,gr);  _banderín(6.0,30.0,gr)

    glEnable(GL_LIGHTING)


# ─────────────────────────────────────────────────────────────────────────────
# EDIFICIO TOURING
# ─────────────────────────────────────────────────────────────────────────────
def draw_touring_building():
    glPushMatrix(); glTranslatef(0.0,0,-48.0)
    glColor3f(0.86,0.82,0.76)
    _wb(-15,0,15,4.0,6)
    glColor3f(0.68,0.20,0.12); _rb(-15,4.0,15,4.0,6,2.0)
    glColor3f(0.08,0.22,0.62)
    glBegin(GL_QUADS); glNormal3f(0,0,1)
    glVertex3f(-8,3.2,0.01); glVertex3f(8,3.2,0.01)
    glVertex3f(8,4.0,0.01);  glVertex3f(-8,4.0,0.01)
    glEnd()
    glPopMatrix()
    for pos in [(44.0,-38.0),(-42.0,-38.0),(44.0,22.0)]:
        glPushMatrix(); glTranslatef(*pos,0)
        glColor3f(0.84,0.80,0.72); _wb(-1.2,0,1.2,2.5,1.2)
        glColor3f(0.65,0.18,0.10); _rb(-1.2,2.5,1.2,2.5,1.2,0.7)
        glPopMatrix()

def _wb(x1,y1,x2,y2,d):
    glNormal3f(0,0,1)
    for z,n in [(0,(0,0,1)),(-d,(0,0,-1))]:
        glBegin(GL_QUADS); glNormal3f(*n)
        glVertex3f(x1,y1,z); glVertex3f(x2,y1,z)
        glVertex3f(x2,y2,z); glVertex3f(x1,y2,z); glEnd()
    for xw,nx in [(x1,-1),(x2,1)]:
        glBegin(GL_QUADS); glNormal3f(nx,0,0)
        glVertex3f(xw,y1,0); glVertex3f(xw,y1,-d)
        glVertex3f(xw,y2,-d); glVertex3f(xw,y2,0); glEnd()

def _rb(x1,by,x2,_,d,rh):
    cx2=(x1+x2)/2
    for z,nz in [(0,1),(-d,-1)]:
        glBegin(GL_TRIANGLES); glNormal3f(0,0,nz)
        glVertex3f(x1,by,z); glVertex3f(x2,by,z)
        glVertex3f(cx2,by+rh,z); glEnd()
    for xw,nx in [(x1,-1),(x2,1)]:
        glBegin(GL_QUADS); glNormal3f(nx*0.7,0.7,0)
        glVertex3f(xw,by,0); glVertex3f(xw,by,-d)
        glVertex3f(cx2,by+rh,-d); glVertex3f(cx2,by+rh,0); glEnd()


# ─────────────────────────────────────────────────────────────────────────────
# ÁRBOLES
# ─────────────────────────────────────────────────────────────────────────────
def draw_trees():
    positions=[
        (-20,-52),(-10,-52),(0,-52),(10,-52),(20,-52),
        (-20,50),(-10,50),(0,50),(10,50),(20,50),
        (-58,-20),(-58,0),(-58,20),
        (54,-20),(54,0),(54,20),
        (-48,-5),(-48,12),(-48,28),
        (-22,-2),(5,-5),(20,-5),(20,-15),
    ]
    for tx,tz in positions: _tree(tx,tz)

def _tree(tx,tz):
    glPushMatrix(); glTranslatef(tx,0,tz)
    glColor3f(0.28,0.17,0.06); r=0.18; n=8
    glBegin(GL_QUAD_STRIP)
    for i in range(n+1):
        a=2*math.pi*i/n; glNormal3f(math.cos(a),0,math.sin(a))
        glVertex3f(r*math.cos(a),0,r*math.sin(a))
        glVertex3f(r*math.cos(a),1.4,r*math.sin(a))
    glEnd()
    glColor3f(0.15,0.48,0.15)
    for by,cr,ch in [(1.2,1.3,1.1),(1.9,1.05,0.9),(2.5,0.78,0.78),(3.0,0.50,0.65)]:
        n2=14; glBegin(GL_TRIANGLES)
        for i in range(n2):
            a0=2*math.pi*i/n2; a1=2*math.pi*(i+1)/n2; m=(a0+a1)/2
            glNormal3f(math.cos(m)*0.7,0.5,math.sin(m)*0.7)
            glVertex3f(cr*math.cos(a0),by,cr*math.sin(a0))
            glVertex3f(cr*math.cos(a1),by,cr*math.sin(a1))
            glVertex3f(0,by+ch,0)
        glEnd()
    glPopMatrix()


# ─────────────────────────────────────────────────────────────────────────────
def draw_full_scene():
    draw_skybox()
    draw_ground()
    _draw_ovalo()
    _draw_zona_paralelo()
    _draw_zona_diagonal()
    _draw_entry_road()
    draw_all_cones()
    draw_signs()
    draw_zone_flags()
    draw_trees()
    draw_touring_building()
