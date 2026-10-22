"""Scenes + boucle principale du moteur (Game).

Une Scene = update(dt) / draw(surf) / on_event(e). Le Game gere pygame,
la boucle FPS, la transition entre scenes.
"""

from __future__ import annotations

import sys

import pygame


class Scene:
    name = "scene"

    def __init__(self, game: "Game"):
        self.game = game

    def enter(self):
        pass

    def exit(self):
        pass

    def handle_event(self, e: pygame.event.Event):
        pass

    def update(self, dt: float):
        pass

    def draw(self, surf: pygame.Surface):
        pass


class Game:
    def __init__(self, title: str = "IsoEngine", size: tuple[int, int] = (1024, 640), fps: int = 60):
        pygame.init()
        pygame.display.set_caption(title)
        self.screen = pygame.display.set_mode(size)
        self.clock = pygame.time.Clock()
        self.fps = fps
        self.running = True
        self.scene: Scene | None = None
        self._next_scene: type[Scene] | None = None
        self.font = pygame.font.SysFont("monospace", 16, bold=True)

    # -------------------------------------------------------------- scenes
    def change_scene(self, scene_cls: type[Scene], **kwargs):
        if self.scene:
            self.scene.exit()
        self.scene = scene_cls(self, **kwargs)
        self.scene.enter()

    # ------------------------------------------------------------ mainloop
    def run(self):
        while self.running:
            dt = min(self.clock.tick(self.fps) / 1000.0, 1 / 20)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    self.running = False
                elif self.scene:
                    self.scene.handle_event(e)
            if self.scene:
                self.scene.update(dt)
                self.scene.draw(self.screen)
            pygame.display.flip()
        pygame.quit()
        sys.exit(0)
