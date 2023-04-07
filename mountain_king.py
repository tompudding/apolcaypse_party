import pygame
import ui
import globals
import drawing
from globals.types import Point
import game
import sys


def init():
    """Initialise everything. Run once on startup"""
    if hasattr(sys, "_MEIPASS"):
        os.chdir(sys._MEIPASS)
    w, h = (1280, 720)

    globals.dirs = globals.types.Directories("resource")

    globals.screen = Point(w, h)
    globals.screen_root = ui.UIRoot(Point(0, 0), globals.screen)
    globals.ui_state = ui.UIState()

    globals.quad_buffer = drawing.QuadBuffer(131072)
    globals.nonstatic_text_buffer = drawing.QuadBuffer(131072)
    globals.screen_quadbuffer = drawing.QuadBuffer(16)

    globals.screen.full_quad = drawing.Quad(globals.screen_quadbuffer)
    globals.screen.full_quad.set_vertices(Point(0, 0), globals.screen, 0.01)
    globals.ui_buffer = drawing.QuadBuffer(131072)
    globals.screen_relative = drawing.QuadBuffer(131072, ui=True)
    globals.line_buffer = drawing.LineBuffer(131072)
    # globals.sounds = sounds.Sounds()
    globals.music_pos = 0

    globals.mouse_relative_text = drawing.QuadBuffer(1024, ui=True, mouse_relative=True)

    globals.mouse_screen = Point(0, 0)
    globals.tiles = None

    pygame.mixer.init(frequency=48000, allowedchanges=0)
    # pygame.init()
    screen = pygame.display.set_mode((w, h), pygame.OPENGL | pygame.DOUBLEBUF)
    pygame.display.set_caption("To the Beat of the Mountain King")
    # pygame.mouse.set_visible(False)
    drawing.init(*globals.screen)
    # globals.cursor = drawing.cursors.Cursor()

    globals.text_manager = drawing.texture.TextManager()


def main_run():

    done = False
    last = 0
    clock = pygame.time.Clock()
    last_handled = False

    while not done:

        clock.tick(120)
        t = pygame.time.get_ticks()
        fps = clock.get_fps()
        if t - last > 1000:
            print("FPS:", fps)
            last = t

        globals.t = t
        if fps == 0:
            fps = 50

        drawing.new_frame()
        globals.current_view.update(t)
        globals.current_view.draw()
        globals.screen_root.draw()
        globals.text_manager.draw()
        drawing.draw_no_texture(globals.ui_buffer)
        # globals.cursor.draw()

        drawing.end_frame()

        # drawing.draw_ui()

        pygame.display.flip()

        eventlist = pygame.event.get()
        for event in eventlist:
            if event.type == pygame.locals.QUIT:
                done = True
                break

            elif event.type == pygame.KEYDOWN:
                try:
                    key = ord(event.unicode)
                except (AttributeError, TypeError):
                    key = event.key

                globals.current_view.key_down(key)
            elif event.type == pygame.KEYUP:
                try:
                    key = ord(event.unicode)
                except AttributeError:
                    key = event.key
                except TypeError:
                    continue
                globals.current_view.key_up(key)
            else:
                try:
                    pos = Point(event.pos[0], globals.screen[1] - event.pos[1])
                except AttributeError:
                    continue
                if event.type == pygame.MOUSEMOTION:
                    rel = Point(event.rel[0], -event.rel[1])
                    globals.mouse_screen = pos
                    if globals.dragging:
                        globals.dragging.mouse_motion(pos, rel, False)
                    else:
                        handled = globals.screen_root.mouse_motion(pos, rel, False)
                        # Only cancel the mouse motion if wasn't cancelled already
                        if handled and not last_handled:
                            globals.current_view.cancel_mouse_motion()
                        last_handled = handled
                        globals.current_view.mouse_motion(pos, rel, True if handled else False)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    for layer in globals.screen_root, globals.current_view:
                        handled, dragging = layer.mouse_button_down(pos, event.button)
                        if handled and dragging:
                            globals.dragging = dragging
                            break
                        if handled:
                            break

                elif event.type == pygame.MOUSEBUTTONUP:
                    for layer in globals.screen_root, globals.current_view:
                        handled, dragging = layer.mouse_button_up(pos, event.button)
                        if handled and not dragging:
                            globals.dragging = None
                        if handled:
                            break


def main():
    """Main loop for the game"""
    init()

    globals.dragging = None

    drawing.init_drawing()

    globals.current_view = game.GameView()

    main_run()


if __name__ == "__main__":
    import logging

    try:
        logging.basicConfig(level=logging.DEBUG, filename="errorlog.log")
        # logging.basicConfig(level=logging.DEBUG)
    except IOError:
        # pants, can't write to the current directory, try using a tempfile
        pass

    try:
        main()
    except Exception as e:
        print("Caught exception, writing to error log...")
        logging.exception("Oops:")
        # Print it to the console too...
        raise
