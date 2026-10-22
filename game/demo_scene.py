"""Scene de demo : monde isometrique avec heros, ennemis, combat d'epee."""

from __future__ import annotations

import math
import random

import pygame

from engine.camera import Camera
from engine.entity import Hero, Slime, Bat, draw_prop
from engine.iso import TILE_W, TILE_H, move_angle_to_world
from engine.scene import Scene
from engine.tilemap import TileMap


class World:
    def __init__(self, seed=None):
        self.map = TileMap(48, 48, seed=seed)
        # Trouver un spawn praticable pres du centre.
        sx, sy = self._find_spawn()
        self.hero = Hero(sx, sy)
        self.enemies: list = []
        self.particles: list[dict] = []
        self.rng = random.Random(seed or 1)
        for _ in range(14):
            ex, ey = self._find_spawn(margin=6)
            cls = Bat if self.rng.random() < 0.3 else Slime
            self.enemies.append(cls(ex, ey, self.rng))
        self.score = 0
        self.hero.max_hp = 6

    def _find_spawn(self, margin: int = 3):
        cx, cy = self.map.w // 2, self.map.h // 2
        for r in range(0, max(self.map.w, self.map.h)):
            for dy in range(-r, r + 1, max(1, r)):
                for dx in range(-r, r + 1, max(1, r)):
                    x, y = cx + dx, cy + dy
                    if self.map.is_walkable(x + 0.5, y + 0.5) and not self._prop_at(x, y):
                        return x + 0.5, y + 0.5
        return cx + 0.5, cy + 0.5

    def _prop_at(self, tx, ty):
        return any(int(p["x"]) == tx and int(p["y"]) == ty for p in self.map.props)

    def spawn_particles(self, wx, wy, color, n=8):
        for _ in range(n):
            a = self.rng.uniform(0, math.tau)
            s = self.rng.uniform(20, 70)
            self.particles.append({
                "x": wx, "y": wy, "z": self.rng.uniform(5, 30),
                "vz": self.rng.uniform(40, 90),
                "vx": math.cos(a) * s * 0.02, "vy": math.sin(a) * s * 0.02,
                "life": self.rng.uniform(0.3, 0.6), "color": color,
            })

    def update(self, dt):
        self.hero.update(dt, self)
        # Frappe du heros -> degats aux ennemis.
        hb = self.hero.attack_hitbox_world
        if hb:
            hx, hy, hr = hb
            for en in self.enemies:
                if en.dead or en.hit_flash > 0:
                    continue
                if math.hypot(en.x - hx, en.y - hy) < hr + en.radius:
                    en.hp -= 1
                    en.hit_flash = 0.25
                    kb = 0.6
                    nx, ny = (en.x - self.hero.x), (en.y - self.hero.y)
                    n = math.hypot(nx, ny) or 1
                    en.x += nx / n * kb
                    en.y += ny / n * kb
                    if en.hp <= 0:
                        en.dead = True
                        self.score += 1
                        self.spawn_particles(en.x, en.y, (120, 220, 120), 12)

        for en in self.enemies:
            if en.dead:
                continue
            en.hit_flash = max(0.0, en.hit_flash - dt)
            en.update(dt, self)
            # Contact avec le heros -> degats + knockback.
            d = math.hypot(en.x - self.hero.x, en.y - self.hero.y)
            if d < en.radius + self.hero.radius and self.hero.hit_flash <= 0:
                self.hero.hp -= 1
                self.hero.hit_flash = 0.8
                ux, uy = (self.hero.x - en.x) / (d or 1), (self.hero.y - en.y) / (d or 1)
                self.hero.x += ux * 0.5
                self.hero.y += uy * 0.5
                if self.hero.hp <= 0:
                    self.hero.dead = True
        self.hero.hit_flash = max(0.0, self.hero.hit_flash - dt)
        self.enemies = [e for e in self.enemies if not e.dead]

        for p in self.particles:
            p["life"] -= dt
            p["z"] += p["vz"] * dt
            p["vz"] -= 160 * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
        self.particles = [p for p in self.particles if p["life"] > 0]


class DemoScene(Scene):
    def __init__(self, game, seed=None):
        super().__init__(game)
        self.world = World(seed=seed)
        self.cam = Camera(game.screen.get_size())
        self.cam.set_bounds(self.world.map.w, self.world.map.h)
        self.cam.cx, self.cam.cy = self.world.hero.x, self.world.hero.y
        self.last_dir_screen = math.pi / 2  # vers le bas de l'ecran
        self.show_help = True

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_SPACE:
                self.world.hero.start_attack(self.last_dir_screen)
            elif e.key == pygame.K_h:
                self.show_help = not self.show_help
            elif e.key == pygame.K_r:
                self.game.change_scene(DemoScene, seed=random.randint(0, 99999))
            elif e.key in (pygame.K_PLUS, pygame.K_EQUALS):
                self.cam.zoom = min(2.0, self.cam.zoom * 1.15)
            elif e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.cam.zoom = max(0.5, self.cam.zoom / 1.15)

    def _input_direction(self) -> tuple[float, float]:
        keys = pygame.key.get_pressed()
        ex = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        ey = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        if ex == 0 and ey == 0:
            return 0.0, 0.0
        angle = math.atan2(ey, ex)
        self.last_dir_screen = angle
        return move_angle_to_world(angle)

    def update(self, dt):
        w = self.world
        if not w.hero.dead:
            wvx, wvy = self._input_direction()
            if w.hero.attacking:
                wvx *= 0.35
            w.hero.set_velocity(wvx, wvy)
            w.hero.try_move(dt, self._walkable_with_props)
        w.update(dt)
        self.cam.follow((w.hero.x, w.hero.y), dt)

    def _walkable_with_props(self, wx, wy) -> bool:
        if not self.world.map.is_walkable(wx, wy):
            return False
        r = self.world.hero.radius
        for p in self.world.map.solid_props():
            if abs(p["x"] - wx) < 0.35 + r and abs(p["y"] - wy) < 0.35 + r:
                return False
        return True

    def draw(self, surf: pygame.Surface):
        surf.fill((24, 32, 48))
        w = self.world
        vr = self.cam.view_rect()
        w.map.draw_ground(surf, self.cam, vr)

        # Assemble les renderables (props + entities + particules) et trie.
        items = []
        for p in w.map.props:
            items.append((p["x"] + p["y"], "prop", p))
        for e in w.enemies:
            items.append((e.depth, "ent", e))
        items.append((w.hero.depth + 0.001, "ent", w.hero))
        items.sort(key=lambda t: t[0])
        for _, kind, obj in items:
            if kind == "prop":
                px, py = self.cam.world_to_view(obj["x"], obj["y"])
                if -80 < px < surf.get_width() + 80 and -160 < py < surf.get_height() + 80:
                    draw_prop(surf, self.cam, obj)
            else:
                obj.draw(surf, self.cam)

        for pt in w.particles:
            px, py = self.cam.world_to_view(pt["x"], pt["y"], pt["z"])
            s = max(1, int(3 * self.cam.zoom * pt["life"]))
            surf.fill(pt["color"], (int(px) - s, int(py) - s, s * 2, s * 2))

        self._draw_hud(surf)

    def _draw_hud(self, surf: pygame.Surface):
        f = self.game.font
        # Coeurs façon Zelda.
        for i in range(self.world.hero.max_hp):
            x = 14 + i * 22
            y = 14
            col = (220, 60, 60) if i < self.world.hero.hp else (60, 40, 40)
            r = 6
            pygame.draw.circle(surf, col, (x + r, y + r), r)
            pygame.draw.circle(surf, col, (x + r * 2, y + r), r)
            pygame.draw.polygon(surf, col, [(x, y + r), (x + r * 2, y + r * 2.6), (x + r * 4, y + r)])
        txt = f.render(f"Ennemis vaincus : {self.world.score}", True, (255, 255, 255))
        surf.blit(txt, (14, 34))
        if self.world.hero.dead:
            msg = f.render("GAME OVER - [R] nouvelle carte", True, (255, 80, 80))
            surf.blit(msg, msg.get_rect(center=(surf.get_width() // 2, surf.get_height() // 2)))
        if self.show_help:
            lines = [
                "ZQSD / WASD / Fleches : deplacer (directions relatives a l'ecran)",
                "ESPACE : coup d'epee    +/- : zoom    H : aide    R : nouvelle carte    ESC : quitter",
            ]
            y = surf.get_height() - 20 - len(lines) * 18
            for ln in lines:
                surf.blit(f.render(ln, True, (200, 220, 255)), (14, y))
                y += 18
