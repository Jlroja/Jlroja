"""
Genera el GIF de gh-space-shooter, pero con las contribuciones dibujadas
como METEORITOS que giran, en lugar de cuadritos verdes.

Todo lo demás (nave, disparos, explosiones, estrellas) queda igual que en
la herramienta original. Solo se reemplaza la forma de dibujar a los enemigos.

Uso (igual que el comando original):
    python scripts/meteoritos.py Jlroja --output assets/space-shooter.gif --strategy random --fps 30
"""

import math
import random

from gh_space_shooter.game.drawables.enemy import Enemy

# ---------------------------------------------------------------------------
# Paleta de rocas: más contribuciones (más "vida") = roca más grande,
# más clara y con grietas de lava más brillantes.
# ---------------------------------------------------------------------------
ROCA = {
    1: {"cuerpo": (92, 78, 66), "sombra": (60, 50, 42), "luz": (128, 112, 96), "lava": None},
    2: {"cuerpo": (110, 90, 72), "sombra": (72, 58, 46), "luz": (150, 128, 104), "lava": (200, 90, 30)},
    3: {"cuerpo": (124, 98, 76), "sombra": (80, 62, 48), "luz": (168, 140, 112), "lava": (240, 120, 40)},
    4: {"cuerpo": (138, 106, 80), "sombra": (88, 66, 50), "luz": (186, 152, 118), "lava": (255, 170, 60)},
}
TAMANO = {1: 0.80, 2: 0.90, 3: 1.00, 4: 1.08}  # factor sobre el tamaño de la celda


def _forma_meteorito(seed: int, puntas: int = 9):
    """Devuelve los radios irregulares (0.72-1.0) que dan forma de roca."""
    rnd = random.Random(seed)
    return [rnd.uniform(0.72, 1.0) for _ in range(puntas)]


def _crateres(seed: int):
    """Posiciones (ángulo, distancia, tamaño) de 2 o 3 cráteres."""
    rnd = random.Random(seed * 7 + 3)
    return [
        (rnd.uniform(0, 2 * math.pi), rnd.uniform(0.0, 0.45), rnd.uniform(0.14, 0.24))
        for _ in range(rnd.choice([2, 3]))
    ]


def _girar(px, py, cx, cy, ang):
    dx, dy = px - cx, py - cy
    c, s = math.cos(ang), math.sin(ang)
    return cx + dx * c - dy * s, cy + dx * s + dy * c


def _init(self, x, y, health, game_state):
    _init_original(self, x, y, health, game_state)
    seed = x * 31 + y * 17 + 5
    self._radios = _forma_meteorito(seed)
    self._crateres = _crateres(seed)
    rnd = random.Random(seed * 13)
    self._angulo = rnd.uniform(0, 2 * math.pi)
    self._vel_giro = rnd.choice([-1, 1]) * rnd.uniform(0.6, 1.6)  # radianes por segundo


def _animate(self, delta_time):
    self._angulo += self._vel_giro * delta_time


def _draw(self, draw, context):
    x, y = context.get_cell_position(self.x, self.y)
    cx = x + context.cell_size / 2
    cy = y + context.cell_size / 2
    nivel = max(1, min(4, self.health))
    pal = ROCA[nivel]
    r = context.cell_size / 2 * TAMANO[nivel] + 0.5

    # Contorno irregular de la roca
    n = len(self._radios)
    puntos = []
    for i, k in enumerate(self._radios):
        a = self._angulo + 2 * math.pi * i / n
        puntos.append((cx + math.cos(a) * r * k, cy + math.sin(a) * r * k))

    # Brillo de calor alrededor de las rocas con más contribuciones
    if pal["lava"] and nivel >= 3:
        g = r * 1.35
        draw.ellipse([cx - g, cy - g, cx + g, cy + g], fill=(*pal["lava"], 40 if nivel == 3 else 65))

    draw.polygon(puntos, fill=pal["sombra"])  # base oscura
    # Cuerpo un poco desplazado hacia arriba-izquierda (efecto de luz)
    cuerpo = [(px - 0.6 + (cx - px) * 0.12, py - 0.6 + (cy - py) * 0.12) for px, py in puntos]
    draw.polygon(cuerpo, fill=pal["cuerpo"])

    # Reflejo de luz
    lx, ly = cx - r * 0.3, cy - r * 0.3
    lr = r * 0.22
    draw.ellipse([lx - lr, ly - lr, lx + lr, ly + lr], fill=(*pal["luz"], 200))

    # Cráteres (giran con la roca)
    for ang, dist, tam in self._crateres:
        px = cx + math.cos(ang + self._angulo) * r * dist
        py = cy + math.sin(ang + self._angulo) * r * dist
        cr = max(1.0, r * tam)
        draw.ellipse([px - cr, py - cr, px + cr, py + cr], fill=pal["sombra"])

    # Grietas de lava en las rocas con más contribuciones
    if pal["lava"]:
        a1 = self._angulo + 0.8
        p1 = _girar(cx - r * 0.5, cy, cx, cy, a1)
        p2 = (cx, cy)
        p3 = _girar(cx + r * 0.35, cy + r * 0.3, cx, cy, a1)
        draw.line([p1, p2, p3], fill=(*pal["lava"], 230), width=1)


# Se reemplaza el dibujo de los enemigos por el de los meteoritos
_init_original = Enemy.__init__
Enemy.__init__ = _init
Enemy.animate = _animate
Enemy.draw = _draw


if __name__ == "__main__":
    from gh_space_shooter.cli import app

    app()
