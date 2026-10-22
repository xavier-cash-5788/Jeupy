"""Tilemap isometrique generee a partir d'une CARTE ASCII + decoupage en ZONES.

Pipeline :
  1. AsciiGenerator produit la trame du monde en caracteres (lisible/editeable)
     avec des regions fonctionnelles : spawn, farm, mine, loot, combat, bucraft.
  2. TileMap convertit l'ASCII en tuiles (CHAR_TO_TILE) et props (CHAR_TO_PROP).
  3. Les regions deviennent des Zone (rectangles monde) utilisees par le jeu
     pour peupler ennemis/resources et afficher le HUD.

Une carte ASCII existante peut etre chargee a la place de la generation :
    TileMap.from_ascii_file("maps/monde.txt", seed=...)
"""

from __future__ import annotations

import math
import random

import pygame

from engine.iso import TILE_W, TILE_H
from engine.ascii_map import (
    WALKABLE, LIQUID, DIGGABLE, SOLID,
    CHAR_TO_TILE, CHAR_TO_PROP, PROP_COLLIDER, TILE_DEFS,
    AsciiGenerator, load_ascii_map, save_ascii_map,
    T_GRASS, T_WATER, T_BRIDGE, T_ORE_COPPER, T_ORE_IRON, T_ORE_GOLD, T_ORE_DIAMOND,
)

# ---------------------------------------------------------------- zones
ZONE_STYLE = {
    "spawn":   ("Village depart", (250, 240, 160)),
    "farm":    ("Ferme - farm",   (160, 230, 120)),
    "mine":    ("Mine - minage",  (170, 180, 210)),
    "loot":    ("Ruines - loot",  (240, 190, 110)),
    "combat":  ("Arene - combat", (240, 130, 130)),
    "bucraft": ("Foret - bucraft",(120, 210, 170)),
    "wild":    ("Sauvage",        (200, 200, 200)),
}


class Zone:
    """Region rectangulaire du monde avec une fonction de gameplay."""

    def __init__(self, name: str, x: int, y: int, w: int, h: int):
        self.name = name
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def label(self) -> str:
        return ZONE_STYLE.get(self.name, (self.name, (255, 255, 255)))[0]

    @property
    def color(self):
        return ZONE_STYLE.get(self.name, ((255, 255, 255)))[1] if self.name in ZONE_STYLE else (255, 255, 255)

    def contains(self, wx: float, wy: float) -> bool:
        return self.x <= wx < self.x + self.w and self.y <= wy < self.y + self.h

    def center(self) -> tuple[float, float]:
        return self.x + self.w / 2, self.y + self.h / 2

    def random_point(self, rng: random.Random) -> tuple[float, float]:
        return rng.uniform(self.x + 1, self.x + self.w - 1), rng.uniform(self.y + 1, self.y + self.h - 1)


def default_layout(w: int, h: int, rng: random.Random) -> list[dict]:
    """Repartit la carte en regions fonctionnelles (grille irreguliere)."""
    cols = [
        ("spawn", 0.00, 0.20),
        ("farm", 0.20, 0.45),
        ("bucraft", 0.45, 0.70),
        ("mine", 0.70, 1.00),
    ]
    # chaque region porte la fonction de sa COLONNE ; seule la ligne basse de
    # la colonne ouest devient 'loot' (ruines) et celle de bucraft 'combat'.
    # => toutes les fonctions sont garanties, quel que soit le seed.
    rows = [(0.00, 0.45), (0.45, 1.00)]
    # chaque region porte la fonction de sa COLONNE ; la ligne basse de la
    # colonne ouest devient 'loot' (ruines). Toutes les fonctions sont donc
    # garanties presentes, quel que soit le seed.
    layout = []
    for ci, (cname, c0, c1) in enumerate(cols):
        for ri, (r0, r1) in enumerate(rows):
            x0, y0 = int(c0 * w), int(r0 * h)
            x1, y1 = int(c1 * w), int(r1 * h)
            # petites variations de bordures => contours organiques
            jx = rng.randint(-3, 3) if 0 < c0 else 0
            jy = rng.randint(-3, 3) if 0 < r0 else 0
            x0 += jx; y0 += jy
            name = cname
            if ci == 0 and ri == 1:
                name = "loot"
            elif ci == 2 and ri == 0:
                name = "combat"
            layout.append({"name": name, "x": max(0, x0), "y": max(0, y0),
                           "w": min(w, x1) - max(0, x0), "h": min(h, y1) - max(0, y0)})
    # le village est toujours a l'ouest-centre pour un spawn garanti
    spawn = next(z for z in layout if z["name"] == "spawn")
    spawn["x"], spawn["y"] = int(0.05 * w), int(0.30 * h)
    spawn["w"], spawn["h"] = int(0.16 * w), int(0.28 * h)
    return layout


class TileMap:
    def __init__(self, w: int = 96, h: int = 96, seed: int | None = None,
                 ascii_source: str | None = None):
        self.w = w
        self.h = h
        rng = random.Random(seed)
        self.rng = rng
        self.zones: list[Zone] = []
        self.props: list[dict] = []
        if ascii_source:
            grid = load_ascii_map(ascii_source)
            self.h = len(grid)
            self.w = len(grid[0])
            self.grid = [[CHAR_TO_TILE.get(ch, CHAR_TO_TILE.get(ch, T_GRASS)) for ch in row]
                         for row in grid]
            self._props_from_grid(grid)
            self._zones_from_grid(grid)
        else:
            layout = default_layout(w, h, rng)
            gen = AsciiGenerator(w, h, seed)
            grid = gen.generate(layout)
            self.grid = [[(CHAR_TO_TILE.get(ch) if ch not in CHAR_TO_PROP else T_GRASS)
                          for ch in row] for row in grid]
            self._props_from_grid(grid)
            self.zones = [Zone(r["name"], r["x"], r["y"], r["w"], r["h"]) for r in layout]

    # ---------------------------------------------------------- construction
    def _props_from_grid(self, grid: list[str]):
        for y, row in enumerate(grid):
            for x, ch in enumerate(row):
                kind = CHAR_TO_PROP.get(ch)
                if kind:
                    self.props.append({
                        "kind": kind,
                        "x": x + 0.5, "y": y + 0.5,
                        "seed": hash((x, y)) % 9999,
                        "hp": 3 if kind == "tree" else (4 if kind in ("rock", "boulder") else 1),
                    })

    def _zones_from_grid(self, grid: list[str]):
        """Zones approximatives quand on charge un fichier ASCII manuel :
        on deduit les regions par dominance de caracteres caracteristiques."""
        marks = {"w": "farm", "c": "mine", "#": "mine", "P": "bucraft", "T": "bucraft"}
        acc: dict[str, list[list[int]]] = {}
        for y, row in enumerate(grid):
            for x, ch in enumerate(row):
                z = marks.get(ch)
                if z:
                    acc.setdefault(z, []).append([x, y])
        for zname, pts in acc.items():
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
            rx = max(6, int(max(abs(x - cx) for x in xs) * 2.2))
            ry = max(6, int(max(abs(y - cy) for y in ys) * 2.2))
            self.zones.append(Zone(zname, int(cx - rx / 2), int(cy - ry / 2), rx, ry))
        if not self.zones:
            self.zones = [Zone("wild", 0, 0, self.w, self.h)]

    # -------------------------------------------------------------- requetes
    def tile_at(self, tx: int, ty: int) -> int:
        if 0 <= tx < self.w and 0 <= ty < self.h:
            return self.grid[ty][tx]
        return T_WATER

    def set_tile(self, tx: int, ty: int, t: int):
        if 0 <= tx < self.w and 0 <= ty < self.h:
            self.grid[ty][tx] = t

    def is_walkable(self, wx: float, wy: float) -> bool:
        t = self.tile_at(int(math.floor(wx)), int(math.floor(wy)))
        return TILE_DEFS[t].kind == WALKABLE

    def is_diggable(self, wx: float, wy: float) -> bool:
        t = self.tile_at(int(math.floor(wx)), int(math.floor(wy)))
        return TILE_DEFS[t].kind == DIGGABLE

    def solid_props(self) -> list[dict]:
        return [p for p in self.props if PROP_COLLIDER.get(p["kind"], 0) > 0]

    def zone_at(self, wx: float, wy: float) -> Zone | None:
        best = None
        for z in self.zones:
            if z.contains(wx, wy):
                if best is None or (z.w * z.h) < (best.w * best.h):
                    best = z
        return best

    def to_ascii(self) -> str:
        inv_t = {}
        for ch, t in CHAR_TO_TILE.items():
            inv_t.setdefault(t, ch)
        inv_p = {v: k for k, v in CHAR_TO_PROP.items()}
        prop_at = {(int(p["x"]), int(p["y"])): p["kind"] for p in self.props}
        lines = []
        for y in range(self.h):
            row = []
            for x in range(self.w):
                kind = prop_at.get((x, y))
                if kind and kind in inv_p:
                    row.append(inv_p[kind])
                else:
                    row.append(inv_t.get(self.grid[y][x], "."))
            lines.append("".join(row))
        return "\n".join(lines)

    def save_ascii(self, path: str):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_ascii() + "\n")

    # ---------------------------------------------------------------- rendu
    def draw_ground(self, surf: pygame.Surface, cam, view_rect_world):
        vx0, vy0, vx1, vy1 = view_rect_world
        pad = 2
        tw, th = TILE_W * cam.zoom, TILE_H * cam.zoom
        ticks = pygame.time.get_ticks()
        for ty in range(int(vy0) - pad, int(vy1) + pad):
            for tx in range(int(vx0) - pad, int(vx1) + pad):
                t = self.tile_at(tx, ty)
                d = TILE_DEFS[t]
                px, py = cam.world_to_view(tx, ty)
                if px < -tw or px > surf.get_width() + tw or py < -th * 4 or py > surf.get_height() + th:
                    continue
                pts = [
                    (px + tw / 2, py),
                    (px + tw, py + th / 2),
                    (px + tw / 2, py + th),
                    (px, py + th / 2),
                ]
                v = ((tx * 73 + ty * 151) % 11) - 5
                col = tuple(max(0, min(255, c + v * 2)) for c in d.base)
                pygame.draw.polygon(surf, col, pts)
                pygame.draw.line(surf, d.shade, pts[3], pts[2], 1)
                pygame.draw.line(surf, d.shade, pts[2], pts[1], 1)
                if d.kind == LIQUID:
                    phase = (ticks / 450 + tx * 0.7 + ty * 0.4) % 1
                    rx = px + tw * (0.25 + 0.4 * abs(math.sin(phase * math.pi)))
                    ry = py + th * 0.5
                    pygame.draw.line(surf, (150, 190, 235),
                                     (rx - 4 * cam.zoom, ry), (rx + 4 * cam.zoom, ry), 1)
                elif d.kind == DIGGABLE:
                    self._draw_ore(surf, px, py, tw, th, d.variant, cam.zoom)
                elif d.name in ("wheat", "carrots", "potatoes", "beetroots"):
                    self._draw_crop(surf, px, py, tw, th, d.name, ticks)
                elif d.name in ("cobble", "mossy", "deepslate", "planks", "stone", "log", "leaves"):
                    # joints de blocs facon Minecraft
                    pygame.draw.line(surf, d.shade, pts[0], pts[2], 1)

    @staticmethod
    def _draw_ore(surf, px, py, tw, th, variant, zoom):
        colors = [(200, 130, 80), (210, 210, 215), (240, 210, 90), (110, 230, 220)]
        spots = [(0.3, 0.45), (0.6, 0.35), (0.45, 0.6), (0.7, 0.6)]
        c = colors[variant % len(colors)]
        for i, (fx, fy) in enumerate(spots[: 2 + variant % 3]):
            cx = px + tw * fx
            cy = py + th * fy
            s = max(2, int(3 * zoom))
            pygame.draw.rect(surf, c, (cx, cy, s, s))

    @staticmethod
    def _draw_crop(surf, px, py, tw, th, name, ticks):
        n = 3
        for i in range(n):
            fx = 0.25 + 0.5 * i / (n - 1)
            cx = px + tw * fx
            cy = py + th * 0.5
            sway = math.sin(ticks / 600 + i) * 1.5
            if name == "wheat":
                col = (230, 200, 110)
                pygame.draw.line(surf, col, (cx, cy + 3), (cx + sway, cy - 5), 1)
            elif name == "carrots":
                pygame.draw.circle(surf, (90, 170, 80), (int(cx + sway), int(cy - 3)), 2)
            elif name == "potatoes":
                pygame.draw.circle(surf, (120, 150, 70), (int(cx), int(cy - 2)), 2)
            else:  # beetroots
                pygame.draw.circle(surf, (180, 80, 90), (int(cx + sway), int(cy - 2)), 2)
