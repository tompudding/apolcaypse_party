import ui
import globals
from globals.types import Point
import drawing
import cmath
import math
import pygame
import traceback
import random
import os

music_start = 0 * 1000


class DifficultyChooser(ui.UIElement):
    def __init__(self, parent, bl, tr, text_options, scale, colour):
        self.text_options = text_options
        self.current_text = 0
        self.scale = scale
        self.text_colour = colour
        self.alignment = (drawing.texture.TextAlignments.CENTRE,)
        super().__init__(
            parent,
            bl,
            tr,
        )

        # Put the current text in the middle
        self.text = ui.TextBox(
            self,
            Point(0.1, 0),
            Point(0.9, 1),
            self.text_options[self.current_text],
            self.scale,
            self.text_colour,
            alignment=self.alignment,
        )

        self.left_button = ui.TextBoxButton(self, "<", Point(0, 0.2), size=self.scale, callback=self.left)
        self.right_button = ui.TextBoxButton(self, ">", Point(0.8, 0.2), size=self.scale, callback=self.right)

    def left(self, pos):
        self.current_text = (self.current_text + len(self.text_options) - 1) % len(self.text_options)
        self.update()

    def right(self, pos):
        self.current_text = (self.current_text + 1) % len(self.text_options)
        self.update()

    def update(self):
        self.text.set_text(self.text_options[self.current_text])

    def get_text(self):
        return self.text_options[self.current_text]


class Bolt:
    speed = 5

    def __init__(self, atlas):
        self.pos = None
        self.target = None
        self.size = Point(64, 64)
        self.atlas = atlas
        self.quad = drawing.Quad(globals.quad_buffer)

    def disable(self):
        self.quad.disable()

    def enable(self):
        self.quad.enable()

    def set_pos(self, pos, target):
        self.pos = pos
        self.target = target
        pos = self.pos + (self.size / 2)
        self.quad.set_vertices(self.pos, self.pos + self.size, 10)
        self.last = globals.music_pos

    def update(self, music_pos):
        elapsed = music_pos - self.last
        self.last = music_pos
        distance = elapsed * self.speed
        diff = self.target.get_centre() - self.pos
        length = diff.length()
        if length < 50:
            return True
        vector = diff / length
        move = vector * self.speed
        self.pos += move
        self.quad.set_vertices(self.pos, self.pos + self.size, 10)

    def set_type(self, num):
        self.quad.set_texture_coordinates(
            self.atlas.texture_coords(f"resource/sprites/magic_bolt_{num%8+1}.png")
        )


class Sprite:
    fps = 12
    gravity = -0.007
    jump_velocity = 2
    duck_duration = 200

    def __init__(self, parent, bl, tr, tc_names, atlas):
        self.bl = bl
        self.tr = tr
        self.size = self.tr - self.bl
        self.parent = parent
        self.tc_coords = [atlas.texture_coords(name) for name in tc_names]
        self.smashing_tc_coords = [atlas.texture_coords(f"resource/sprites/a{n}.png") for n in range(1, 5)]

        self.quad = drawing.Quad(globals.quad_buffer, tc=self.tc_coords[0])
        self.quad.set_vertices(bl, tr, 50)
        self.per_frame = 1000 / self.fps
        self.jumping = False
        self.pos = Point(0, 0)
        self.start_pos = self.bl
        self.velocity = 0
        self.ducking = False
        # We make 16 secret bolt sprites and set them to disabled
        self.bolts = [Bolt(atlas) for i in range(16)]
        for bolt in self.bolts:
            bolt.disable()
        self.smashing = False

        self.active_bolts = []

    def update(self, music_pos):
        new_bolts = []
        for bolt in self.active_bolts:
            if bolt.update(music_pos):
                bolt.disable()
                self.bolts.append(bolt)
            else:
                new_bolts.append(bolt)
        self.active_bolts = new_bolts

        animated = False

        if self.ducking:
            if music_pos < self.ducking:
                return
            else:
                self.ducking = False
                self.quad.translate(Point(0, -32))
            animated = True

        if self.jumping:
            t = music_pos - self.jumping
            self.pos = Point(0, (self.jump_velocity * t) + (self.gravity * t * t))
            if self.pos.y < 0:
                self.pos = Point(0, 0)
                self.jumping = False
            pos = self.start_pos + self.pos
            self.quad.set_vertices(pos, pos + self.size, 50)

            animated = True

        if self.smashing:
            t = music_pos - self.smashing
            pos = int(t // self.per_frame)
            if pos < len(self.smashing_tc_coords):
                self.quad.set_texture_coordinates(self.smashing_tc_coords[pos])
                animated = True
            else:
                self.smashing = False

        if animated:
            return

        pos = int(music_pos // self.per_frame) % len(self.tc_coords)
        self.quad.set_texture_coordinates(self.tc_coords[pos])

    def jump(self, high=False):
        # For a jump we switch to a fixed image for the duration, and arc upwards in a parabola
        self.jumping = globals.music_pos
        self.quad.set_texture_coordinates(self.tc_coords[0])
        self.jump_velocity = 2.4 if high else 2
        self.last_pos = 0

    def duck(self):
        self.ducking = globals.music_pos + self.duck_duration
        self.quad.set_texture_coordinates(self.tc_coords[2])
        self.quad.translate(Point(0, 32))

    def shoot(self, num):
        # We create a new active bolt
        if len(self.bolts) == 0:
            return

        bolt = self.bolts.pop(0)
        bolt.set_pos(Point(*self.quad.vertex[0][:2]), self.parent.right_track)
        bolt.target = self.parent.right_track
        bolt.set_type(num)
        bolt.enable()
        self.active_bolts.append(bolt)

    def smash(self, wall):
        print("smash!", wall)
        wall.smash()
        self.smashing = globals.music_pos
        # Start a short animation


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
            "To the Beat of the Mountain King",
            3,
            colour=drawing.constants.colours.white,
            alignment=drawing.texture.TextAlignments.CENTRE,
        )
        self.info = ui.TextBox(
            self,
            Point(0, 0.0),
            Point(1, 0.05),
            "Hit the keys to save your adventurer, until your inevitable defeat!",
            1.5,
            colour=drawing.constants.colours.white,
            alignment=drawing.texture.TextAlignments.CENTRE,
        )
        self.difficulty_text = ui.TextBox(
            self,
            Point(0.2, 0.515),
            Point(0.9, 0.615),
            "Difficulty:",
            2,
            colour=drawing.constants.colours.white,
            alignment=drawing.texture.TextAlignments.LEFT,  # This should be right aligned really but apparently I didn't implement that
        )
        self.difficulty = DifficultyChooser(
            self,
            Point(0.44, 0.56),
            Point(0.75, 0.61),
            ["Easy", "Medium", "Hard", "Impossible"],
            2,
            colour=drawing.constants.colours.white,
        )
        self.border.set_colour(drawing.constants.colours.red)
        self.border.set_vertices(self.absolute.bottom_left, self.absolute.top_right)
        self.border.enable()
        self.start_button = ui.TextBoxButton(
            self, "Play", Point(0.31, 0.1), size=2, callback=self.parent.start
        )
        self.resume_button = ui.TextBoxButton(
            self, "Resume", Point(0.55, 0.1), size=2, callback=self.parent.resume
        )
        self.resume_button.disable()
        self.quit_button = ui.TextBoxButton(self, "Quit", Point(0.45, 0.1), size=2, callback=self.parent.quit)

        pos = Point(0.2, 0.8)

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

    def get_difficulty(self):
        return self.difficulty.current_text

    def get_difficulty_text(self):
        return self.difficulty.get_text()

    def set_difficulty(self, difficulty):
        self.difficulty.current_text = difficulty
        self.difficulty.update()


class GameOver(ui.HoverableBox):
    line_width = 1

    def __init__(self, parent, bl, tr):
        self.border = drawing.QuadBorder(globals.ui_buffer, line_width=self.line_width)
        super(GameOver, self).__init__(parent, bl, tr, (0, 0, 0, 1))
        self.text = ui.TextBox(
            self,
            Point(0, 0.5),
            Point(1, 0.6),
            f"You won! Inconceivable, with the best possible time of {format_time(globals.music_pos)}",
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
        self.parent.main_menu.enable()
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


class Note:
    def __init__(self, ms, duration, instrument, note, difficulty):
        self.time = ms
        self.instrument = instrument
        self.duration = duration
        self.note = note
        self.difficulty = difficulty
        self.block = None


class NoteTiming:
    def __init__(self, filename):
        self.notes = []

        interval = None
        with open(filename, "r") as file:
            for line in file:
                line = line.strip()
                if "#" in line:
                    line = line[: line.index("#")].strip()

                if not line:
                    continue

                if interval is None and line.startswith("+"):
                    # Line of the form +n/m means the previous entry was the start, the next was the end, and they're m beats apart, with the first n set
                    n, m = (int(v) for v in line[1:].split("/"))
                    interval = [note, n, m]
                    continue
                ms, duration, instrument, note, difficulty = line.split(",")
                ms, duration, difficulty = (float(v) for v in (ms, duration, difficulty))
                instrument, note = (v.strip() for v in (instrument, note))
                note = Note(ms, duration, instrument, note, difficulty)
                if interval:
                    diff = (note.time - interval[0].time) / interval[2]
                    for i in range(1, interval[1]):
                        new_note = Note(
                            ms=interval[0].time + diff * i,
                            duration=interval[0].duration,
                            instrument=interval[0].instrument,
                        )
                        self.notes.append(new_note)
                    interval = None

                self.notes.append(note)

        self.current_note = 0
        self.notes.sort(key=lambda note: note.time)
        self.current_play = self.notes[::]

    def get_notes(self, pos):
        for i, note in enumerate(self.current_play):
            if note.time <= pos:
                yield note
            else:
                self.current_play = self.current_play[i:]
                return

        self.current_play = []

    def get_all_notes(self, instruments, difficulty):
        for note in self.notes:

            if note.instrument in instruments and note.difficulty <= difficulty:
                yield note

    @property
    def current(self):
        try:
            return self.notes[self.current_note]
        except IndexError:
            return 9999999999

    def next(self):
        self.current_note += 1


class Line(object):
    def __init__(self, parent, start, end, colour=(1, 0, 0, 1)):
        self.parent = parent
        self.line = drawing.Line(globals.line_buffer)
        self.line.set_colour(colour)

        self.set(start, end)

    def set_start(self, start):
        self.start = start
        self.update()

    def set_end(self, end):
        self.end = end
        self.update()

    def set(self, start, end):
        self.start = start
        self.end = end
        self.update()

    def update(self):
        if self.start and self.end:
            self.line.set_vertices(self.start, self.end, 2)

    def enable(self):
        self.line.enable()

    def disable(self):
        self.line.disable()


note_subs = {
    0: {"q": "a", "e": "d", "space": " ", "enter": chr(pygame.locals.K_RETURN)},  # easy
    1: {"q": "a", "e": "d", "space": " ", "enter": chr(pygame.locals.K_RETURN)},  # medium
    2: {"q": "a", "e": "d", "space": " ", "enter": chr(pygame.locals.K_RETURN)},  # hard
    3: {"space": " ", "enter": chr(pygame.locals.K_RETURN)},  # expert
}

print_trans = {
    " ": "_",
}


def letter_from_note(note, difficulty):
    try:
        return note_subs[difficulty][note.note]
    except KeyError:
        return note.note


class Block:
    image = "resource/sprites/crate.png"

    def __init__(self, time, note, size, pos, speed):
        self.time = time
        self.note = note
        note.block = self
        self.quad = None
        self.letter = None
        self.start_pos = pos
        self.speed = speed
        self.size = size
        self.pos = self.start_pos
        self.open = False
        self.closed = False
        self.done = False
        self.hit = False
        self.wall = None

    def update(self, music_pos):
        if self.done:
            return self.done

        if self.quad is None:
            # The first time we're called we can grab a qua
            self.quad = drawing.Quad(
                globals.quad_buffer,
                tc=globals.current_view.atlas.texture_coords(self.image),
            )
            letter = letter_from_note(self.note, globals.current_view.difficulty)
            self.key = ord(letter)
            try:
                letter = print_trans[letter]
            except KeyError:
                pass
            self.letter = globals.text_manager.letter(letter, drawing.texture.TextTypes.SCREEN_RELATIVE)

        elapsed = music_pos - self.time
        moved = elapsed * self.speed
        self.pos = self.start_pos - Point(moved, 0)
        tr = self.pos + self.size

        self.quad.set_vertices(self.pos, tr, 10)
        margin = self.size * 0.2
        self.letter.set_vertices(self.pos + margin, tr - margin, 11)

        self.done = tr.x <= 0
        return self.done

    def mark_hit(self):
        self.hit = True

    def delete(self):
        self.done = True
        if self.quad:
            self.quad.delete()
            self.quad = None
        if self.letter:
            self.letter.delete()
            self.letter = None


class Monster(Block):
    image = "resource/sprites/iron_devil.png"

    def __init__(self, time, note, size, pos, speed):
        self.time = time
        self.note = note
        self.quad = None
        self.letter = None
        self.start_pos = pos
        self.speed = speed
        self.size = size
        self.pos = self.start_pos
        self.open = False
        self.done = False
        self.hit = False

    def update(self, music_pos):
        if self.done:
            return self.done

        if self.quad is None:
            # The first time we're called we can grab a qua
            self.quad = drawing.Quad(
                globals.quad_buffer,
                tc=globals.current_view.atlas.texture_coords(self.image),
            )

        elapsed = music_pos - self.time
        moved = elapsed * self.speed
        self.pos = self.start_pos - Point(moved, 0)
        tr = self.pos + self.size

        self.quad.set_vertices(self.pos, tr, 10)

        self.done = tr.x <= 0
        return self.done

    def delete(self):
        self.done = True
        if self.quad:
            self.quad.delete()
            self.quad = None


class Wall(Monster):
    image = "resource/sprites/low_wall.png"


class BigMonster(Monster):
    image = "resource/sprites/big_monster.png"


class DestructableWall:
    image = "resource/sprites/low_wall.png"

    def __init__(self, time, note, size, pos, speed, block):
        self.top_size = Point(size.x, size.y * 5 / 6)
        self.bottom_size = Point(size.x, size.y / 6)
        self.time = time
        self.note = note
        self.bottom_quad = None
        self.top_quad = None
        self.letter = None
        self.start_pos = pos
        self.speed = speed
        self.size = size
        self.pos = self.start_pos
        self.open = False
        self.done = False
        self.hit = False
        self.block = block
        block.wall = self

    def update(self, music_pos):
        if self.done:
            return self.done

        if self.top_quad is None:
            # The first time we're called we can grab a qua
            tc = [[0, 0], [0, 5 / 6], [1, 5 / 6], [1, 0]]
            globals.current_view.atlas.transform_coords(self.image, tc)
            self.top_quad = drawing.Quad(globals.quad_buffer, tc=tc)
            tc = [[0, 0], [0, 1 / 6], [1, 1 / 6], [1, 0]]
            globals.current_view.atlas.transform_coords(self.image, tc)
            self.bottom_quad = drawing.Quad(globals.quad_buffer, tc=tc)

        elapsed = music_pos - self.time
        moved = elapsed * self.speed
        self.pos = self.start_pos - Point(moved, 0)
        tr = self.pos + self.size

        z = 10
        for quad, size, offset in (
            (self.bottom_quad, self.bottom_size, Point(0, 0)),
            (self.top_quad, self.top_size, Point(0, 64)),
        ):
            if quad:
                quad.set_vertices(self.pos + offset, self.pos + size + offset, z)
            z -= 1

        self.done = tr.x <= 0
        return self.done

    def delete(self):
        self.done = True
        if self.top_quad:
            self.top_quad.delete()
            self.top_quad = None
        if self.bottom_quad:
            self.bottom_quad.delete()
            self.bottom_quad = None

    def smash(self):
        self.bottom_quad.delete()
        self.bottom_quad = None


class Track:
    speed = 0.5  # widths per second. I.e 0.5 = take 2 seconds to transit the whole the tack
    window_before = 150
    window_after = 250

    def __init__(self, parent, pos, height, notes, atlas):
        self.parent = parent
        self.region = ui.Border(
            parent, Point(0, pos), Point(1, pos + height), colour=(1, 1, 1, 0.7), line_width=1
        )
        # Absolute speed is pixels per ms
        self.absolute_speed = (self.speed * self.region.absolute.size[0]) / 1000
        self.absolute_line_pos = parent.get_absolute(Point(parent.line_pos, 0)).x

        print(f"{self.absolute_speed=} {self.absolute_line_pos=}"),

        self.notes = list(notes)

        self.starts = []

        block_size = self.region.absolute.size[1] * 0.6
        transit_pixels = self.region.absolute.size[0] - self.absolute_line_pos + (block_size / 2)
        self.transit_ms = transit_pixels / self.absolute_speed

        print(f"{self.transit_ms=}", self.notes)

        for note in self.notes:
            # The time this wants introducing is the time that it should cross the line minus the amount of
            # time that it will take to go from the top to the line pos
            time = note.time - self.transit_ms + parent.previous_runs + parent.gaps
            self.starts.append(
                Block(
                    time,
                    note,
                    size=Point(block_size, block_size),
                    pos=self.region.absolute.top_right
                    - Point(0, block_size + (self.region.absolute.size[1] - block_size) / 2),
                    speed=self.absolute_speed,
                )
            )

        self.current_starts = self.starts[::]
        self.in_flight = []

        self.open_by_key = {}

    def delete(self):
        for block in self.starts:
            block.delete()

    def get_blocks(self, pos):
        for i, note in enumerate(self.current_starts):
            if note.time <= pos:
                yield note
            else:
                self.current_starts = self.current_starts[i:]
                return

        self.current_starts = []

    def update(self, t, music_pos):
        # Do we need to start drawing any new blocks?
        for new_block in self.get_blocks(music_pos):
            self.in_flight.append(new_block)

        # Update the position of any existing blocks
        finished_blocks = []
        new_in_flight = []

        for block in self.in_flight:
            done = block.update(music_pos)
            if done:
                finished_blocks.append(block)
                block.delete()
            else:
                new_in_flight.append(block)
                # They become open window milliseconds before their target time
                block_time = block.note.time + self.parent.previous_runs + self.parent.gaps
                if (
                    not block.open
                    and not block.closed
                    and globals.music_pos >= block_time - self.window_before
                ):
                    try:
                        self.open_by_key[block.key].append(block)
                    except KeyError:
                        self.open_by_key[block.key] = [block]
                    block.open = True

                elif block.open and globals.music_pos >= block_time + self.window_after:
                    # You missed your chance to get this one buddy!
                    if not block.hit:
                        self.parent.miss(block)
                    block.open = False
                    block.closed = True
                    try:
                        a = self.open_by_key[block.key]
                        a = [b for b in a if b is not block]
                        if not a:
                            del self.open_by_key[block.key]
                        else:
                            self.open_by_key[block.key] = a
                    except KeyError:
                        pass

        self.in_flight = new_in_flight

    def key_down(self, key):
        try:
            hit_blocks = self.open_by_key[key]
        except KeyError:
            return False

        for hit_block in hit_blocks:
            # Only permit this if it's within the right amount of time
            hit_time = (
                globals.music_pos - self.parent.music_offset - self.parent.previous_runs
            ) - hit_block.note.time
            print(f"{hit_time=}")
            window = self.window_before if hit_time < 0 else self.window_after
            if abs(hit_time) < window:
                self.parent.hit(hit_block)
                hit_block.mark_hit()
                hit_block.delete()
                hit_block.closed = True
                hit_block.open = False
                a = self.open_by_key[hit_block.key]
                a.pop(0)
                if not a:
                    del self.open_by_key[hit_block.key]
                else:
                    self.open_by_key[hit_block.key] = a
                return True
                # del self.open_by_key[key]

        # if we get here it means the key didn't delete any blocks. That's a paddlin'
        return False


class MonsterTrack(Track):
    # The monster track puts monsters in the players path that can be jumped with the 'a' key
    def __init__(self, parent, pos, height, notes, atlas):
        super().__init__(parent, pos, height, notes, atlas)
        self.monster_starts = []
        monster_size = 64
        # We also want to manage the devil positions
        for note in self.notes:
            # The time this wants introducing is the time that it should cross the line minus the amount of
            # time that it will take to go from the top to the line pos
            time = note.time - self.transit_ms + parent.previous_runs + parent.gaps
            if note.note in ["a", "q"]:
                self.monster_starts.append(
                    Monster(
                        time,
                        note,
                        size=Point(monster_size, monster_size),
                        pos=parent.absolute.bottom_right + Point(300, 214),
                        speed=self.absolute_speed,
                    )
                )
            elif note.note in ["t"]:
                self.monster_starts.append(
                    BigMonster(
                        time,
                        note,
                        size=Point(121, 131),
                        pos=parent.absolute.bottom_right + Point(300, 214),
                        speed=self.absolute_speed,
                    )
                )

            elif note.note in ["d", "e"]:
                # For these we'll put a wall that needs to be ducked under
                self.monster_starts.append(
                    Wall(
                        time,
                        note,
                        size=Point(64, 384),
                        pos=parent.absolute.bottom_right + Point(300, 214 + 48),
                        speed=self.absolute_speed,
                    )
                )
            elif note.note == "space":
                self.monster_starts.append(
                    DestructableWall(
                        time,
                        note,
                        size=Point(64, 384) * 1.15,
                        pos=parent.absolute.bottom_right + Point(300, 214),
                        speed=self.absolute_speed,
                        block=note.block,
                    )
                )

        self.current_monster_starts = self.monster_starts[::]
        self.monsters_in_flight = []

    # This code duplication is nasty, but I'm in a rush
    def get_monsters(self, pos):
        for i, note in enumerate(self.current_monster_starts):
            if note.time <= pos:
                yield note
            else:
                self.current_monster_starts = self.current_monster_starts[i:]
                return

        self.current_monster_starts = []

    def update(self, t, music_pos):
        super().update(t, music_pos)

        # Do we need to start drawing any new monsters?
        for new_monster in self.get_monsters(music_pos):
            self.monsters_in_flight.append(new_monster)

        # Update the position of any existing blocks
        finished_monsters = []
        new_monsters_in_flight = []

        for monster in self.monsters_in_flight:
            done = monster.update(music_pos)
            if done:
                finished_monsters.append(monster)
                monster.delete()
            else:
                new_monsters_in_flight.append(monster)

        self.monsters_in_flight = new_monsters_in_flight

    def delete(self):
        super().delete()
        for monster in self.monster_starts:
            monster.delete()


class KingTrack(Track):
    # The king track will manage the position of the floating ghost that can be hit with magic missiles
    image = "resource/sprites/ghost.png"

    def __init__(self, parent, pos, height, notes, atlas):
        super().__init__(parent, pos, height, notes, atlas)
        self.size = Point(150, 240)
        self.quad = drawing.Quad(
            globals.quad_buffer,
            tc=atlas.texture_coords(self.image),
        )
        self.bl = Point(0, 250)
        self.tr = self.bl + self.size
        self.quad.set_vertices(self.bl, self.tr, 10)

    def update(self, t, music_pos):
        super().update(t, music_pos)

        # We want to oscillate our position
        x = 32 * math.sin(16 + (music_pos * 1.2 / 1000))
        y = 32 * math.sin((music_pos * 0.8 / 1000))

        self.current_pos = self.bl + Point(x, y)

        self.quad.set_vertices(self.current_pos, self.tr + Point(x, y), 10)

    def delete(self):
        super().delete()
        self.quad.delete()

    def get_centre(self):
        return self.current_pos + (self.size / 2)


class HealthBar(ui.UIElement):
    def __init__(self, parent, bl, tr, health):
        self.max_health = health
        self.health = health
        super().__init__(parent, bl, tr)

        self.border = ui.Border(self, Point(0, 0.5), Point(1, 1), colour=(1, 0, 0, 1))
        self.filled_quad = drawing.Quad(globals.ui_buffer)
        self.title = ui.TextBox(
            self,
            Point(0, 0),
            Point(1, 0.5),
            "Health",
            2,
            drawing.constants.colours.red,
            alignment=drawing.texture.TextAlignments.CENTRE,
        )

        self.set_health()

    def set_health(self):
        bl = self.border.absolute.bottom_left
        partial = self.health / self.max_health
        size = self.border.absolute.size * Point(partial, 1)
        self.filled_quad.set_vertices(bl, bl + size, drawing.constants.DrawLevels.ui)
        self.filled_quad.set_colour((1, 0, 0, 1))

    def reset(self):
        self.health = self.max_health
        self.set_health()

    def add(self, amount):
        if amount < 0:
            drawing.shake_screen(20, 500)
        self.health += amount
        if self.health > self.max_health:
            self.health = self.max_health
        if self.health < 0:
            self.health = 0

        self.set_health()


def format_time(t):
    seconds = globals.music_pos // 1000
    ms = globals.music_pos % 1000
    return f"{seconds:4d}.{ms:03d}"


class GameView(ui.UIRoot):
    text_fade_duration = 1000
    music_offset = 0
    line_pos = 0.3
    gap = 1000

    def __init__(self):
        super(GameView, self).__init__(Point(0, 0), globals.screen)

        self.atlas = drawing.texture.TextureAtlas("atlas_0.png", "atlas.txt", extra_names=None)
        self.wall_buffer = drawing.QuadBuffer(128)
        self.wall_atlas = drawing.texture.TextureAtlas("wall_atlas_0.png", "wall_atlas.txt", extra_names=None)
        self.paused = False
        self.music_start = None
        self.main_menu = MainMenu(self, Point(0.1, 0.15), Point(0.9, 0.85))
        self.difficulty = self.main_menu.get_difficulty()
        pygame.mixer.music.load(
            os.path.join(globals.dirs.music, "Musopen_-_In_the_Hall_Of_The_Mountain_King.ogg")
        )
        # Parse the note list
        self.notes = NoteTiming(os.path.join(globals.dirs.music, "timing.txt"))
        # We want a line across the screen to mark the point that the keys should be hit
        self.line = Line(
            self, self.get_absolute(Point(self.line_pos, 0)), self.get_absolute(Point(self.line_pos, 1))
        )

        self.health_bar = HealthBar(self, Point(0.05, 0.02), Point(0.2, 0.08), 100)
        self.timer = ui.TextBox(
            self,
            Point(0.85, 0.1),
            Point(1, 0.2),
            format_time(0),
            2,
            colour=drawing.constants.colours.white,
            alignment=drawing.texture.TextAlignments.LEFT,
        )

        aspect = globals.screen_root.absolute.size.x / globals.screen_root.absolute.size.y
        tile = 1
        tc = [[0, 0], [0, tile], [tile * aspect, tile], [tile * aspect, 0]]
        self.wall_atlas.transform_coords("resource/background/wall.png", tc)

        self.dungeon = ui.ImageBox(
            self,
            Point(0, 0.1),
            Point(1, 0.9),
            tc=tc,
            buffer=self.wall_buffer,
            level=4,
        )

        self.player = Sprite(
            self,
            self.get_absolute(Point(0.45, 0.30)),
            self.get_absolute(Point(0.55, 0.40)),
            [f"resource/sprites/k{n}.png" for n in range(1, 9)],
            self.atlas,
        )

        self.paused = True
        self.tracks = []
        self.previous_runs = 0
        self.gaps = 0
        self.gapping = 0
        self.setup_tracks()
        self.disable()
        self.damage = [1, 2, 4, 8]
        self.miss_streak = 0
        self.fade_text = ui.FaderTextBox(
            self,
            Point(0, 0),
            Point(1, 0.9),
            scale=4,
            text="A monkey",
            colour=(1, 1, 1, 1),
            alignment=drawing.texture.TextAlignments.CENTRE,
        )
        self.fade_text.disable()
        self.fading_text = False

    def setup_tracks(self):
        for track in self.tracks:
            track.delete()
            self.tracks = []
        track_width = 0.1
        self.left_track = MonsterTrack(
            self, 0, track_width, self.notes.get_all_notes({"horn"}, self.difficulty), self.atlas
        )

        self.right_track = KingTrack(
            self,
            1.0 - track_width,
            track_width,
            self.notes.get_all_notes({"strings"}, self.difficulty),
            self.atlas,
        )

        self.tracks = [self.left_track, self.right_track]

    def quit(self, pos):
        raise SystemExit()

    def miss(self, block):
        print("Missed one!")
        try:
            damage = self.damage[self.miss_streak]
        except IndexError:
            damage = self.damage[-1]

        self.health_bar.add(-damage)
        self.miss_streak += 1
        if self.health_bar.health <= 0:
            # Bring the menu back up, but remove the resume button
            self.main_menu.start_button.set_text("Play")
            self.main_menu.enable()
            self.main_menu.resume_button.disable()
            self.main_menu.info.set_text(f"You lasted {format_time(globals.music_pos)}. Try again!")
            self.disable()
            self.paused = True
            pygame.mixer.music.pause()

    def hit(self, block):
        print("Got one!")
        if block:
            if block.key in [ord("a"), ord("q")]:
                self.player.jump()
            elif block.key == ord("t"):
                self.player.jump(high=True)
            elif block.key in [ord("d"), ord("e")]:
                self.player.duck()
            elif block.key in range(ord("0"), ord("9")):
                self.player.shoot(block.key - ord("0"))
            elif block.key == ord(" "):
                self.player.smash(block.wall)

        self.miss_streak = 0

    def key_down(self, key):
        if key == pygame.locals.K_ESCAPE:
            if self.main_menu.enabled:
                if self.music_start is not None:
                    return self.resume(None)
                else:
                    return None
            self.main_menu.start_button.set_text("Restart")
            self.main_menu.enable()
            self.disable()
            self.paused = True
            pygame.mixer.music.pause()
            return

        for track in self.tracks:
            if track.key_down(key):
                break
        else:
            self.miss(None)

    def key_up(self, key):
        pass

    def start(self, pos):
        self.main_menu.disable()
        self.enable()
        self.paused = False

        self.music_start = None
        self.health_bar.reset()
        self.miss_streak = 0
        pygame.mixer.music.stop()
        self.difficulty = self.main_menu.get_difficulty()
        self.setup_tracks()
        self.previous_runs = 0
        self.fade_text.disable()

    def resume(self, pos):
        self.main_menu.disable()
        self.enable()
        pygame.mixer.music.unpause()
        self.paused = False

    def enable(self):
        self.health_bar.enable()

    def disable(self):
        self.health_bar.disable()

    def update(self, t):
        global music_start

        if self.paused:
            return

        if self.fading_text:
            self.fading_text = not self.fade_text.update(t)

        if self.music_start is None:
            pygame.mixer.music.play(start=music_start / 1000)
            self.music_start = t

        self.timer.set_text(format_time(globals.music_pos))

        if self.gapping:
            core_music_pos = t - self.gapping + self.gap

            if t >= self.gapping:
                pygame.mixer.music.play(start=music_start / 1000)
                self.music_start = t
                self.gapping = 0
                self.gaps = 0
                self.previous_runs += self.gap

        if not self.gapping:
            core_music_pos = pygame.mixer.music.get_pos()
            if core_music_pos < 0:
                # It looped
                self.previous_runs += globals.music_pos - self.previous_runs
                self.gaps += self.gap
                self.difficulty += 1
                if self.difficulty >= 3:
                    self.game_over = GameOver(self, Point(0.2, 0.2), Point(0.8, 0.8))
                    self.paused = True
                    return
                self.main_menu.set_difficulty(self.difficulty)
                self.gapping = globals.t + self.gap
                self.setup_tracks()
                music_start = 0
                core_music_pos = 0
                difficulty_text = self.main_menu.get_difficulty_text()
                self.fade_text.set_text(f"{difficulty_text} Difficulty!")
                self.fade_text.SetFade(
                    globals.t + 1000, globals.t + 3000, end_size=4, end_colour=(1, 0, 0, 0)
                )
                self.fade_text.enable()
                self.fading_text = True

        music_pos = globals.music_pos = (
            self.previous_runs + core_music_pos + self.music_offset + music_start
        )  # t - self.music_start
        # print(f"{core_music_pos=} {music_pos=}")

        # new_notes = list(self.notes.get_notes(music_pos))
        # if new_notes:
        #     output = [f"{music_pos:6} "]
        #     for note in new_notes:
        #         output.append(f"{note.instrument:10}({note.note})")

        #     print(" ".join(output))

        #     # These notes go into the "can-be-pressed list"

        for track in self.tracks:
            track.update(t, music_pos)

        self.player.update(music_pos)

        speed = self.left_track.speed
        tc_max = self.dungeon.start_tc[2][0]
        extra = ((speed * music_pos * tc_max) / 1000) % (1.0)
        for i in range(4):
            new = self.dungeon.start_tc[i][0] + extra
            self.dungeon.quad.tc[i][0] = new

    def draw(self):
        drawing.draw_no_texture(globals.ui_buffer)
        drawing.draw_all(self.wall_buffer, self.wall_atlas.texture)
        drawing.draw_all(globals.quad_buffer, self.atlas.texture)
        drawing.line_width(3)
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
