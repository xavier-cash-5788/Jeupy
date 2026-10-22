# IsoEngine — map ASCII procédurale + zones fonctionnelles

## Génération procédurale en ASCII
Le monde est d'abord généré sous forme de **grille de caractères lisible**
(`engine/ascii_map.py`), puis converti en tuiles isométriques.

Chaque caractère = une tuile au sol, et certains caractères posent un décor :

| sol  | `. herbe , chemin : sable ~ eau = pont # roche f forêt " herbe haute * fleur c/i/g/d minerais cuivre/fer/or/diamant r gravier w/C/p/b cultures (blé/carotte/pomme de terre/betterave) o pavé m mousse D deepslate L tronc % feuilles P planches S pierre |
| décor| `T arbre R rocher B buisson ! souche ? bloc énorme |

- Touche **M** en jeu : sauvegarde la carte générée dans `maps/carte_<seed>.txt`.
- On peut rejouer un fichier ASCII édité à la main :
  `TileMap(ascii_source="maps/carte_42.txt")`.

## Zones fonctionnelles (une carte 96×96 par défaut)
| Zone | Rôle | Contenu |
|---|---|---|
| Village depart (spawn) | zone sûre, point d'apparition | **0 ennemi**, chemins, fleurs |
| Ferme (farm) | farm style Minecraft | parcelles blé/carotte/pomme de terre/betterave, buissons fruitiers **qui repoussent** |
| Mine (mine) | minage | carrière rocheuse, minerais cuivre→diamant **minables avec la pioche** |
| Ruines (loot) | loot | **coffres** (pièces, fer, or, diamant), ruines pavées |
| Arène (combat) | combat | clairière entourée de rochers, **zone dense en ennemis** |
| Forêt (bucraft) | construction | arbres à couper (bois), place pavée, craft facon Minecraft |
| Sauvage (wild) | exploration | quelques ennemis errants |

## Tu n'es plus attaqué trop vite
- **Aucun ennemi** au village ni à la ferme ; spawn toujours au village.
- Chaque ennemi a un **court rayon d'aggro** (~3 tuiles) et un **rayon de
  gardiennage** (leash) autour de son point d'apparition : il ne te poursuit
  jamais hors de sa zone et y retourne.
- Les ennems sont **peuplés par zone** : denses seulement dans l'arène.
- **I-frames** de 1 s après un coup + régénération lente quand aucun ennemi
  n'est proche (< 10 tuiles).

## Commandes
- `ZQSD` / flèches : déplacement (isométrique)
- `ESPACE` : attaque à l'épée (avec la souris pour orienter le coup)
- `E` maintenu : outil — récolte (farm), minage (mine), ouverture des coffres (loot), coupe de bois (bucraft). Barre de progression affichée.
- `C` : craft rapide (1 bois → 1 planche ; planches → table/pieu)
- `M` : sauvegarder la carte ASCII dans `maps/`
- `R` : nouvelle carte procédurale (nouvelle graine)

## Lancer
```bash
python main.py            # graine aléatoire
python main.py --seed 42  # carte reproductible
```

## Structure
```
engine/ascii_map.py   génération + parsing des cartes ASCII, types de tuiles
engine/tilemap.py     TileMap (ASCII -> tuiles iso), Zones, layout des régions
engine/entity.py      héros (épée + pioche), slime, chauve-souris, ressources (coffre/fruit/crop)
game/world.py         peuplement par zone, inventaire, minage/récolte/loot/craft, équilibrage
game/demo_scene.py    scène pygame : rendu isométrique, HUD, mini-carte ASCII
```
