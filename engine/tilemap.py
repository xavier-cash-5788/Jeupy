"""Tilemap isometrique genere proceduralement + rendu des tuiles au sol.

Les tuiles sont codees par entier :
  0 herbe, 1 chemin, 2 eau, 3 sable, 4 rocher (sol), 5 pont.
Les objets haussables (arbres, rochers, buissons...) sont geres par la
couche "props" et triees avec les entities (depth sorting).
"""

from __future__ import annotations

import math
import random

import pygame

from engine.iso import TILE_W, TILE_H, world_to_screen

# Codes de tuiles
GRASS, PATH, WATER, SAND, ROCK_FLOOR, BRIDGE = range(6)

TILE_COLORS = {
    GRASS:       ((88, 158, 74), (74, 138, 62)),
    PATH:        ((198, 172, 120), (178, 152, 102)),
    WATER:       ((58, 118, 188), (44, 98, 168)),
    SAND:        ((228, 214, 150), (210, 196, 132)),
    ROCK_FLOOR:  ((140, 140, 148), (120, 120, 130)),
    BRIDGE:      ((172, 128, 80), (150, 108, 66)),
}

WALKABLE = {GRASS, PATH, SAND, BRIDGE, ROCK_FLOOR}


class TileMap:
    def __init__(self, w: int = 48, h: int = 48, seed: int | None = None):
        self.w = w
        self.h = h
        rng = random.Random(seed)
        self.grid = [[GRASS for _ in range(w)] for _ in range(h)]
        self.props: list[dict] = []  # {kind, x, y, height, hp?}
        self._generate(rng)

    # ------------------------------------------------------------------ gen
    def _noise(self, rng: random.Random, scale: int) -> list[list[float]]:
        """Bruit de valeur simple interpole (sans dependance externe)."""
        gw = self.w // scale + 2
        gh = self.h // scale + 2
        grid = [[rng.random() for _ in range(gw)] for _ in range(gh)]

        def smooth(t):
            return t * t * (3 - 2 * t)

        out = [[0.0] * self.w for _ in range(self.h)]
        for y in range(self.h):
            for x in range(self.w):
                fx, fy = x / scale, y / scale
                x0, y0 = int(fx), int(fy)
                tx, ty = smooth(fx - x0), smooth(fy - y0)
                a = grid[y0][x0] + (grid[y0][x0 + 1] - grid[y0][x0]) * tx
                b = grid[y0 + 1][x0] + (grid[y0 + 1][x0 + 1] - grid[y0 + 1][x0]) * tx
                out[y][x] = a + (b - a) * ty
        return out

    def _generate(self, rng: random.Random):
        n_water = self._noise(rng, 9)
        n_grass = self._noise(rng, 6)
        cx, cy = self.w / 2, self.h / 2

        # Bordure d'eau autour de l'ile.
        for y in range(self.h):
            for x in range(self.w):
                edge = min(x, y, self.w - 1 - x, self.h - 1 - y)
                depth = n_water[y][x] + max(0.0, (4 - edge)) * 0.35
                if depth > 0.85:
                    self.grid[y][x] = WATER
                elif depth > 0.72:
                    self.grid[y][x] = SAND
                elif n_grass[y][x] > 0.78:
                    self.grid[y][x] = ROCK_FLOOR
                else:
                    self.grid[y][x] = GRASS

        # Chemin sinueux traversant l'ile (style overworld Zelda).
        px, py = 2, rng.randint(4, self.h - 5)
        steps = self.w * 2
        i = 0
        while 0 <= px < self.w and 0 <= py < self.h and i < steps:
            if self.grid[py][px] == WATER:
                self.grid[py][px] = BRIDGE
            elif self.grid[py][px] != BRIDGE:
                self.grid[py][px] = PATH
            py += rng.choice([-1, -1, 0, 1, 1])
            px += 1 if rng.random() < 0.85 else rng.choice([-1, 0, 1])
            py = max(1, min(self.h - 2, py))
            i += 1

        # Props (arbres, rochers, buissons) sur sol praticable.
        kinds = [("tree", 0.10), ("rock", 0.05), ("bush", 0.08), ("flower", 0.06)]
        for y in range(self.h):
            for x in range(self.w):
                t = self.grid[y][x]
                if t not in (GRASS, SAND, ROCK_FLOOR):
                    continue
                r = rng.random()
                acc = 0.0
                for kind, p in kinds:
                    acc += p
                    if r < acc:
                        # Ne pas bloquer le chemin.
                        if t == PATH and kind in ("tree", "rock"):
                            break
                        self.props.append({
                            "kind": kind,
                            "x": x + rng.uniform(0.15, 0.85),
                            "y": y + rng.uniform(0.15, 0.85),
                            "seed": rng.randint(0, 9999),
                        })
                        break

    # -------------------------------------------------------------- queries
    def tile_at(self, tx: int, ty: int) -> int:
        if 0 <= tx < self.w and 0 <= ty < self.h:
            return self.grid[ty][tx]
        return WATER  # hors carte = infranchissable

    def is_walkable(self, wx: float, wy: float) -> bool:
        tx, ty = int(math.floor(wx)), int(math.floor(wy))
        return self.tile_at(tx, ty) in WALKABLE

    def solid_props(self) -> list[dict]:
        return [p for p in self.props if p["kind"] in ("tree", "rock")]

    # ---------------------------------------------------------------- render
    def draw_ground(self, surf: pygame.Surface, cam, view_rect_world):
        vx0, vy0, vx1, vy1 = view_rect_world
        pad = 2
        tw, th = TILE_W * cam.zoom, TILE_H * cam.zoom
        for ty in range(int(vy0) - pad, int(vy1) + pad):
            for tx in range(int(vx0) - pad, int(vx1) + pad):
                t = self.tile_at(tx, ty)
                base, shade = TILE_COLORS[t]
                px, py = cam.world_to_view(tx, ty)
                if px < -tw or px > surf.get_width() + tw or py < -th * 4 or py > surf.get_height() + th:
                    continue
                pts = [
                    (px + tw / 2, py),
                    (px + tw, py + th / 2),
                    (px + tw / 2, py + th),
                    (px, py + th / 2),
                ]
                # Variance legere par tuile pour le cote "peinture SNES".
                v = ((tx * 73 + ty * 151) % 11) - 5
                col = tuple(max(0, min(255, c + v * 2)) for c in base)
                pygame.draw.polygon(surf, col, pts)
                # Ligne de fond sombre en bas du diamant (relief).
                pygame.draw.line(surf, shade, pts[3], pts[2], 1)
                pygame.draw.line(surf, shade, pts[2], pts[1], 1)
                if t == WATER:
                    # Reflets animes.
                    phase = (pygame.time.get_ticks() / 450 + tx * 0.7 + ty * 0.4) % 1
                    rx = px + tw * (0.25 + 0.4 * abs(math.sin(phase * math.pi)))
                    ry = py + th * 0.5
                    c = (150, 190, 235)
                    pygame.draw.line(surf, c, (rx - 4 * cam.zoom, ry), (rx + 4 * cam.zoom, ry), 1)
