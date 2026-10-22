"""Conversions de coordonnees isometriques (projection dimetrique 2:1).

Repere "monde" : un plan en coordonnees (x, y) continues, ou une tuile
occupee par le coin haut-gauche de son diamant.
Repere "ecran" : pixels 2D classiques (x droite, y bas), avec l'axe iso
incline selon la projection SNES-like (rapport 2:1).
"""

from __future__ import annotations

import math

# Taille d'une tuile au sol en pixels ecran (diamant 2:1, comme sur SNES).
TILE_W = 64
TILE_H = 32

# Facteur vertical : compression de profondeur pour eviter l'effet
# "vue du dessus trop ecrasee". Les objets hauts sont dessines en hauteur
# d'ecran pure (soustraction de y_screen).
ISO_ANGLE = math.atan2(1, 2)  # ~26.57 degres


def world_to_screen(wx: float, wy: float, wz: float = 0.0) -> tuple[float, float]:
    """Convertit une position monde (wx, wy, hauteur wz) en pixels ecran."""
    sx = (wx - wy) * (TILE_W / 2.0)
    sy = (wx + wy) * (TILE_H / 2.0) - wz
    return sx, sy


def screen_to_world(sx: float, sy: float) -> tuple[float, float]:
    """Inverse de world_to_screen (wz ignore). Donne les coordonnees monde
    continues sous le pointeur souris."""
    wx = (sx / (TILE_W / 2.0) + sy / (TILE_H / 2.0)) / 2.0
    wy = (sy / (TILE_H / 2.0) - sx / (TILE_W / 2.0)) / 2.0
    return wx, wy


def tile_of(world_pos: tuple[float, float]) -> tuple[int, int]:
    """Coherentes de la tuile contenant une position monde."""
    return int(math.floor(world_pos[0])), int(math.floor(world_pos[1]))


def depth_key(wx: float, wy: float) -> float:
    """Cle de tri painter's-order : plus grand = plus proche de la camera."""
    return wx + wy


def move_angle_to_world(angle: float) -> tuple[float, float]:
    """Transforme un angle d'ecran (joystick/clavier, 0 = droite vers le bas
    de l'ecran) en vecteur direction monde isometrique normalise."""
    # En monde, "vers le bas de l'ecran" = (+x, +y). On applique une rotation
    # dans l'espace d'ecran puis on reprojette en monde.
    ex = math.cos(angle)  # axe ecran X
    ey = math.sin(angle)  # axe ecran Y (vers le bas)
    # Inversion de la projection (sans hauteur) :
    wx = ex / (TILE_W / 2.0) + ey / (TILE_H / 2.0)
    wy = -ex / (TILE_W / 2.0) + ey / (TILE_H / 2.0)
    n = math.hypot(wx, wy) or 1.0
    return wx / n, wy / n
