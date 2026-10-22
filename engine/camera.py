"""Camera isometrique : suit une cible avec lissage, limite a la carte."""

from __future__ import annotations

import pygame

from engine.iso import world_to_screen


class Camera:
    def __init__(self, screen_size: tuple[int, int]):
        self.screen_w, self.screen_h = screen_size
        # Position monde du centre de vue.
        self.cx = 0.0
        self.cy = 0.0
        self.zoom = 1.0
        self.smoothing = 8.0  # vitesse de rattrapage (unites/seconde^2 approx)
        self.bounds: tuple[float, float, float, float] | None = None  # xmin,ymin,xmax,ymax monde

    def set_bounds(self, w_tiles: int, h_tiles: int):
        self.bounds = (-1.0, -1.0, float(w_tiles), float(h_tiles))

    def follow(self, target_world: tuple[float, float], dt: float):
        tx, ty = target_world
        k = min(1.0, self.smoothing * dt)
        self.cx += (tx - self.cx) * k
        self.cy += (ty - self.cy) * k
        self.clamp()

    def clamp(self):
        if not self.bounds:
            return
        x_min, y_min, x_max, y_max = self.bounds
        # On convertit les limites d'ecran en monde via les coins.
        half_w = self.screen_w / (2 * self.zoom)
        half_h = self.screen_h / (2 * self.zoom)
        # Marge monde correspondant a la demi-diagonale visible.
        margin_x = half_w / 32.0 + half_h / 32.0
        margin_y = margin_x
        self.cx = max(x_min + margin_x, min(x_max - margin_x, self.cx)) if x_max - x_min > 2 * margin_x else (x_min + x_max) / 2
        self.cy = max(y_min + margin_y, min(y_max - margin_y, self.cy)) if y_max - y_min > 2 * margin_y else (y_min + y_max) / 2

    def world_to_view(self, wx: float, wy: float, wz: float = 0.0) -> tuple[float, float]:
        """Position monde -> pixels ecran (camera appliquee)."""
        sx, sy = world_to_screen(wx, wy, wz)
        csx, csy = world_to_screen(self.cx, self.cy)
        px = (sx - csx) * self.zoom + self.screen_w / 2
        py = (sy - csy) * self.zoom + self.screen_h / 2
        return px, py

    def view_rect(self) -> tuple[float, float, float, float]:
        """Rectangle englobant la vue en coordonnees monde (pour culling)."""
        corners = [
            (0, 0), (self.screen_w, 0), (0, self.screen_h), (self.screen_w, self.screen_h),
        ]
        pts = []
        for vx, vy in corners:
            wx, wy = self.view_to_world(vx, vy)
            pts.append((wx, wy))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)

    def view_to_world(self, vx: float, vy: float) -> tuple[float, float]:
        from engine.iso import screen_to_world
        csx, csy = world_to_screen(self.cx, self.cy)
        sx = (vx - self.screen_w / 2) / self.zoom + csx
        sy = (vy - self.screen_h / 2) / self.zoom + csy
        return screen_to_world(sx, sy)
