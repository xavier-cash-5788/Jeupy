"""Monde de jeu : zones fonctionnelles, peuplement adapte, inventaire,
recolte (farm), minage (mine), coffres (loot), bucraft (bois), combat.

Regles anti "trop vite attaque" :
  * chaque ennemi a un rayon d'aggro COURT et un rayon de gardiennage
    (leash) autour de son point d'apparition ; il ne poursuit jamais
    le heros au-dela de sa zone ;
  * les ennemis sont peuples PAR ZONE : dense seulement dans l'arene
    "combat", tres peu ailleurs, AUCUN dans le village (spawn) ni la ferme ;
  * le heros apparait au village : il doit marcher pour trouver du danger.
"""

from __future__ import annotations

import math
import random

from engine.ascii_map import (
    TILE_DEFS, DIGGABLE,
    T_ORE_COPPER, T_ORE_IRON, T_ORE_GOLD, T_ORE_DIAMOND, T_RUBBLE, T_GRASS,
)
from engine.entity import Hero, Slime, Bat, ResourceNode
from engine.tilemap import TileMap

ORE_ITEMS = {T_ORE_COPPER: "cuivre", T_ORE_IRON: "fer",
             T_ORE_GOLD: "or", T_ORE_DIAMOND: "diamant"}
LOOT_TABLES = [
    [("piece", 3), ("bois", 5)],
    [("piece", 8), ("fer", 2)],
    [("piece", 15), ("or", 1), ("diamant", 1)],
]


class World:
    def __init__(self, seed=None, map_w=96, map_h=96):
        self.seed = seed if seed is not None else random.randint(0, 99999)
        self.rng = random.Random(self.seed)
        self.map = TileMap(map_w, map_h, seed=self.seed)
        sx, sy = self._find_spawn()
        self.hero = Hero(sx, sy)
        self.hero.max_hp = 6
        self.hero.hp = 6
        self.enemies: list = []
        self.resources: list[ResourceNode] = []
        self.particles: list[dict] = []
        self.floaters: list[dict] = []   # textes flottants "+3 bois"
        self.inventory: dict[str, int] = {}
        self.score = 0
        self.time = 0.0
        self._populate()

    # ---------------------------------------------------------- placement
    def _find_spawn(self):
        """Spawn : centre de la zone 'spawn' (village), sinon centre carte."""
        z = next((zn for zn in self.map.zones if zn.name == "spawn"), None)
        cx, cy = z.center() if z else (self.map.w / 2, self.map.h / 2)
        for r in range(0, max(self.map.w, self.map.h)):
            step = max(1, r)
            for dy in range(-r, r + 1, step):
                for dx in range(-r, r + 1, step):
                    x, y = int(cx) + dx, int(cy) + dy
                    if self.map.is_walkable(x + 0.5, y + 0.5) and not self._occupied(x, y):
                        return x + 0.5, y + 0.5
        return cx, cy

    def _occupied(self, tx, ty):
        return any(int(p["x"]) == tx and int(p["y"]) == ty for p in self.map.props)

    def _walkable_point_in(self, zone):
        for _ in range(40):
            x, y = zone.random_point(self.rng)
            if self.map.is_walkable(x, y) and not self._occupied(int(x), int(y)):
                return x, y
        return None

    def _populate(self):
        """Peuple chaque zone selon sa fonction (densite = role de la zone)."""
        density = {"combat": 10, "wild": 3, "loot": 3, "mine": 2,
                   "bucraft": 2, "farm": 0, "spawn": 0}
        for z in self.map.zones:
            for _ in range(density.get(z.name, 2)):
                pt = self._walkable_point_in(z)
                if not pt:
                    continue
                cls = Bat if self.rng.random() < 0.3 else Slime
                tough = z.name == "combat"
                e = cls(pt[0], pt[1], self.rng,
                        aggro=4.5 if tough else 3.0,   # aggro courte partout
                        leash=9.0 if tough else 6.0,   # ne quitte jamais sa zone
                        speed=2.4 if tough else 1.7,
                        hp=3 if tough else 2)
                self.enemies.append(e)

            if z.name == "loot":
                for _ in range(5):
                    pt = self._walkable_point_in(z)
                    if pt:
                        table = LOOT_TABLES[self.rng.randrange(len(LOOT_TABLES))]
                        self.resources.append(ResourceNode("chest", pt[0], pt[1], loot=list(table)))
            elif z.name == "farm":
                for _ in range(6):  # buissons fruitiers qui repoussent
                    pt = self._walkable_point_in(z)
                    if pt:
                        self.resources.append(ResourceNode("fruit", pt[0], pt[1], loot=[("fraise", 2)]))
            elif z.name == "bucraft":
                for _ in range(4):
                    pt = self._walkable_point_in(z)
                    if pt:
                        self.resources.append(ResourceNode("crop", pt[0], pt[1], loot=[("graine", 1)]))

    # ------------------------------------------------------------ items
    def add_item(self, name: str, n: int = 1):
        self.inventory[name] = self.inventory.get(name, 0) + n
        self.floaters.append({"text": f"+{n} {name}", "x": self.hero.x, "y": self.hero.y,
                              "z": 40, "life": 1.4})

    def craft(self, recipe: str) -> bool:
        """Recettes 'bucraft' simples (facon Minecraft)."""
        recipes = {
            "planche": {"bois": 1},
            "table": {"planche": 4},
            "pieu": {"planche": 3},
        }
        need = recipes.get(recipe)
        if not need:
            return False
        if any(self.inventory.get(k, 0) < v for k, v in need.items()):
            return False
        for k, v in need.items():
            self.inventory[k] -= v
        self.add_item(recipe, 1)
        return True

    # ------------------------------------------------------------ effets
    def spawn_particles(self, wx, wy, color, n=8, z0=(5, 30)):
        for _ in range(n):
            a = self.rng.uniform(0, math.tau)
            s = self.rng.uniform(20, 70)
            self.particles.append({
                "x": wx, "y": wy, "z": self.rng.uniform(*z0),
                "vz": self.rng.uniform(40, 90),
                "vx": math.cos(a) * s * 0.02, "vy": math.sin(a) * s * 0.02,
                "life": self.rng.uniform(0.3, 0.6), "color": color,
            })

    # ------------------------------------------------------------ collecte
    def gather_target(self):
        """Cible de recolte/minage pres du heros (outil E maintenu).
        Priorite : resource node, puis prop, puis tuile minable."""
        hx, hy = self.hero.x, self.hero.y
        reach = 1.3
        best, bestd = None, reach
        for r in self.resources:
            if r.used:
                continue
            d = math.hypot(r.x - hx, r.y - hy)
            if d < bestd:
                best, bestd = ("res", r), d
        if best:
            return best
        for p in self.map.props:
            if p["kind"] in ("tree", "rock", "bush", "boulder", "stump"):
                d = math.hypot(p["x"] - hx, p["y"] - hy)
                if d < bestd:
                    best, bestd = ("prop", p), d
        if best:
            return best
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                tx, ty = int(hx) + dx, int(hy) + dy
                t = self.map.tile_at(tx, ty)
                if TILE_DEFS[t].kind == DIGGABLE:
                    return ("tile", tx, ty)
        return None

    GATHER_TIME = {"tree": 1.2, "rock": 1.5, "boulder": 2.0, "bush": 0.5, "stump": 0.6}

    def gather_duration(self, target) -> float:
        if target[0] == "prop":
            return self.GATHER_TIME.get(target[1]["kind"], 1.0)
        if target[0] == "tile":
            t = self.map.tile_at(target[1], target[2])
            return {T_ORE_COPPER: 1.2, T_ORE_IRON: 1.6, T_ORE_GOLD: 2.0,
                    T_ORE_DIAMOND: 2.6}.get(t, 1.0)
        return 0.6

    def complete_gather(self, target):
        kind = target[0]
        if kind == "res":
            r = target[1]
            got = r.harvest(self, self.rng)
            if got:
                for name, n in got:
                    self.add_item(name, n)
                self.spawn_particles(r.x, r.y, (250, 220, 120), 10)
        elif kind == "prop":
            p = target[1]
            pk = p["kind"]
            if pk == "tree":
                self.add_item("bois", self.rng.randint(2, 4))
                self.map.props.remove(p)
            elif pk in ("rock", "boulder"):
                self.add_item("pierre", self.rng.randint(2, 3))
                if self.rng.random() < 0.25:
                    self.add_item("charbon", 1)
                self.map.props.remove(p)
            elif pk == "bush":
                self.add_item("baie", 1)
            elif pk == "stump":
                self.add_item("bois", 1)
                self.map.props.remove(p)
            self.spawn_particles(p["x"], p["y"], (180, 140, 90), 8)
        elif kind == "tile":
            tx, ty = target[1], target[2]
            t = self.map.tile_at(tx, ty)
            if ORE_ITEMS.get(t):
                self.add_item(ORE_ITEMS[t], self.rng.randint(1, 2))
                if t != T_ORE_DIAMOND and self.rng.random() < 0.5:
                    self.add_item("pierre", 1)
                self.spawn_particles(tx + 0.5, ty + 0.5, (200, 200, 220), 10)
                self.map.set_tile(tx, ty, T_RUBBLE)
            elif t == T_RUBBLE:
                self.add_item("pierre", 1)
                self.map.set_tile(tx, ty, T_GRASS)

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.time += dt
        self.hero.update(dt, self)

        hb = self.hero.attack_hitbox_world
        if hb:
            hx, hy, hr = hb
            for en in self.enemies:
                if en.dead or en.hit_flash > 0:
                    continue
                if math.hypot(en.x - hx, en.y - hy) < hr + en.radius:
                    en.hp -= 1
                    en.hit_flash = 0.25
                    nx, ny = (en.x - self.hero.x), (en.y - self.hero.y)
                    n = math.hypot(nx, ny) or 1
                    en.x += nx / n * 0.6
                    en.y += ny / n * 0.6
                    if en.hp <= 0:
                        en.dead = True
                        self.score += 1
                        self.spawn_particles(en.x, en.y, (120, 220, 120), 12)
                        if self.rng.random() < 0.30:
                            self.add_item("gel", 1)
                        if self.rng.random() < 0.10:
                            self.add_item("piece", 2)

        for en in self.enemies:
            if en.dead:
                continue
            en.hit_flash = max(0.0, en.hit_flash - dt)
            en.update(dt, self)
            d = math.hypot(en.x - self.hero.x, en.y - self.hero.y)
            if d < en.radius + self.hero.radius and self.hero.hit_flash <= 0:
                self.hero.hp -= 1
                self.hero.hit_flash = 1.0     # i-frames plus longues
                ux, uy = (self.hero.x - en.x) / (d or 1), (self.hero.y - en.y) / (d or 1)
                self.hero.x += ux * 0.7
                self.hero.y += uy * 0.7
                if self.hero.hp <= 0:
                    self.hero.dead = True
        self.hero.hit_flash = max(0.0, self.hero.hit_flash - dt)
        self.enemies = [e for e in self.enemies if not e.dead]

        for r in self.resources:
            r.update(dt)

        # Regen lente hors combat (1 coeur toutes les ~8 s si aucun ennemi proche)
        if not self.hero.dead and self.hero.hit_flash <= 0:
            if int(self.time) != int(self.time - dt):  # une fois par seconde
                near_foe = any(math.hypot(e.x - self.hero.x, e.y - self.hero.y) < 10
                               for e in self.enemies)
                if not near_foe and self.hero.hp < self.hero.max_hp and int(self.time) % 8 == 0:
                    self.hero.hp += 1

        for p in self.particles:
            p["life"] -= dt
            p["z"] += p["vz"] * dt
            p["vz"] -= 160 * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
        self.particles = [p for p in self.particles if p["life"] > 0]
        for fl in self.floaters:
            fl["life"] -= dt
            fl["z"] += 18 * dt
        self.floaters = [fl for fl in self.floaters if fl["life"] > 0]

    def current_zone(self):
        return self.map.zone_at(self.hero.x, self.hero.y)
