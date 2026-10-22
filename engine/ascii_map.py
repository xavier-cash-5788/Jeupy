"""Cartes ASCII : dictionnaire de tuiles + generation procedurale en ASCII.

La carte est d'abord generee sous forme de GRILLE DE CARACTERES (ASCII), ce
qui la rend lisible, editeable a la main et versionnable dans un fichier .txt.
Chaque caractere est mappe vers une tuile via TileDict.

Exemple de fichier ASCII (lisible tel quel) :

    ~~~~~~~~~~~~~~~
    ~,,,^^^####,,,~
    ~,T,.c..o.,P,~
    ~^^^^####^^^,,~
    ~~~~~~~~~~~~~~~

Formats supportes par load_ascii_map() :
  - "chemin/vers/carte.txt"
  - "carte:chemin/vers/carte.txt"   (nom + donnees, pour les zones)
  - texte brut multi-lignes (les lignes trop courtes sont completees avec le
    caractere de remplissage, par defaut '~' = eau).
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------- types
WALKABLE = "walkable"
SOLID = "solid"          # bloque le passage (arbre, rocher, mur...)
LIQUID = "liquid"        # bloque mais peut etre traverse par un pont
DIGGABLE = "diggable"    # minable avec la pioche (E)

# Codes de terrain logiques (stables, utilises par le jeu).
(T_GRASS, T_PATH, T_SAND, T_WATER, T_ROCK_FLOOR, T_BRIDGE,
 T_FOREST, T_TALLGRASS, T_FLOWER, T_ORE_COPPER, T_ORE_IRON, T_ORE_GOLD,
 T_ORE_DIAMOND, T_RUBBLE, T_WHEAT, T_CARROTS, T_POTATOES, T_BEETROOTS,
 T_COBBLE, T_MOSSY, T_DEEPSLATE, T_LOG, T_LEAVES, T_PLANKS, T_STONE) = range(25)


class TileDef:
    """Definition d'une tuile : couleur, type de collision, variante."""

    def __init__(self, name, base, shade, kind=WALKABLE, variant=0):
        self.name = name
        self.base = base            # couleur RGB du diamant
        self.shade = shade          # couleur RGB des aretes basses
        self.kind = kind            # WALKABLE / SOLID / LIQUID / DIGGABLE
        self.variant = variant      # index de variante de rendu (sol minier...)


# palette "SNES" : couleurs saturees, variantes par legere variance (dans le rendu)
TILE_DEFS: dict[int, TileDef] = {
    T_GRASS:       TileDef("grass",       (88, 158, 74),  (74, 138, 62)),
    T_PATH:        TileDef("path",        (198, 172, 120), (178, 152, 102)),
    T_SAND:        TileDef("sand",        (228, 214, 150), (210, 196, 132)),
    T_WATER:       TileDef("water",       (58, 118, 188), (44, 98, 168), LIQUID),
    T_ROCK_FLOOR:  TileDef("rock_floor",  (140, 140, 148), (120, 120, 130)),
    T_BRIDGE:      TileDef("bridge",      (172, 128, 80), (150, 108, 66)),
    T_FOREST:      TileDef("forest",      (66, 122, 60),  (52, 100, 50)),
    T_TALLGRASS:   TileDef("tallgrass",   (104, 168, 82), (86, 142, 68)),
    T_FLOWER:      TileDef("flower",      (96, 166, 82),  (78, 140, 70)),
    T_ORE_COPPER:  TileDef("ore_copper",  (136, 136, 146), (112, 112, 124), DIGGABLE, 0),
    T_ORE_IRON:    TileDef("ore_iron",    (136, 136, 146), (112, 112, 124), DIGGABLE, 1),
    T_ORE_GOLD:    TileDef("ore_gold",    (136, 136, 146), (112, 112, 124), DIGGABLE, 2),
    T_ORE_DIAMOND: TileDef("ore_diamond", (136, 136, 146), (112, 112, 124), DIGGABLE, 3),
    T_RUBBLE:      TileDef("rubble",      (150, 148, 152), (124, 122, 128)),
    T_WHEAT:       TileDef("wheat",       (206, 178, 96),  (184, 156, 80)),
    T_CARROTS:     TileDef("carrots",     (150, 120, 70),  (128, 100, 56)),
    T_POTATOES:    TileDef("potatoes",    (140, 116, 76),  (120, 98, 62)),
    T_BEETROOTS:   TileDef("beetroots",   (150, 100, 80),  (128, 84, 66)),
    T_COBBLE:      TileDef("cobble",      (124, 124, 132), (100, 100, 110)),
    T_MOSSY:       TileDef("mossy",       (112, 128, 108), (90, 106, 88)),
    T_DEEPSLATE:   TileDef("deepslate",   (80, 80, 88),    (60, 60, 70)),
    T_LOG:         TileDef("log",         (110, 80, 48),   (88, 62, 38)),
    T_LEAVES:      TileDef("leaves",      (56, 116, 52),   (42, 92, 42)),
    T_PLANKS:      TileDef("planks",      (176, 138, 88),  (152, 118, 74)),
    T_STONE:       TileDef("stone",       (128, 128, 136), (104, 104, 114)),
}

# caractere ASCII -> code de tuile
CHAR_TO_TILE: dict[str, int] = {
    ".": T_GRASS, ",": T_PATH, ":": T_SAND, "~": T_WATER, "=": T_BRIDGE,
    "#": T_ROCK_FLOOR, "f": T_FOREST, "\"": T_TALLGRASS, "*": T_FLOWER,
    "c": T_ORE_COPPER, "i": T_ORE_IRON, "g": T_ORE_GOLD, "d": T_ORE_DIAMOND,
    "r": T_RUBBLE,
    "w": T_WHEAT, "C": T_CARROTS, "p": T_POTATOES, "b": T_BEETROOTS,
    "o": T_COBBLE, "m": T_MOSSY, "D": T_DEEPSLATE,
    "L": T_LOG, "%": T_LEAVES, "P": T_PLANKS, "S": T_STONE,
    " ": T_GRASS,
}

# caractere ASCII -> prop (objet 3D pose sur la tuile)
CHAR_TO_PROP: dict[str, str] = {
    "T": "tree", "R": "rock", "B": "bush", "!": "stump", "?": "boulder",
}

PROP_COLLIDER = {"tree": 0.35, "rock": 0.35, "boulder": 0.42, "bush": 0.0, "stump": 0.0}

DEFAULT_FILL = "~"


def tile_kind(t: int) -> str:
    return TILE_DEFS[t].kind


def is_walkable_tile(t: int) -> bool:
    return TILE_DEFS[t].kind == WALKABLE


class TileDict:
    """Nom logique -> code de tuile (pour lire des cartes nommees)."""

    def __init__(self, mapping: dict[str, int] | None = None):
        self.map = {}
        if mapping:
            for k, v in mapping.items():
                self.add(k, v)

    def add(self, name: str, tile: int):
        self.map[name] = tile

    def get(self, name: str) -> int:
        return self.map[name]


# ------------------------------------------------------------- parsing
def load_ascii_map(data: str, fill: str = DEFAULT_FILL) -> list[list[str]]:
    """Charge une grille ASCII depuis un chemin fichier, 'nom:chemin', ou
    directement du texte multi-lignes. Retourne list[ligne[str]] rectangulaire."""
    text = data
    name_part, _, maybe_path = data.partition(":")
    if maybe_path:
        try:
            with open(maybe_path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            pass
    else:
        try:
            with open(data, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            pass  # consider it as raw ascii text

    lines = [ln.rstrip("\n").rstrip("\r") for ln in text.splitlines()]
    lines = [ln for ln in lines if ln.strip() != "" or ln]  # garde tout
    if not lines:
        raise ValueError(f"carte ASCII vide : {data!r}")
    w = max(len(ln) for ln in lines)
    grid = [(ln + fill * (w - len(ln)))[:w] for ln in lines]
    bad = sorted({ch for row in grid for ch in row
                  if ch not in CHAR_TO_TILE and ch not in CHAR_TO_PROP})
    if bad:
        raise ValueError(f"caracteres ASCII inconnus : {bad}")
    return grid


def save_ascii_map(grid: list[list[str]], path: str):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join("".join(row) for row in grid) + "\n")


# ------------------------------------------------------- generation ASCII
class AsciiGenerator:
    """Genere une grande carte monde (list[str]) en ASCII par regions
    fonctionnelles : farm, mine, loot, combat, bucraft...

    Chaque region devient plus tard une Zone jouable ; ici on produit
    simplement la trame ASCII (sol + props + bordures).
    """

    def __init__(self, w: int = 96, h: int = 96, seed: int | None = None):
        self.w = w
        self.h = h
        self.rng = random.Random(seed)

    # -- bruit de valeur simple ------------------------------------------
    def _noise(self, scale: int) -> list[list[float]]:
        rng = self.rng
        gw, gh = self.w // scale + 2, self.h // scale + 2
        pts = [[rng.random() for _ in range(gw)] for _ in range(gh)]

        def sm(t):
            return t * t * (3 - 2 * t)

        out = [[0.0] * self.w for _ in range(self.h)]
        for y in range(self.h):
            for x in range(self.w):
                fx, fy = x / scale, y / scale
                x0, y0 = int(fx), int(fy)
                tx, ty = sm(fx - x0), sm(fy - y0)
                a = pts[y0][x0] + (pts[y0][x0 + 1] - pts[y0][x0]) * tx
                b = pts[y0 + 1][x0] + (pts[y0 + 1][x0 + 1] - pts[y0 + 1][x0]) * tx
                out[y][x] = a + (b - a) * ty
        return out

    def generate(self, layout: list[dict]) -> list[str]:
        """layout = liste de regions [{name,x,y,w,h}, ...] -> grille ASCII."""
        w, h = self.w, self.h
        g = [[DEFAULT_FILL] * w for _ in range(h)]
        n_land = self._noise(10)
        n_detail = self._noise(4)

        # 1) Masse principale : ile entouree d'eau, plages en bordure.
        for y in range(h):
            for x in range(w):
                edge = min(x, y, w - 1 - x, h - 1 - y)
                land = n_land[y][x] - max(0.0, (6 - edge)) * 0.16
                if land > 0.52:
                    g[y][x] = "."
                elif land > 0.30:
                    g[y][x] = "." if n_detail[y][x] < 0.7 else ","
                elif land > 0.22:
                    g[y][x] = ":"  # plage
                # sinon reste eau

        # 2) Regions fonctionnelles : elles peignent leur sol en ASCII.
        painters = {
            "spawn": self._paint_spawn,
            "farm": self._paint_farm,
            "mine": self._paint_mine,
            "loot": self._paint_loot,
            "combat": self._paint_combat,
            "bucraft": self._paint_bucraft,
            "wild": self._paint_wild,
        }
        for reg in layout:
            fn = painters.get(reg["name"], self._paint_wild)
            fn(g, reg)

        # 3) Chemins reliant les centres de regions (ASCII ',' + ponts '=').
        centers = [reg for reg in layout]
        for a, b in zip(centers, centers[1:]):
            self._carve_path(g, self._center(a), self._center(b))
        spawn = next((r for r in layout if r["name"] == "spawn"), layout[0])
        for reg in layout:
            if reg is not spawn:
                self._carve_path(g, self._center(spawn), self._center(reg))

        return ["".join(row) for row in g]

    @staticmethod
    def _center(reg: dict) -> tuple[int, int]:
        return reg["x"] + reg["w"] // 2, reg["y"] + reg["h"] // 2

    def _fill_rect(self, g, x0, y0, x1, y1, ch_fn):
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                g[y][x] = ch_fn(x, y)

    def _scatter(self, g, x0, y0, x1, y1, choices: list[tuple[str, float]], only=".,:"):
        rng = self.rng
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                if g[y][x] in only:
                    r, acc = rng.random(), 0.0
                    for ch, p in choices:
                        acc += p
                        if r < acc:
                            g[y][x] = ch
                            break

    # -- peintres de regions ----------------------------------------------
    def _paint_spawn(self, g, reg):
        x, y, w, h = reg["x"], reg["y"], reg["w"], reg["h"]
        self._fill_rect(g, x, y, x + w, y + h, lambda i, j: ".")
        cx, cy = self._center(reg)
        self._fill_rect(g, cx - 2, cy - 2, cx + 3, cy + 3, lambda i, j: ",")
        self._scatter(g, x, y, x + w, y + h, [("B", 0.05), ("*", 0.06), ("T", 0.03)])

    def _paint_farm(self, g, reg):
        x, y, w, h = reg["x"], reg["y"], reg["w"], reg["h"]
        rng = self.rng
        self._fill_rect(g, x, y, x + w, y + h, lambda i, j: ".")
        # parcelles labourées en rangées (comme Minecraft : blocs de culture)
        crops = ["w", "C", "p", "b"]
        px0, py0 = x + 2, y + 2
        pw, ph = max(4, w - 4), max(4, h - 4)
        for j in range(py0, py0 + ph):
            crop = crops[(j - py0) % len(crops)]
            for i in range(px0, px0 + pw):
                if rng.random() < 0.85:
                    g[j][i] = crop
                else:
                    g[j][i] = ":"
        # mare pour l'ambiance + cloture autour
        self._scatter(g, x, y, x + w, y + h, [("=", 0.02)])
        pond_x, pond_y = x + w - 4, y + h - 4
        self._fill_rect(g, pond_x, pond_y, pond_x + 3, pond_y + 2, lambda i, j: "~")
        self._scatter(g, x, y, x + w, y + h, [("B", 0.04), ("T", 0.02)])

    def _paint_mine(self, g, reg):
        x, y, w, h = reg["x"], reg["y"], reg["w"], reg["h"]
        rng = self.rng
        # sol rocheux ; carriere circulaire
        cx, cy = self._center(reg)
        rad = min(w, h) // 2

        def stone(i, j):
            d = (i - cx) ** 2 + (j - cy) ** 2
            if d < rad * rad:
                r = rng.random()
                if r < 0.10:
                    return "c"
                if r < 0.16:
                    return "i"
                if r < 0.19:
                    return "g"
                if r < 0.205:
                    return "d"
                if r < 0.26:
                    return "D"
                if r < 0.32:
                    return "o"
                return "#"
            return "." if rng.random() < 0.9 else ","
        self._fill_rect(g, x, y, x + w, y + h, stone)
        # entree : couloir de dalles depuis le bord jusqu'au centre
        ey = cy
        for i in range(x, cx):
            g[ey][i] = "o" if g[ey][i] == "~" else g[ey][i]
        self._scatter(g, x, y, x + w, y + h, [("R", 0.03), ("!", 0.02)], only=".,:")

    def _paint_loot(self, g, reg):
        x, y, w, h = reg["x"], reg["y"], reg["w"], reg["h"]
        rng = self.rng
        self._fill_rect(g, x, y, x + w, y + h, lambda i, j: ",")
        # allees de ruines + coins herbe
        for j in range(y, y + h):
            for i in range(x, x + w):
                if (i - x) % 5 == 0 or (j - y) % 5 == 0:
                    g[j][i] = "o"
                elif rng.random() < 0.12:
                    g[j][i] = "m"
                elif rng.random() < 0.10:
                    g[j][i] = "\""
        self._scatter(g, x, y, x + w, y + h, [("R", 0.05), ("?", 0.03), ("B", 0.03)], only=".,:om\"")

    def _paint_combat(self, g, reg):
        x, y, w, h = reg["x"], reg["y"], reg["w"], reg["h"]
        rng = self.rng
        self._fill_rect(g, x, y, x + w, y + h, lambda i, j: ".")
        # clairiere : anneau de rochers/arbres, interieur herbe haute
        cx, cy = self._center(reg)
        rad = min(w, h) // 2
        for j in range(y, y + h):
            for i in range(x, x + w):
                d = ((i - cx) / rad) ** 2 + ((j - cy) / (rad * 0.8)) ** 2
                if 0.75 < d < 1.05:
                    if rng.random() < 0.5:
                        g[j][i] = rng.choice(["T", "R", "!"])
                    else:
                        g[j][i] = "#"
                elif d <= 0.75:
                    g[j][i] = "\"" if rng.random() < 0.35 else "."
        # acces depuis l'ouest
        for i in range(x, cx):
            if g[cy][i] in "TR!#":
                g[cy][i] = ","

    def _paint_bucraft(self, g, reg):
        x, y, w, h = reg["x"], reg["y"], reg["w"], reg["h"]
        rng = self.rng
        self._fill_rect(g, x, y, x + w, y + h, lambda i, j: ".")
        # foret dense (bois de construction)
        for j in range(y, y + h):
            for i in range(x, x + w):
                r = rng.random()
                if r < 0.16:
                    g[j][i] = "T"
                elif r < 0.20:
                    g[j][i] = "%"
                elif r < 0.23:
                    g[j][i] = "f"
                elif r < 0.25:
                    g[j][i] = "L"
                elif r < 0.28:
                    g[j][i] = "B"
        # petite clairiere centrale pavee (place du village)
        cx, cy = self._center(reg)
        self._fill_rect(g, cx - 3, cy - 2, cx + 4, cy + 3, lambda i, j: "P")

    def _paint_wild(self, g, reg):
        x, y, w, h = reg["x"], reg["y"], reg["w"], reg["h"]
        self._scatter(g, x, y, x + w, y + h,
                      [("T", 0.06), ("B", 0.05), ("\"", 0.06), ("*", 0.04), ("R", 0.02)])

    # -- chemins ------------------------------------------------------------
    def _carve_path(self, g, a, b):
        rng = self.rng
        x, y = a
        gx = 1 if b[0] > x else (-1 if b[0] < x else 0)
        gy = 1 if b[1] > y else (-1 if b[1] < y else 0)
        steps = 0
        while (x, y) != b and steps < self.w * self.h:
            steps += 1
            if g[y][x] in ".: \"*~":
                g[y][x] = "=" if g[y][x] == "~" else ","
            # avance vers b, axe prioritaire aléatoire
            if abs(b[0] - x) >= abs(b[1] - y) and gx:
                x += gx
                if rng.random() < 0.25 and gy:
                    y += gy
            elif gy:
                y += gy
                if rng.random() < 0.25 and gx:
                    x += gx
            else:
                break
            x = max(1, min(self.w - 2, x))
            y = max(1, min(self.h - 2, y))
        if 0 <= b[1] < self.h and 0 <= b[0] < self.w:
            if g[b[1]][b[0]] in ".: \"*":
                g[b[1]][b[0]] = ","
