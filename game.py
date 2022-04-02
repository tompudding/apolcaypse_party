import ui
import globals
from globals.types import Point
import drawing
import cmath
import math
import pygame
import traceback
import random


class MainMenu(ui.HoverableBox):
    line_width = 1

    def __init__(self, parent, bl, tr):
        self.border = drawing.QuadBorder(globals.ui_buffer, line_width=self.line_width)
        self.level_buttons = []
        self.ticks = []
        super(MainMenu, self).__init__(parent, bl, tr, (0.05, 0.05, 0.05, 1))
        self.text = ui.TextBox(
            self,
            Point(0, 0.8),
            Point(1, 0.95),
            "Keep the Streak Alive",
            3,
            colour=drawing.constants.colours.white,
            alignment=drawing.texture.TextAlignments.CENTRE,
        )
        self.info = ui.TextBox(
            self,
            Point(0, 0.0),
            Point(1, 0.05),
            "Right button cancels a throw. Escape for main menu",
            1.5,
            colour=drawing.constants.colours.white,
            alignment=drawing.texture.TextAlignments.CENTRE,
        )
        self.border.set_colour(drawing.constants.colours.red)
        self.border.set_vertices(self.absolute.bottom_left, self.absolute.top_right)
        self.border.enable()
        self.quit_button = ui.TextBoxButton(self, "Quit", Point(0.45, 0.1), size=2, callback=self.parent.quit)

        pos = Point(0.2, 0.8)
        for i, level in enumerate(parent.levels):
            button = ui.TextBoxButton(
                self,
                f"{i}: {level.name}",
                pos,
                size=2,
                callback=call_with(self.start_level, i),
            )
            self.ticks.append(
                ui.TextBox(
                    self,
                    pos - Point(0.05, 0.01),
                    tr=pos + Point(0.1, 0.04),
                    text="\x9a",
                    scale=3,
                    colour=(0, 1, 0, 1),
                )
            )
            if not self.parent.done[i]:
                self.ticks[i].disable()

            pos.y -= 0.1
            self.level_buttons.append(button)

    def start_level(self, pos, level):
        self.disable()
        self.parent.current_level = level
        self.parent.init_level()
        self.parent.stop_throw()
        self.parent.paused = False

    def enable(self):
        if not self.enabled:
            self.root.register_ui_element(self)
            self.border.enable()
        for button in self.level_buttons:
            button.enable()
        super(MainMenu, self).enable()
        for i, tick in enumerate(self.ticks):
            if self.parent.done[i]:
                tick.enable()
            else:
                tick.disable()

    def disable(self):
        if self.enabled:
            self.root.remove_ui_element(self)
            self.border.disable()
        super(MainMenu, self).disable()
        for tick in self.ticks:
            tick.disable()


class GameOver(ui.HoverableBox):
    line_width = 1

    def __init__(self, parent, bl, tr):
        self.border = drawing.QuadBorder(globals.ui_buffer, line_width=self.line_width)
        super(GameOver, self).__init__(parent, bl, tr, (0, 0, 0, 1))
        self.text = ui.TextBox(
            self,
            Point(0, 0.5),
            Point(1, 0.6),
            "You Kept the Streak Alive! Amazing!",
            2,
            colour=drawing.constants.colours.white,
            alignment=drawing.texture.TextAlignments.CENTRE,
        )
        self.border.set_colour(drawing.constants.colours.red)
        self.border.set_vertices(self.absolute.bottom_left, self.absolute.top_right)
        self.border.enable()
        self.replay_button = ui.TextBoxButton(self, "Replay", Point(0.1, 0.1), size=2, callback=self.replay)
        self.quit_button = ui.TextBoxButton(self, "Quit", Point(0.7, 0.1), size=2, callback=parent.quit)

    def replay(self, pos):
        self.parent.replay()
        self.disable()

    def enable(self):
        if not self.enabled:
            self.root.register_ui_element(self)
            self.border.enable()
        super(GameOver, self).enable()

    def disable(self):
        if self.enabled:
            self.root.remove_ui_element(self)
            self.border.disable()
        super(GameOver, self).disable()


class GameView(ui.RootElement):
    text_fade_duration = 1000

    def __init__(self):
        super(GameView, self).__init__(Point(0, 0), globals.screen)

        self.atlas = drawing.texture.TextureAtlas("atlas_0.png", "atlas.txt", extra_names=None)

        self.paused = False

    def quit(self, pos):
        raise SystemExit()

    def key_down(self, key):
        print("Game key down", key)
        if key == pygame.locals.K_ESCAPE:
            if self.main_menu.enabled:
                return self.quit(0)
            self.main_menu.enable()
            self.paused = True
            globals.cursor.enable()
            self.level_text.disable()
            if self.sub_text:
                self.sub_text.disable()
            if self.next_level_menu:
                self.next_level_menu.disable()
            if self.game_over:
                self.game_over.disable()
        if key == pygame.locals.K_SPACE:
            # space is as good as the left button
            self.mouse_button_down(globals.mouse_screen, 1)

        elif key in (pygame.locals.K_RSHIFT, pygame.locals.K_LSHIFT):
            # shifts count as the right button
            self.mouse_button_down(globals.mouse_screen, 3)

    def key_up(self, key):
        print("Game key up", key)

    def update(self, t):

        if self.paused:
            return

    def draw(self):
        drawing.draw_no_texture(globals.ui_buffer)
        drawing.draw_all(globals.quad_buffer, self.atlas.texture)
        drawing.line_width(1)
        drawing.draw_no_texture(globals.line_buffer)

    def mouse_motion(self, pos, rel, handled):
        if self.paused:
            return super(GameView, self).mouse_motion(pos, rel, handled)

    def mouse_button_down(self, pos, button):
        print("Mouse down", pos, button)
        if self.paused:
            return super(GameView, self).mouse_button_down(pos, button)

        return False, False

    def mouse_button_up(self, pos, button):
        if self.paused:
            return super(GameView, self).mouse_button_up(pos, button)

        print("Mouse up", pos, button)

        return False, False
