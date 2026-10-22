# IsoEngine — moteur 2D isométrique style Zelda SNES (100 % Python)

Moteur de jeu + scène de démo : vue isométrique diamant 2:1, génération
procedurale de carte (île, plage, chemin, ponts), héros qui se déplace par
rapport à l'écran (comme sur SNES), combat à l'épée, ennemis (slimes qui
poursuivent, chauves-souris volantes), tri de profondeur painter's-order,
caméra fluide avec zoom, HUD cœurs façon Zelda.

Aucun asset externe : tous les sprites sont dessinés procéduralement
(remplaçables plus tard par des spritesheets).

## Lancer

```bash
pip install -r requirements.txt
python main.py                 # fenêtre 1024x640
python main.py --seed 42       # carte reproductible
python main.py --size 1280x720
```

## Contrôles

| Touche            | Action                                        |
|-------------------|-----------------------------------------------|
| ZQSD / WASD / flèches | Déplacement (relatif à l'écran, style Zelda) |
| ESPACE            | Coup d'épée                                   |
| +/-               | Zoom caméra                                   |
| R                 | Générer une nouvelle carte                    |
| H                 | Afficher/cacher l'aide                        |
| ESC               | Quitter                                       |

## Architecture (`engine/`)

- `iso.py` — projection dimétrique 2:1 : `world_to_screen`, `screen_to_world`,
  conversion angle-écran → direction monde.
- `camera.py` — caméra isométrique : suivi lissé, clamp aux bornes de carte,
  zoom, culling (`view_rect`).
- `tilemap.py` — carte de tuiles générée par bruit de valeur interpolé
  (herbe/chemin/eau/sable/rocher/pont) + props (arbres, rochers, buissons,
  fleurs), rendu des losanges au sol avec reflets d'eau animés.
- `entity.py` — classes `Entity` (déplacement + collisions axiales avec
  glissement), `Hero` (attaque en arc, hitbox monde), `Slime`, `Bat`,
  et rendu procédural des props.
- `scene.py` — boucle principale `Game` (60 FPS, événements) et interface
  `Scene` (enter/exit/handle_event/update/draw).

Le jeu lui-même est dans `game/demo_scene.py` (monde, IA, combat, particules,
HUD) : il n'utilise **que** l'API du moteur, exactement comme un futur vrai
jeu l'utiliserait.

## Étapes suivantes possibles

1. Spritesheets pixel-art (charger des PNG à la place des primitives).
2. Éditeur de carte (clic souris → `screen_to_world` est déjà prêt).
3. Donjons / plusieurs scènes, PNJ, objets à ramasser.
4. Sons & musique (pygame.mixer).
