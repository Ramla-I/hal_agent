#!/usr/bin/env python3
"""A minimal PDF 1.4 writer -- enough of the format to draw a bar chart.

Shared by the figure scripts in this directory. Written against the spec
rather than through a plotting library on purpose: matplotlib is pinned in
requirements.txt and still is not present in every environment these figures
have to regenerate in, and a figure that only rebuilds where someone
remembered to install a plotting stack goes stale between drafts. This needs
the standard library and nothing else.

The output is real vector art: marks are rectangles and Bezier caps, and text
is Base-14 Helvetica/Courier, which every PDF viewer and LaTeX toolchain
already has -- so no font is embedded and none can go missing when a .tex
reaches a co-author.

Courier is metrically exact at 0.6 em per glyph, which is why rotated axis
labels use it: right-aligning a rotated label needs a real advance width, and
guessing a proportional font's is how labels drift off an axis.
"""

import math

_PT = 72.0
_COURIER_ADV = 0.6
_HELV_ADV = 0.52


def _esc(s: str) -> str:
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


class Pdf:
    """Enough of PDF 1.4 to draw a bar chart."""

    def __init__(self, w: float, h: float):
        self.w, self.h, self.ops = w, h, []

    def _rgb(self, hexstr):
        v = hexstr.lstrip("#")
        return tuple(int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def fill(self, c):
        self.ops.append("%.4f %.4f %.4f rg" % self._rgb(c))

    def stroke(self, c):
        self.ops.append("%.4f %.4f %.4f RG" % self._rgb(c))

    def rect(self, x, y, w, h, sw=0.0):
        self.ops.append("%.2f %.2f %.2f %.2f re" % (x, y, w, h))
        self.ops.append("%.2f w B" % sw if sw else "f")

    def cap_rect(self, x, y, w, h, r, sw=0.0):
        """Rectangle with only the TOP corners rounded -- the data end."""
        r = min(r, w / 2, h)
        k = r * 0.5523
        self.ops.append(
            "%.2f %.2f m %.2f %.2f l " % (x, y, x, y + h - r)
            + "%.2f %.2f %.2f %.2f %.2f %.2f c " % (x, y + h - r + k,
                                                    x + r - k, y + h, x + r, y + h)
            + "%.2f %.2f l " % (x + w - r, y + h)
            + "%.2f %.2f %.2f %.2f %.2f %.2f c " % (x + w - r + k, y + h,
                                                    x + w, y + h - r + k,
                                                    x + w, y + h - r)
            + "%.2f %.2f l h" % (x + w, y))
        self.ops.append("%.2f w B" % sw if sw else "f")

    def hatch(self, x, y, w, h, angles, gap=1.9, lw=0.42, color="#ffffff"):
        """Texture inside a segment: a clip plus strokes.

        Tiling-pattern objects would work too, but the geometry here is known
        and a clip with a few lines is something a reader can check.
        """
        if not angles or h <= 0.4:
            return
        self.ops.append("q %.2f %.2f %.2f %.2f re W n" % (x, y, w, h))
        self.stroke(color)
        span = w + h
        for a in angles:
            rad = math.radians(a)
            dx, dy = math.cos(rad), math.sin(rad)
            steps = int(span / gap) + 2
            for i in range(-steps, steps + 1):
                ox, oy = x - dy * i * gap, y + dx * i * gap
                self.ops.append("%.2f w %.2f %.2f m %.2f %.2f l S"
                                % (lw, ox - dx * span, oy - dy * span,
                                   ox + dx * span, oy + dy * span))
        self.ops.append("Q")

    def line(self, x1, y1, x2, y2, w=0.4):
        self.ops.append("%.2f w %.2f %.2f m %.2f %.2f l S" % (w, x1, y1, x2, y2))

    def text(self, x, y, s, size=7.0, font="F1", anchor="start"):
        adv = (_COURIER_ADV if font == "F2" else _HELV_ADV) * size
        if anchor == "middle":
            x -= adv * len(s) / 2
        elif anchor == "end":
            x -= adv * len(s)
        self.ops.append("BT /%s %.2f Tf %.2f %.2f Td (%s) Tj ET"
                        % (font, size, x, y, _esc(s)))

    def rot_text(self, x, y, s, size=6.0, deg=-60.0, font="F2"):
        a = math.radians(deg)
        ca, sa = math.cos(a), math.sin(a)
        wdt = _COURIER_ADV * size * len(s)
        self.ops.append("BT /%s %.2f Tf %.4f %.4f %.4f %.4f %.2f %.2f Tm "
                        "(%s) Tj ET" % (font, size, ca, sa, -sa, ca,
                                        x - wdt * ca, y - wdt * sa, _esc(s)))

    def to_bytes(self) -> bytes:
        content = "\n".join(self.ops).encode("latin-1", "replace")
        objs = [
            b"<</Type/Catalog/Pages 2 0 R>>",
            b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
            ("<</Type/Page/Parent 2 0 R/MediaBox[0 0 %.2f %.2f]"
             "/Resources<</Font<</F1 5 0 R/F2 6 0 R>>>>/Contents 4 0 R>>"
             % (self.w, self.h)).encode(),
            b"<</Length " + str(len(content)).encode() + b">>\nstream\n"
            + content + b"\nendstream",
            b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
            b"<</Type/Font/Subtype/Type1/BaseFont/Courier>>",
        ]
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offs = []
        for i, body in enumerate(objs, start=1):
            offs.append(len(out))
            out += str(i).encode() + b" 0 obj\n" + body + b"\nendobj\n"
        xref = len(out)
        n = len(objs) + 1
        out += b"xref\n0 " + str(n).encode() + b"\n0000000000 65535 f \n"
        for o in offs:
            out += ("%010d 00000 n \n" % o).encode()
        out += (b"trailer\n<</Size " + str(n).encode() + b"/Root 1 0 R>>\n"
                b"startxref\n" + str(xref).encode() + b"\n%%EOF\n")
        return bytes(out)
