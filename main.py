#!/usr/bin/env python3
"""Point d'entree : lance la demo du moteur isometrique.

Usage :
    python main.py [--seed 1234] [--size 1280x720]
"""

from __future__ import annotations

import argparse

from engine.scene import Game
from game.demo_scene import DemoScene


def parse_size(s: str) -> tuple[int, int]:
    w, _, h = s.partition("x")
    return int(w), int(h)


def main():
    ap = argparse.ArgumentParser(description="IsoEngine - demo 2D isometrique style Zelda SNES")
    ap.add_argument("--seed", type=int, default=None, help="graine de generation de carte")
    ap.add_argument("--size", type=str, default="1024x640", help="resolution fenetre, ex: 1280x720")
    args = ap.parse_args()

    game = Game(title="IsoEngine - Aventure Isometrique (style Zelda SNES)", size=parse_size(args.size))
    game.change_scene(DemoScene, seed=args.seed)
    game.run()


if __name__ == "__main__":
    main()
