"""Entites isometriques : sprite "geometrique" dessine a la volee, style
mini-Zelda (heros, ennemis), avec ombre au sol et depth sorting.

Pas d'assets externes : tout est dessine proceduralement pour que le moteur
tourne immediatement. On pourra remplacer par des spritesheets plus tard.
"""

from __future__ import annotations

import math

import pygame

from engine.iso import TILE_W, TILE_H


class Entity:
    """Base : position monde (x, y continue), deplacement, animation."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 4.0            # tuiles / seconde
        self.facing = 1             # -1 gauche, 1 droite
        self.anim_t = 0.0
        self.moving = False
        self.radius = 0.28          # rayon de collision en tuiles
        self.hp = 3
        self.max_hp = 3
        self.dead = False
        self.hit_flash = 0.0
        self.home = (x, y)          # point d'attache (gardiennage de zone)
        self.leash = 0.0            # rayon de gardiennage autour du home

    # ------------------------------------------------------------ movement
    def set_velocity(self, wvx: float, wvy: float):
        n = math.hypot(wvx, wvy)
        if n > 1e-6:
            k = self.speed / n
            self.vx, self.vy = wvx * k, wvy * k
            self.moving = True
            if abs(self.vx) > 0.01:
                self.facing = -1 if self.vx < 0 else 1
        else:
            self.vx = self.vy = 0.0
            self.moving = False

    def try_move(self, dt: float, walkable_fn) -> bool:
        """Deplace avec glissement le long des murs (collisions axiales)."""
        ok = False
        nx, ny = self.x + self.vx * dt, self.y + self.vy * dt
        if walkable_fn(nx, self.y):
            self.x = nx
            ok = True
        if walkable_fn(self.x, ny):
            self.y = ny
            ok = True
        if self.moving:
            self.anim_t += dt
        return ok

    @property
    def depth(self) -> float:
        return self.x + self.y

    # --------------------------------------------------------------- hooks
    def update(self, dt: float, world):
        pass

    def draw(self, surf: pygame.Surface, cam):
        px, py = cam.world_to_view(self.x, self.y)
        self._draw_shadow(surf, px, py, cam.zoom)

    def _draw_shadow(self, surf, px, py, zoom):
        r = int(10 * zoom)
        pygame.draw.ellipse(surf, (30, 40, 30), (px - r, py - r // 2, r * 2, r))


class Hero(Entity):
    """Le heros : petit bonhomme dessine a base de primitives, marche,
    epée equipable (A pour frapper)."""

    def __init__(self, x: float, y: float):
        super().__init__(x, y)
        self.speed = 4.5
        self.attacking = False
        self.attack_t = 0.0
        self.attack_dir = 0.0  # angle ecran de l'attaque
        self.gathering = False
        self.gather_t = 0.0
        self.gather_target = None

    def start_attack(self, angle_screen: float):
        if not self.attacking:
            self.attacking = True
            self.attack_t = 0.0
            self.attack_dir = angle_screen

    @property
    def attack_hitbox_world(self):
        """Retourne (wx, wy, rayon) du point d'impact si en pleine attaque."""
        if not self.attacking or not (0.08 < self.attack_t < 0.22):
            return None
        reach = 0.7
        ex = math.cos(self.attack_dir) * reach * (TILE_H / TILE_W)  # compense l'aspect iso
        ey = math.sin(self.attack_dir) * reach
        return self.x + ex + ey, self.y - ex + ey, 0.45

    def update(self, dt: float, world):
        if self.attacking:
            self.attack_t += dt
            if self.attack_t > 0.35:
                self.attacking = False
        if self.gathering:
            self.gather_t += dt
        else:
            self.gather_t = 0.0

    def draw(self, surf: pygame.Surface, cam):
        px, py = cam.world_to_view(self.x, self.y)
        z = cam.zoom
        bob = 0
        if self.moving:
            bob = int(math.sin(self.anim_t * 14) * 2 * z)
        elif self.attacking:
            bob = int(math.sin(self.attack_t * 30) * z)

        skin = (240, 200, 160)
        tunic = (60, 160, 70) if self.hit_flash <= 0 else (255, 255, 255)
        hat = (40, 130, 55)
        hair = (200, 170, 60)
        boot = (90, 60, 30)

        h = 30 * z   # taille totale approximative
        # Jambes
        leg_off = int(math.sin(self.anim_t * 14) * 3 * z) if self.moving else 0
        pygame.draw.line(surf, boot, (px - 3 * z, py - 8 * z), (px - 3 * z + leg_off, py - 1 * z), max(1, int(3 * z)))
        pygame.draw.line(surf, boot, (px + 3 * z, py - 8 * z), (px + 3 * z - leg_off, py - 1 * z), max(1, int(3 * z)))
        # Corps (tunique)
        body = pygame.Rect(int(px - 7 * z), int(py - h + 8 * z + bob), int(14 * z), int(14 * z))
        pygame.draw.rect(surf, tunic, body, border_radius=int(3 * z))
        # Bras
        arm_y = py - h + 14 * z + bob
        pygame.draw.circle(surf, skin, (int(px - 8 * z), int(arm_y)), max(1, int(2.5 * z)))
        pygame.draw.circle(surf, skin, (int(px + 8 * z), int(arm_y)), max(1, int(2.5 * z)))
        # Tete + casquette
        head_c = (int(px), int(py - h + 4 * z + bob))
        pygame.draw.circle(surf, skin, head_c, max(1, int(6 * z)))
        pygame.draw.arc(surf, hat, (*head_c, int(13 * z), int(11 * z)), math.pi * 0.05, math.pi * 0.95, max(1, int(4 * z)))
        pygame.draw.circle(surf, hat, (head_c[0], head_c[1] - int(4 * z)), max(1, int(3 * z)))
        # Yeux selon orientation
        exo = int(self.facing * 2 * z)
        es = max(1, int(1.3 * z))
        pygame.draw.rect(surf, (20, 20, 20), (head_c[0] + exo - 2, head_c[1], es, es))
        pygame.draw.rect(surf, (20, 20, 20), (head_c[0] + exo + 2, head_c[1], es, es))

        # Epee pendant l'attaque : arc lumineux oriente.
        if self.attacking:
            prog = min(1.0, self.attack_t / 0.3)
            ang0 = self.attack_dir - 1.1 + prog * 2.2
            cx, cy = px, py - 14 * z
            L = 26 * z
            tipx = cx + math.cos(ang0) * L
            tipy = cy + math.sin(ang0) * L * 0.6
            pygame.draw.line(surf, (250, 250, 255), (cx, cy), (tipx, tipy), max(1, int(3 * z)))
            pygame.draw.line(surf, (180, 180, 220), (cx, cy), (tipx, tipy), max(1, int(1 * z)))
            # trainer
            for i in range(1, 4):
                a = ang0 - i * 0.25
                tx = cx + math.cos(a) * L
                ty = cy + math.sin(a) * L * 0.6
                s = max(1, int((4 - i) * z))
                pygame.draw.circle(surf, (255, 255, 200), (int(tx), int(ty)), s)

        # Pioche : outil qui tape pendant la recolte / le minage.
        if self.gathering:
            swing = math.sin(self.gather_t * 18)
            cx, cy = px + 9 * z, py - 15 * z
            hx = cx + 10 * z * (0.4 + 0.6 * swing)
            hy = cy + 8 * z * swing
            pygame.draw.line(surf, (120, 85, 50), (cx, cy), (hx, hy), max(1, int(2.5 * z)))
            pygame.draw.line(surf, (170, 170, 180), (hx - 5 * z, hy), (hx + 5 * z, hy - 3 * z), max(1, int(2 * z)))


class Slime(Entity):
    """Ennemi simple : erre, poursuit le heros s'il est proche."""

    def __init__(self, x: float, y: float, rng=None, aggro: float = 6.0,
                 leash: float = 12.0, speed: float = 1.8, hp: int = 2):
        import random
        super().__init__(x, y)
        self.rng = rng or random.Random()
        self.speed = speed
        self.hp = hp
        self.max_hp = hp
        self.aggro = aggro
        self.leash = leash
        self.wander_t = 0.0
        self.dir = self.rng.uniform(0, math.tau)

    def update(self, dt: float, world):
        hero = world.hero
        dx, dy = hero.x - self.x, hero.y - self.y
        dist = math.hypot(dx, dy)
        dh = math.hypot(hero.x - self.home[0], hero.y - self.home[1])
        chasing = 0.05 < dist < self.aggro and dh < self.leash and not hero.dead
        if chasing:
            self.set_velocity(dx / dist, dy / dist)
        else:
            self.wander_t -= dt
            if self.wander_t <= 0:
                self.wander_t = self.rng.uniform(1.0, 2.5)
                self.dir = self.rng.uniform(0, math.tau)
            if self.leash and math.hypot(self.x - self.home[0], self.y - self.home[1]) > self.leash * 0.7:
                hx, hy = self.home
                self.dir = math.atan2(hy - self.y, hx - self.x) + self.rng.uniform(-0.6, 0.6)
            self.set_velocity(math.cos(self.dir), math.sin(self.dir))
        if not self.try_move(dt, world.map.is_walkable):
            self.dir = self.rng.uniform(0, math.tau)

    def draw(self, surf: pygame.Surface, cam):
        px, py = cam.world_to_view(self.x, self.y)
        z = cam.zoom
        squash = 1 + math.sin(self.anim_t * 10) * 0.12 if self.moving else 1
        w = int(16 * z * squash)
        h = int(14 * z / squash)
        col = (90, 190, 90) if self.hit_flash <= 0 else (255, 120, 120)
        rect = (px - w // 2, py - h, w, h)
        pygame.draw.ellipse(surf, col, rect)
        pygame.draw.ellipse(surf, (60, 140, 60), rect, max(1, int(z)))
        # yeux
        ey = py - h + int(h * 0.45)
        pygame.draw.circle(surf, (10, 10, 10), (int(px - 4 * z), int(ey)), max(1, int(1.8 * z)))
        pygame.draw.circle(surf, (10, 10, 10), (int(px + 4 * z), int(ey)), max(1, int(1.8 * z)))


class Bat(Entity):
    """Ennemi volant : se deplace en ligne droite, ignore le sol, ondule."""

    def __init__(self, x: float, y: float, rng=None, aggro: float = 8.0,
                 leash: float = 14.0, speed: float = 3.2, hp: int = 1):
        import random
        super().__init__(x, y)
        self.rng = rng or random.Random()
        self.speed = speed
        self.hp = hp
        self.max_hp = hp
        self.aggro = aggro
        self.leash = leash
        self.fly_h = 34
        self.phase = self.rng.uniform(0, math.tau)
        self.dir = self.rng.uniform(0, math.tau)
        self.timer = 0.0

    def update(self, dt: float, world):
        self.timer += dt
        self.phase += dt * 9
        hero = world.hero
        dx, dy = hero.x - self.x, hero.y - self.y
        dist = math.hypot(dx, dy)
        dh = math.hypot(hero.x - self.home[0], hero.y - self.home[1])
        if 0.05 < dist < self.aggro and dh < self.leash and not hero.dead:
            self.dir = math.atan2(dy, dx)
        elif self.leash and math.hypot(self.x - self.home[0], self.y - self.home[1]) > self.leash:
            hx, hy = self.home
            self.dir = math.atan2(hy - self.y, hx - self.x)
        self.set_velocity(math.cos(self.dir), math.sin(self.dir))
        # Les chauves-souris passent partout sauf hors carte.
        self.x += self.vx * dt
        self.y += self.vy * dt
        if not (-1 < self.x < world.map.w + 1 and -1 < self.y < world.map.h + 1):
            self.dir += math.pi

    def draw(self, surf: pygame.Surface, cam):
        px, py = cam.world_to_view(self.x, self.y, self.fly_h + math.sin(self.phase) * 6)
        z = cam.zoom
        flap = math.sin(self.phase * 2) * 6 * z
        col = (70, 50, 90) if self.hit_flash <= 0 else (255, 150, 150)
        pygame.draw.line(surf, col, (px - 12 * z, py - flap), (px, py), max(1, int(2.5 * z)))
        pygame.draw.line(surf, col, (px + 12 * z, py - flap), (px, py), max(1, int(2.5 * z)))
        pygame.draw.circle(surf, col, (int(px), int(py)), max(1, int(4 * z)))
        pygame.draw.circle(surf, (255, 80, 80), (int(px), int(py - 1 * z)), max(1, int(1.2 * z)))



class ResourceNode:
    """Ressource cueillable : coffre de loot, buisson fruitier, plant mur."""

    def __init__(self, kind: str, x: float, y: float, loot=None):
        self.kind = kind          # "chest" | "fruit" | "crop"
        self.x = x
        self.y = y
        self.loot = loot or []
        self.used = False
        self.respawn = -1.0       # temps restant avant repousse (-1 = infini)

    @property
    def depth(self):
        return self.x + self.y

    def update(self, dt):
        if self.respawn >= 0:
            self.respawn -= dt
            if self.respawn <= 0:
                self.respawn = -1.0
                self.used = False

    def harvest(self, world, rng):
        if self.used:
            return None
        self.used = True
        if self.kind == "chest":
            self.respawn = -1
        elif self.kind == "fruit":
            self.respawn = 45.0
        else:  # crop : repousse facon Minecraft
            self.respawn = 60.0
        return self.loot

    def draw(self, surf, cam):
        px, py = cam.world_to_view(self.x, self.y)
        z = cam.zoom
        if self.kind == "chest":
            w, h = int(18 * z), int(12 * z)
            col = (150, 100, 45) if not self.used else (90, 70, 45)
            pygame.draw.rect(surf, col, (px - w // 2, py - h, w, h), border_radius=2)
            pygame.draw.rect(surf, (200, 170, 60), (px - 2 * z, py - h + 2 * z, 4 * z, h - 4 * z))
            if not self.used:
                glow = abs(math.sin(pygame.time.get_ticks() / 300)) * 0.6 + 0.4
                pygame.draw.circle(surf, (255, 230, 120), (int(px), int(py - h - 4 * z)), max(1, int(2 * z * glow)))
        elif self.kind == "fruit":
            r = int(8 * z)
            pygame.draw.circle(surf, (55, 125, 55), (int(px), int(py - r // 2)), r)
            if not self.used:
                for i in range(3):
                    fx = px + int(math.cos(i * 2.1) * r * 0.5)
                    fy = py - r // 2 + int(math.sin(i * 2.1) * r * 0.4)
                    pygame.draw.circle(surf, (220, 70, 70), (fx, fy), max(1, int(2.5 * z)))
        else:  # crop mure
            col = (230, 200, 110) if not self.used else (150, 130, 80)
            for i in (-1, 0, 1):
                pygame.draw.line(surf, col, (px + i * 4 * z, py), (px + i * 4 * z, py - 9 * z), max(1, int(z)))


def draw_prop(surf: pygame.Surface, cam, prop: dict):
    """Dessine un decor (arbre, rocher...) ; retourne sa cle de profondeur."""
    kind = prop["kind"]
    px, py = cam.world_to_view(prop["x"], prop["y"])
    z = cam.zoom
    rng = __import__("random").Random(prop.get("seed", 0))
    if kind == "tree":
        trunk_h = int(26 * z)
        pygame.draw.line(surf, (110, 75, 45), (px, py), (px, py - trunk_h), max(2, int(5 * z)))
        r = int(20 * z)
        dark = (40, 110, 45)
        light = (70, 150, 60)
        cy = py - trunk_h - r // 2
        pygame.draw.circle(surf, dark, (int(px - r * 0.4), int(cy + r * 0.3)), int(r * 0.8))
        pygame.draw.circle(surf, dark, (int(px + r * 0.5), int(cy + r * 0.2)), int(r * 0.75))
        pygame.draw.circle(surf, light, (int(px), int(cy)), r)
        pygame.draw.circle(surf, (95, 175, 75), (int(px - r * 0.3), int(cy - r * 0.3)), int(r * 0.55))
    elif kind == "rock":
        s = int(14 * z)
        pts = [(px - s, py), (px - s * 0.4, py - s), (px + s * 0.5, py - s * 0.8), (px + s, py)]
        pygame.draw.polygon(surf, (130, 130, 140), pts)
        pygame.draw.polygon(surf, (100, 100, 112), pts, max(1, int(z)))
    elif kind == "bush":
        r = int(9 * z)
        pygame.draw.circle(surf, (55, 125, 55), (int(px), int(py - r // 2)), r)
        pygame.draw.circle(surf, (75, 150, 70), (int(px - r // 2), int(py - r // 2)), int(r * 0.6))
    elif kind == "flower":
        c = [(240, 240, 240), (240, 200, 90), (230, 120, 160)][prop.get("seed", 0) % 3]
        pygame.draw.line(surf, (60, 120, 50), (px, py), (px, py - 6 * z), max(1, int(z)))
        pygame.draw.circle(surf, c, (int(px), int(py - 7 * z)), max(1, int(2.5 * z)))
    elif kind == "ore_pile":
        cols = {0: (200, 130, 80), 1: (210, 210, 215), 2: (240, 210, 90), 3: (110, 230, 220)}
        variant = prop.get("variant", 0)
        s_ = int(8 * z)
        base = (110, 110, 120)
        offs = [(0, 0), (-s_ // 2, -s_ // 3), (s_ // 2, -s_ // 3), (0, -s_)]
        for ox, oy in offs:
            pygame.draw.rect(surf, base, (px + ox - s_ // 2, py + oy - s_, s_, s_))
            pygame.draw.rect(surf, cols.get(variant, base), (px + ox - s_ // 4, py + oy - s_ * 0.75, s_ // 2, s_ // 2))
