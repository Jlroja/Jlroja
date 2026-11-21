"""
☄️ BUILD & SMASH — juego en pixel art con tu gráfica de contribuciones de GitHub.

- Un ROBOT constructor con jetpack construye escaleras, peldaño por peldaño,
  desde el suelo hasta cada contribución.
- Un GÓLEM de piedra sube por la escalera y destruye la contribución a puñetazos.
- Entre más contribuciones tiene un día, más golpes aguanta el bloque.
- El marcador SCORE suma las contribuciones destruidas.

Uso:
    # Con datos reales (necesita la variable de entorno GH_TOKEN)
    python scripts/constructor_golem.py Jlroja --output assets/constructor-golem.gif

    # Con un JSON de prueba (mismo formato que gh-space-shooter --raw-output)
    python scripts/constructor_golem.py Jlroja --raw-input datos.json --output prueba.gif
"""

import argparse
import json
import math
import os
import random
from datetime import date

from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Lienzo en "pixeles de arte" (luego se escala x2 con vecino más cercano)
# ---------------------------------------------------------------------------
ESCALA = 2
PAD_X = 14
TOP = 14
CELDA = 6
PASO = 7
W = PAD_X * 2 + 52 * PASO          # 392
SUELO = 98                         # y del borde superior del suelo
H = 108

FPS = 15
DT = 1 / FPS

# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------
CIELO = (13, 17, 23)
CELDA_VACIA = (22, 27, 34)
NIVELES = {1: (14, 68, 41), 2: (0, 109, 50), 3: (38, 166, 65), 4: (57, 211, 83)}
ESTRELLA = [(70, 80, 100), (150, 160, 190), (230, 235, 255)]
SUELO_C = {"borde": (96, 84, 72), "ladrillo": (60, 50, 44), "junta": (38, 32, 28)}
ESCALERA_C = {"riel": (176, 120, 64), "peldano": (214, 160, 90), "sombra": (110, 72, 40)}
CHISPA = [(255, 240, 120), (255, 190, 60), (255, 255, 255)]
TEXTO = (230, 235, 255)
TEXTO_SOMBRA = (40, 50, 70)

ROBOT_PAL = {
    "o": (255, 150, 40),   # luz de antena (parpadea)
    "a": (130, 140, 150),  # antena
    "M": (180, 190, 200),  # metal claro
    "m": (120, 130, 145),  # metal oscuro
    "C": (60, 230, 230),   # visor
    "Y": (250, 200, 40),   # franja amarilla
    "W": (150, 155, 165),  # llave inglesa
    "d": (70, 78, 90),     # articulaciones
}
GOLEM_PAL = {
    "g": (70, 140, 60),    # musgo
    "G": (100, 175, 80),   # musgo claro
    "S": (118, 112, 106),  # piedra
    "s": (88, 82, 78),     # piedra oscura
    "E": (255, 150, 40),   # ojos brillantes
    "L": (240, 100, 30),   # grieta de lava
    "F": (100, 94, 90),    # puños
    "D": (60, 56, 52),     # sombra
}

# ---------------------------------------------------------------------------
# Sprites (cada caracter = 1 pixel de arte, '.' = transparente)
# ---------------------------------------------------------------------------
ROBOT = [
    "...o...",
    "...a...",
    ".MMMMM.",
    ".CCMMm.",
    ".MMMMm.",
    "..ddd..",
    "WMYYYMd",
    "W.MMMm.",
    "..d.d..",
]

GOLEM_QUIETO = [
    "....gGGg....",
    "...gSSSSg...",
    "..SSSSSSSS..",
    "..SEESSEES..",
    "..SSSSSSSs..",
    "..SsDDDDss..",
    ".SSSSSSSSSs.",
    "SSSSSLSSSSSs",
    "FFSSSSLSSsFF",
    "FFSSSSSSSsFF",
    "FF.SSSSSs.FF",
    "...SSSSSs...",
    "...SS..Ss...",
    "...SS..Ss...",
    "..SSS..SSs..",
    "..DDD..DDD..",
]

GOLEM_GOLPE = [
    "..FF....FF..",
    "..FF....FF..",
    "..SFgGGgFs..",
    "..SSSSSSSs..",
    "..SSSSSSSS..",
    "..SEESSEES..",
    "..SSSSSSSs..",
    "..SsDDDDss..",
    "..SSSSSSSs..",
    ".SSSSSLSSSs.",
    ".SSSSSSLSsS.",
    "..SSSSSSSs..",
    "...SSSSSs...",
    "...SSSSSs...",
    "...SS..Ss...",
    "...SS..Ss...",
    "..SSS..SSs..",
    "..DDD..DDD..",
]

PIERNAS_A = ["...SS..Ss...", "...SS...Ss..", "..SSS...SSs.", "..DDD...DDD."]
PIERNAS_B = ["...SS..Ss...", "..SS...Ss...", ".SSS...SSs..", ".DDD...DDD.."]

# Fuente 3x5 para el marcador
FUENTE = {
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"], "9": ["111", "101", "111", "001", "111"],
    "S": ["111", "100", "111", "001", "111"], "C": ["111", "100", "100", "100", "111"],
    "O": ["111", "101", "101", "101", "111"], "R": ["110", "101", "110", "101", "101"],
    "E": ["111", "100", "111", "100", "111"], "L": ["100", "100", "100", "100", "111"],
    "A": ["010", "101", "111", "101", "101"], "!": ["010", "010", "010", "000", "010"],
    " ": ["000", "000", "000", "000", "000"],
}


# ---------------------------------------------------------------------------
# Utilidades de dibujo
# ---------------------------------------------------------------------------
def pintar_sprite(px, sprite, pal, x, y):
    """Dibuja un sprite con su esquina superior izquierda en (x, y)."""
    for j, fila in enumerate(sprite):
        for i, ch in enumerate(fila):
            if ch != ".":
                xx, yy = int(x) + i, int(y) + j
                if 0 <= xx < W and 0 <= yy < H:
                    px[xx, yy] = pal[ch]


def rect(px, x0, y0, x1, y1, color):
    for yy in range(max(0, int(y0)), min(H, int(y1) + 1)):
        for xx in range(max(0, int(x0)), min(W, int(x1) + 1)):
            px[xx, yy] = color


def texto(px, s, x, y, color, tam=1):
    for k, ch in enumerate(s):
        glifo = FUENTE.get(ch, FUENTE[" "])
        for j, fila in enumerate(glifo):
            for i, b in enumerate(fila):
                if b == "1":
                    rect(px, x + (k * 4 + i) * tam, y + j * tam,
                         x + (k * 4 + i) * tam + tam - 1, y + j * tam + tam - 1, color)


def aclarar(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def col_x(c):
    return PAD_X + c * PASO


def fila_y(r):
    return TOP + r * PASO


# ---------------------------------------------------------------------------
# Estado del juego
# ---------------------------------------------------------------------------
class Juego:
    def __init__(self, datos, velocidad=1.0, semilla=7):
        self.vel = min(velocidad, 3.0)                  # velocidad de movimiento (con tope)
        self.turbo = max(1, math.ceil(velocidad / 3.0))  # peldaños y golpes por cuadro
        self.rnd = random.Random(semilla)
        self.bloques = {}       # (col, fila) -> vida restante
        self.nivel = {}         # (col, fila) -> nivel original
        self.cuenta = {}        # (col, fila) -> # contribuciones
        self.temblor = {}       # (col, fila) -> frames de temblor
        semanas = datos["weeks"][-52:]
        for c, semana in enumerate(semanas):
            for dia in semana["days"]:
                nivel = int(dia.get("level", 0))
                if nivel <= 0:
                    continue
                r = (date.fromisoformat(dia["date"]).weekday() + 1) % 7  # domingo = 0
                self.bloques[(c, r)] = nivel
                self.nivel[(c, r)] = nivel
                self.cuenta[(c, r)] = int(dia.get("count", nivel))
        self.escaleras = {}     # col -> y superior de la escalera
        self.particulas = []    # [x, y, vx, vy, vida, color]
        self.robot = [6.0, SUELO - 14.0]   # centro del robot
        self.golem = [10.0, float(SUELO)]  # (centro x, y de los pies)
        self.pose = "quieto"
        self.score = 0
        self.tick = 0
        self.mensaje = None
        self.estrellas = [(self.rnd.randrange(W), self.rnd.randrange(SUELO - 2),
                           self.rnd.randrange(3), self.rnd.randrange(40))
                          for _ in range(70)]

    # ---------------- acciones (generadores: 1 yield = 1 frame) ----------------
    def esperar(self, t):
        for _ in range(max(1, round(t / self.vel * FPS))):
            yield

    def mover_robot(self, tx, ty, rapidez=90):
        while True:
            dx, dy = tx - self.robot[0], ty - self.robot[1]
            d = math.hypot(dx, dy)
            paso = rapidez * self.vel * DT
            if d <= paso:
                self.robot = [tx, ty]
                yield
                return
            self.robot[0] += dx / d * paso
            self.robot[1] += dy / d * paso
            yield

    def caminar_golem(self, tx, rapidez=45):
        self.pose = "camina"
        while True:
            dx = tx - self.golem[0]
            paso = rapidez * self.vel * DT
            if abs(dx) <= paso:
                self.golem[0] = tx
                self.pose = "quieto"
                yield
                return
            self.golem[0] += math.copysign(paso, dx)
            yield

    def trepar_golem(self, ty, rapidez=40):
        self.pose = "trepa"
        while True:
            dy = ty - self.golem[1]
            paso = rapidez * self.vel * DT
            if abs(dy) <= paso:
                self.golem[1] = ty
                self.pose = "quieto"
                yield
                return
            self.golem[1] += math.copysign(paso, dy)
            yield

    def construir(self, c, tope):
        x0 = col_x(c)
        actual = self.escaleras.get(c, SUELO)
        yield from self.mover_robot(x0 + 12, actual - 6)
        while actual > tope:
            actual = max(tope, actual - 3 * self.turbo)
            self.escaleras[c] = actual
            self.robot = [x0 + 12, actual - 6]
            for _ in range(5):
                self.particulas.append([x0 + 3, actual, self.rnd.uniform(-25, 25),
                                        self.rnd.uniform(-35, 5), self.rnd.uniform(0.15, 0.35),
                                        self.rnd.choice(CHISPA)])
            yield from self.esperar(0.07)

    def golpear(self, c, r):
        clave = (c, r)
        while clave in self.bloques:
            self.pose = "golpe"
            self.bloques[clave] -= min(self.turbo, self.bloques[clave])
            self.temblor[clave] = 3
            bx, by = col_x(c) + 3, fila_y(r) + 5
            color = NIVELES[self.nivel[clave]]
            n = 4
            if self.bloques[clave] <= 0:
                del self.bloques[clave]
                self.score += self.cuenta[clave]
                n = 14
            for _ in range(n):
                self.particulas.append([bx + self.rnd.uniform(-3, 3), by - self.rnd.uniform(0, 5),
                                        self.rnd.uniform(-45, 45), self.rnd.uniform(-60, 10),
                                        self.rnd.uniform(0.3, 0.7),
                                        self.rnd.choice([color, aclarar(color, 1.4), (140, 130, 120)])])
            yield from self.esperar(0.13)
            self.pose = "quieto"
            yield from self.esperar(0.12)

    def paralelo(self, *gens):
        activos = list(gens)
        while True:
            siguientes = []
            for g in activos:
                try:
                    next(g)
                    siguientes.append(g)
                except StopIteration:
                    pass
            activos = siguientes
            if not activos:
                return
            yield

    def guion(self):
        yield from self.esperar(0.6)
        columnas = sorted({c for c, _ in self.bloques})
        for c in columnas:
            cx = col_x(c) + 3
            yield from self.paralelo(self.mover_robot(cx + 9, SUELO - 14),
                                     self.caminar_golem(cx))
            filas = sorted((r for (cc, r) in self.bloques if cc == c), reverse=True)
            for r in filas:
                pies = fila_y(r) + 6 + 18
                yield from self.construir(c, pies)
                yield from self.trepar_golem(pies)
                yield from self.golpear(c, r)
            yield from self.trepar_golem(SUELO, rapidez=70)
            tope = self.escaleras.pop(c, SUELO)
            for _ in range(10):
                self.particulas.append([col_x(c) + 3, self.rnd.uniform(tope, SUELO),
                                        self.rnd.uniform(-20, 20), self.rnd.uniform(-20, 0),
                                        self.rnd.uniform(0.2, 0.4), ESCALERA_C["peldano"]])
        yield from self.paralelo(self.mover_robot(W / 2 + 14, SUELO - 14),
                                 self.caminar_golem(W / 2 - 10))
        self.mensaje = "CLEAR!"
        yield from self.esperar(2.0)

    # ---------------- actualización por frame ----------------
    def actualizar(self):
        self.tick += 1
        vivas = []
        for p in self.particulas:
            p[0] += p[2] * DT
            p[1] += p[3] * DT
            p[3] += 160 * DT
            p[4] -= DT
            if p[4] > 0 and p[1] < SUELO:
                vivas.append(p)
        self.particulas = vivas
        for k in list(self.temblor):
            self.temblor[k] -= 1
            if self.temblor[k] <= 0:
                del self.temblor[k]

    # ---------------- dibujo ----------------
    def dibujar(self):
        img = Image.new("RGB", (W, H), CIELO)
        px = img.load()

        for x, y, b, fase in self.estrellas:
            brillo = b if (self.tick + fase) % 40 > 3 else min(2, b + 1)
            px[x, y] = ESTRELLA[brillo]

        # Gráfica de contribuciones
        for c in range(52):
            for r in range(7):
                x0, y0 = col_x(c), fila_y(r)
                clave = (c, r)
                if clave in self.bloques:
                    dx = (1 if self.tick % 2 else -1) if clave in self.temblor else 0
                    self._bloque(px, x0 + dx, y0, clave)
                else:
                    rect(px, x0, y0, x0 + CELDA - 1, y0 + CELDA - 1, CELDA_VACIA)

        # Suelo de ladrillos
        rect(px, 0, SUELO, W - 1, H - 1, SUELO_C["ladrillo"])
        rect(px, 0, SUELO, W - 1, SUELO, SUELO_C["borde"])
        for yy in range(SUELO + 4, H, 4):
            rect(px, 0, yy, W - 1, yy, SUELO_C["junta"])
        for fila, yy in enumerate(range(SUELO + 1, H, 4)):
            for xx in range((fila % 2) * 4, W, 8):
                rect(px, xx, yy, xx, yy + 2, SUELO_C["junta"])

        # Escaleras
        for c, tope in self.escaleras.items():
            x0 = col_x(c)
            rect(px, x0, tope, x0, SUELO - 1, ESCALERA_C["riel"])
            rect(px, x0 + 5, tope, x0 + 5, SUELO - 1, ESCALERA_C["riel"])
            rect(px, x0 + 6, tope + 1, x0 + 6, SUELO - 1, ESCALERA_C["sombra"])
            for yy in range(SUELO - 2, tope - 1, -3):
                rect(px, x0 + 1, yy, x0 + 4, yy, ESCALERA_C["peldano"])

        self._golem(px)
        self._robot(px)

        for x, y, _, _, _, color in self.particulas:
            if 0 <= int(x) < W and 0 <= int(y) < H:
                px[int(x), int(y)] = color

        # Marcador
        s = f"SCORE {self.score:05d}"
        ancho = len(s) * 4
        texto(px, s, W - PAD_X - ancho + 1, 4, TEXTO_SOMBRA)
        texto(px, s, W - PAD_X - ancho, 3, TEXTO)
        if self.mensaje and (self.tick // 4) % 2 == 0:
            ancho = len(self.mensaje) * 8
            texto(px, self.mensaje, W // 2 - ancho // 2 + 1, 74, TEXTO_SOMBRA, 2)
            texto(px, self.mensaje, W // 2 - ancho // 2, 73, CHISPA[1], 2)

        return img.resize((W * ESCALA, H * ESCALA), Image.NEAREST)

    def _bloque(self, px, x0, y0, clave):
        color = NIVELES[self.nivel[clave]]
        rect(px, x0, y0, x0 + CELDA - 1, y0 + CELDA - 1, color)
        rect(px, x0, y0, x0 + CELDA - 1, y0, aclarar(color, 1.35))
        rect(px, x0, y0, x0, y0 + CELDA - 1, aclarar(color, 1.2))
        rect(px, x0, y0 + CELDA - 1, x0 + CELDA - 1, y0 + CELDA - 1, aclarar(color, 0.6))
        rect(px, x0 + CELDA - 1, y0, x0 + CELDA - 1, y0 + CELDA - 1, aclarar(color, 0.6))
        dano = self.nivel[clave] - self.bloques[clave]
        grieta = aclarar(color, 0.35)
        puntos = [(2, 1), (3, 2), (2, 3), (3, 4), (1, 2), (4, 3)]
        for i in range(min(len(puntos), dano * 2)):
            gx, gy = puntos[i]
            if 0 <= x0 + gx < W:
                px[x0 + gx, y0 + gy] = grieta

    def _robot(self, px):
        x = self.robot[0] - 3
        y = self.robot[1] - 5
        flot = 1 if (self.tick // 3) % 2 else 0
        sprite = list(ROBOT)
        if (self.tick // 5) % 2:
            sprite[0] = "......."  # la luz de la antena parpadea
        pintar_sprite(px, sprite, ROBOT_PAL, x, y + flot)
        # Llama del jetpack
        llama = CHISPA[(self.tick // 2) % 2]
        for i, (fx, fy) in enumerate([(2, 9), (4, 9), (3, 10)]):
            if i < 2 or self.tick % 3:
                xx, yy = int(x) + fx, int(y + flot) + fy
                if 0 <= xx < W and 0 <= yy < H:
                    px[xx, yy] = llama

    def _golem(self, px):
        cx, pies = self.golem
        if self.pose == "golpe":
            sprite = GOLEM_GOLPE
        else:
            sprite = list(GOLEM_QUIETO)
            if self.pose in ("camina", "trepa"):
                sprite[-4:] = PIERNAS_A if (self.tick // 3) % 2 else PIERNAS_B
        pintar_sprite(px, sprite, GOLEM_PAL, cx - 6, pies - len(sprite))


# ---------------------------------------------------------------------------
def simular(datos, velocidad):
    juego = Juego(datos, velocidad)
    n = 0
    for _ in juego.guion():
        n += 1
    return n


def generar(datos, salida, max_seg=35):
    max_frames = int(max_seg * FPS)
    velocidad = 1.0
    for _ in range(8):  # ajusta la velocidad para que el GIF no sea eterno
        n = simular(datos, velocidad)
        if n <= max_frames:
            break
        velocidad *= min(2.0, n / max_frames * 1.05)
    juego = Juego(datos, velocidad)
    frames = []
    for _ in juego.guion():
        juego.actualizar()
        frames.append(juego.dibujar())
    paleta = [f.convert("P", palette=Image.ADAPTIVE, colors=128) for f in frames]
    duraciones = [round(1000 / FPS)] * len(paleta)
    paleta[0].save(salida, save_all=True, append_images=paleta[1:], duration=duraciones,
                   loop=0, optimize=True, disposal=1)
    print(f"✓ GIF guardado en {salida} ({len(frames)} frames, velocidad x{velocidad:.2f}, "
          f"{juego.score} contribuciones destruidas)")


def cargar_datos(usuario, entrada_json):
    if entrada_json:
        with open(entrada_json) as f:
            return json.load(f)
    from gh_space_shooter.github_client import GitHubClient
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("Falta la variable de entorno GH_TOKEN")
    with GitHubClient(token) as cliente:
        return cliente.get_contribution_graph(usuario)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Robot constructor + gólem en tu gráfica de contribuciones")
    ap.add_argument("usuario")
    ap.add_argument("--output", default="constructor-golem.gif")
    ap.add_argument("--raw-input", default=None)
    ap.add_argument("--max-segundos", type=float, default=35)
    a = ap.parse_args()
    generar(cargar_datos(a.usuario, a.raw_input), a.output, a.max_segundos)
