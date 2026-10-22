"""Point d'entree du jeu.

Lance la scene principale : monde isometrique genere a partir d'une carte
ASCII procedurale, decoupee en zones (village, ferme, mine, ruines/loot,
arene de combat, foret bucraft).

    python main.py            # graine aleatoire
    python main.py --seed 42  # meme carte a chaque fois
"""

import sys

from engine.scene import Game
from game.demo_scene import DemoScene


def parse_seed(argv):
    for i, a in enumerate(argv):
        if a == "--seed" and i + 1 < len(argv):
            return int(argv[i + 1])
    return None


def main():
    seed = parse_seed(sys.argv[1:])
    game = Game(title="IsoEngine - map ASCII procedurale + zones", size=(1024, 640))
    game.change_scene(DemoScene, seed=seed)
    game.run()


if __name__ == "__main__":
    main()
