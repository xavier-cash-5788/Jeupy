"""Scene principale : monde ASCII procedural + zones (farm/mine/loot/combat/bucraft).

Commandes :
  ZQSD / fleches   deplacement
  ESPACE           attaque a l'epee (zone combat)
  E (maintenu)     outil : farm (recolte), mine (minage), loot (coffres), bucraft (bois)
  C                craft rapide facon Minecraft (1 bois -> 1 planche)
  M                sauvegarde la carte generee en ASCII (maps/carte_<seed>.txt)
  R                nouvelle carte (nouvelle graine)
"""

from __future__ import annotations

import math
import os

import pygame

from engine.scene import Scene
from engine.camera import Camera
from engine.entity import draw_prop
from engine.iso import world_to_screen, screen_to_world
from game.world import World


class DemoScene(Scene):
    name = "demo"

    def __init__(self, game=None, seed=None):
        super().__init__(game)
        self.world = World(seed=seed)
        size = game.screen.get_size() if game is not None else (1024, 640)
        self.camera = Camera(size)
        self.camera.set_bounds(self.world.map.w, self.world.map.h)
        self.camera.cx, self.camera.cy = self.world.hero.x, self.world.hero.y
        self.camera.zoom = 0.75
        self.font = game.font if game is not None else None
        self.bigfont = None
        self._attack_consumed = False
        self.hint = "Zone tranquille : explore ! Les ennemis restent dans leur zone."

    def enter(self):
        pygame.display.set_caption("IsoEngine - map ASCII procedurale + zones")
        if self.font is None:
            self.font = pygame.font.SysFont("monospace", 16, bold=True)
        if self.bigfont is None:
            self.bigfont = pygame.font.SysFont("monospace", 20, bold=True)

    # ------------------------------------------------------------------ input
    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_r:
                self.game.change_scene(DemoScene, seed=None)
            elif e.key == pygame.K_m:
                os.makedirs("maps", exist_ok=True)
                path = f"maps/carte_{self.world.seed}.txt"
                self.world.map.save_ascii(path)
                self.hint = f"Carte ASCII sauvegardee : {path}"
            elif e.key == pygame.K_c:
                if self.world.craft("planche"):
                    self.hint = "Bucraft : 1 bois -> 1 planche !"
                else:
                    self.hint = "Il te faut au moins 1 bois (foret bucraft)."

    def _hero_input(self):
        keys = pygame.key.get_pressed()
        wvx = wvy = 0.0
        for key, d in ((pygame.K_UP, (0, -1)), (pygame.K_w, (0, -1)),
                       (pygame.K_DOWN, (0, 1)), (pygame.K_s, (0, 1)),
                       (pygame.K_LEFT, (-1, 0)), (pygame.K_a, (-1, 0)),
                       (pygame.K_RIGHT, (1, 0)), (pygame.K_d, (1, 0))):
            if keys[key]:
                sx, sy = world_to_screen(d[0], d[1])
                wx, wy = screen_to_world(sx, sy)
                wvx += wx
                wvy += wy
        hero = self.world.hero
        hero.set_velocity(wvx, wvy)

        mx, my = pygame.mouse.get_pos()
        hx, hy = self.camera.world_to_view(hero.x, hero.y)
        angle = math.atan2(my - (hy - 14 * self.camera.zoom), mx - hx)
        if keys[pygame.K_SPACE] and not hero.attacking and not self._attack_consumed:
            hero.start_attack(angle)
            self._attack_consumed = True
        if not keys[pygame.K_SPACE]:
            self._attack_consumed = False

        # Outil (E maintenu) : recolte / minage / loot / bucraft.
        hero.gathering = bool(keys[pygame.K_e]) and not hero.dead
        target = self.world.gather_target() if hero.gathering else None
        hero.gather_target = target
        if target is None:
            hero.gather_t = 0.0
        elif hero.gather_t >= self.world.gather_duration(target):
            self.world.complete_gather(target)
            hero.gather_t = 0.0

    # ------------------------------------------------------------------ update
    def update(self, dt):
        if not self.world.hero.dead:
            self._hero_input()
            self.world.update(dt)
        self.camera.follow((self.world.hero.x, self.world.hero.y), dt)

    # ------------------------------------------------------------------ render
    def draw(self, surf: pygame.Surface):
        W, H = surf.get_size()
        surf.fill((38, 60, 92))
        cam = self.camera

        vx0, vy0, vx1, vy1 = cam.view_rect()
        self.world.map.draw_ground(surf, cam, (vx0, vy0, vx1, vy1))

        # tri depth : props, ressources, ennemis, heros
        items = []
        for p in self.world.map.props:
            items.append((p["x"] + p["y"], "prop", p))
        for r in self.world.resources:
            items.append((r.depth, "res", r))
        for e in self.world.enemies:
            items.append((e.depth, "ent", e))
        hero = self.world.hero
        items.append((hero.depth, "ent", hero))
        items.sort(key=lambda it: it[0])
        for _, kind, obj in items:
            if kind == "prop":
                draw_prop(surf, cam, obj)
            else:
                obj.draw(surf, cam)

        # particules
        for p in self.world.particles:
            px, py = cam.world_to_view(p["x"], p["y"], p["z"])
            s = max(1, int(3 * cam.zoom * p["life"] * 2))
            pygame.draw.rect(surf, p["color"], (px - s // 2, py - s // 2, s, s))

        # cible de l'outil : surbrillance + barre de progression
        if hero.gathering and hero.gather_target:
            t = hero.gather_target
            if t[0] == "res":
                ox, oy = t[1].x, t[1].y
            elif t[0] == "prop":
                ox, oy = t[1]["x"], t[1]["y"]
            else:
                ox, oy = t[1] + 0.5, t[2] + 0.5
            px, py = cam.world_to_view(ox, oy)
            prog = min(1.0, hero.gather_t / max(0.01, self.world.gather_duration(t)))
            pygame.draw.circle(surf, (255, 255, 160), (int(px), int(py - 6 * cam.zoom)),
                               int(16 * cam.zoom), 2)
            bw = int(30 * cam.zoom)
            pygame.draw.rect(surf, (40, 40, 40), (px - bw // 2, py - 34 * cam.zoom, bw, 5))
            pygame.draw.rect(surf, (250, 220, 90), (px - bw // 2, py - 34 * cam.zoom, int(bw * prog), 5))

        # textes flottants "+2 bois"
        for fl in self.world.floaters:
            px, py = cam.world_to_view(fl["x"], fl["y"], fl["z"])
            txt = self.font.render(fl["text"], True, (255, 255, 180))
            surf.blit(txt, (px - txt.get_width() / 2, py))

        self._draw_hud(surf, (W, H))

    # ------------------------------------------------------------------ HUD
    def _draw_hud(self, surf, size):
        W, H = size
        hero = self.world.hero

        # coeurs
        for i in range(hero.max_hp):
            x = 14 + i * 22
            col = (230, 60, 60) if i < hero.hp else (70, 40, 40)
            pygame.draw.circle(surf, col, (x + 5, 20), 6)
            pygame.draw.circle(surf, col, (x + 13, 20), 6)
            pygame.draw.polygon(surf, col, [(x - 1, 22), (x + 17, 22), (x + 8, 32)])

        # zone actuelle
        z = self.world.current_zone()
        label = z.label if z else "Inconnu"
        txt = self.bigfont.render(f"Zone : {label}", True, (255, 240, 170))
        surf.blit(txt, (14, 40))

        inv = ", ".join(f"{k}:{v}" for k, v in sorted(self.world.inventory.items()) if v > 0) or "vide"
        it = self.font.render(f"Inventaire : {inv}", True, (220, 220, 220))
        surf.blit(it, (14, 68))
        sc = self.font.render(f"Ennemis vaincus : {self.world.score}   Graine : {self.world.seed}", True, (200, 200, 200))
        surf.blit(sc, (14, 86))

        self._draw_minimap(surf, W)

        hint = self.font.render(self.hint, True, (180, 230, 180))
        surf.blit(hint, (14, H - 40))
        ctrl = self.font.render("ZQSD bouger | ESPACE epee | E outil (farm/mine/loot/bucraft) | C craft | M save ASCII | R nouvelle carte", True, (170, 190, 210))
        surf.blit(ctrl, (14, H - 22))

        if hero.dead:
            over = self.bigfont.render("GAME OVER - appuie sur R pour une nouvelle carte", True, (255, 120, 120))
            surf.blit(over, (W / 2 - over.get_width() / 2, H / 2))

    def _draw_minimap(self, surf, W):
        m = self.world.map
        mm = pygame.Surface((m.w, m.h))
        from engine.ascii_map import TILE_DEFS
        for y in range(m.h):
            for x in range(m.w):
                mm.set_at((x, y), TILE_DEFS[m.grid[y][x]].base)
        for z in m.zones:
            pygame.draw.rect(mm, z.color, (z.x, z.y, z.w, z.h), 1)
        scale = 2
        big = pygame.transform.scale(mm, (m.w * scale, m.h * scale))
        rect = big.get_rect(topright=(W - 12, 12))
        bg = pygame.Rect(rect.left - 4, rect.top - 4, rect.width + 8, rect.height + 8)
        pygame.draw.rect(surf, (20, 25, 35), bg)
        surf.blit(big, rect.topleft)
        hero = self.world.hero
        pygame.draw.circle(surf, (255, 255, 80),
                           (rect.left + int(hero.x * scale), rect.top + int(hero.y * scale)), 3)
