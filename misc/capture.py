#!/usr/bin/python

import time
import sys
from math import cos, radians

from colour import Color
from gtk import gdk
from PIL import Image
from PIL.ImageStat import Stat
from send import LEDs, discover_leds


class Capturer(object):
    "A class that will take a screenshot of a single pixel on a GTK system."
    def __init__(self, w=None, h=None):
        self._w = w if w else gdk.screen_width()
        self._h = h if h else gdk.screen_height()

        self._window = gdk.get_default_root_window()
        self._pb = gdk.Pixbuf(gdk.COLORSPACE_RGB, False, 8, self._w, self._h)

    def _screenshot(self, x, y):
        pb = self._pb.get_from_drawable(
                self._window,
                self._window.get_colormap(),
                x, y,
                0, 0,
                self._w, self._h)
        image = Image.frombuffer(
                'RGB',
                (self._w, self._h),
                pb.get_pixels(),
                'raw',
                'RGB',
                pb.get_rowstride(),
                1)
        return image

    def capture(self, x, y):
        """Capture a pixel from the screen."""
        color = Color(rgb=[c / 255.0 for c in self._screenshot(x, y).getpixel((0, 0))])
        return color


class Tween(object):
    def __init__(self, color, tween, duration=1):
        self._start = time.time()
        self._color = color
        self._duration = float(duration)
        self._tween = self._get_tween_func(tween)

    def _get_tween_func(self, name):
        if name == "cosine":
            func = lambda r: Color(self._color, luminance=self._color.luminance * abs(cos(radians(180 * r))))
        elif name == "quick cosine":
            func = lambda r: Color(self._color, luminance=self._color.luminance * abs(cos(radians(2 * 180 * r))))
        elif name == "quick cosine with floor":
            func = lambda r: Color(self._color, luminance=self._color.luminance * (0.8 * abs(cos(radians(2 * 180 * r))) + 0.2))
        elif name == "cosine with floor":
            func = lambda r: Color(self._color, luminance=self._color.luminance * (0.8 * abs(cos(radians(180 * r))) + 0.2))
        elif name == "square":
            func = lambda r: self._color if r * 3 % 1 < 0.8 else Color("black")
        return func

    @property
    def is_done(self):
        "Return True when the tween is done."
        return time.time() > self._start + self._duration

    @property
    def color(self):
        # The time since the tween started.
        since = time.time() - self._start

        # The percentage of time we are along.
        rate = min(since / self._duration, 1)

        color = self._tween(rate)
        return color


class NaiveColorGenerator(object):
    "An averaging filter."
    def __init__(self):
        self._capturer = Capturer()

    def get_color(self):
        image = self._capturer._screenshot(0, 0)
        color = Color(rgb=[c / 255.0 for c in Stat(image).mean])
        return color


class SuperHexColorGenerator(object):
    CAPTURE = 1
    PULSING = 2
    IDLE = 3

    def __init__(self):
        self._capturer = Capturer(1, 1)
        self._state = self.CAPTURE
        self._tween = None

    def get_color(self):
        screen_color = self._capturer.capture(134, 59)
        second_col = self._capturer.capture(1706, 75)

        if self._state == self.CAPTURE and \
           screen_color == Color("white") == second_col:
            self._state = self.PULSING
            self._tween = Tween(Color("red"), tween="quick cosine", duration=2)

        if self._state in (self.IDLE, self.CAPTURE):
            if second_col == Color("#d7d7d7"):
                color = screen_color
                self._state = self.CAPTURE
            else:
                color = Color("black")
                self._state = self.IDLE
        else:
            color = self._tween.color
            if self._tween.is_done:
                self._state = self.CAPTURE

        return color


def main():
    print("Discovering gamelights controllers...")
    ips = discover_leds()
    print("Found %s controllers: %s." % (len(ips), ", ".join(ips)))
    if not ips:
        sys.exit(1)

    leds = LEDs(udp_ips=ips)
    fps = 30
    colorgen = SuperHexColorGenerator()
    last_color = None
    while True:
        color = colorgen.get_color()
        if last_color == color:
            continue
        else:
            last_color = color
            print color
            r, g, b = [int(x * 255) for x in color.get_rgb()]
            leds.send(r, g, b)
        time.sleep(1.0/fps)


if __name__ == "__main__":
    main()
