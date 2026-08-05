"""HUD and menu chrome.

Panels are 9-slice: the packer emits a fixed 24x24 sprite and the manifest
records the 8px inset, so Swift can stretch the middle without smearing the
corners.
"""

from __future__ import annotations

import math

from .canvas import Canvas
from .palette import (
    ARCANE, BLOOD, BONE, CLOTH_RED, COPPER, GOLD, METAL, PLASMA, RGBA, Ramp,
    SOLAR, STEEL, TOXIC, UI_DARK, UI_LIGHT, VOID, with_alpha,
)
from .shapes import bevel, gradient_disc, ring, rounded_rect, soft_glow, star

PANEL_SIZE = 24
PANEL_INSET = 8


def panel(accent: Ramp = GOLD, dark: bool = True) -> Canvas:
    """9-slice frame. Corners carry a rivet so stretched panels still look
    built rather than drawn."""
    c = Canvas(PANEL_SIZE, PANEL_SIZE)
    base = UI_DARK if dark else UI_LIGHT
    rounded_rect(c, 0, 0, PANEL_SIZE, PANEL_SIZE, with_alpha(base[1], 232),
                 radius=3)
    c.frame(0, 0, PANEL_SIZE, PANEL_SIZE, accent[1])
    c.frame(1, 1, PANEL_SIZE - 2, PANEL_SIZE - 2, accent[3])
    c.frame(2, 2, PANEL_SIZE - 4, PANEL_SIZE - 4, base[0])
    for cx, cy in ((3, 3), (PANEL_SIZE - 4, 3), (3, PANEL_SIZE - 4),
                   (PANEL_SIZE - 4, PANEL_SIZE - 4)):
        c.rect(cx - 1, cy - 1, 2, 2, accent[4])
        c.put(cx, cy, accent[1])
    return c


def button(accent: Ramp = STEEL, pressed: bool = False) -> Canvas:
    c = Canvas(PANEL_SIZE, PANEL_SIZE)
    rounded_rect(c, 0, 0, PANEL_SIZE, PANEL_SIZE, accent[1 if pressed else 2],
                 radius=3)
    bevel(c, 1, 1, PANEL_SIZE - 2, PANEL_SIZE - 2, accent,
          light_index=1 if pressed else 4, dark_index=4 if pressed else 1)
    c.frame(0, 0, PANEL_SIZE, PANEL_SIZE, UI_DARK[0])
    return c


def bar_frame(w: int = 64, h: int = 10, accent: Ramp = GOLD) -> Canvas:
    c = Canvas(w, h)
    rounded_rect(c, 0, 0, w, h, UI_DARK[1], radius=2)
    c.frame(0, 0, w, h, accent[1])
    c.hline(1, 1, w - 2, UI_DARK[0])
    return c


def bar_fill(w: int = 60, h: int = 6, ramp: Ramp = BLOOD) -> Canvas:
    """Drawn at full width; the renderer crops it to the current value."""
    c = Canvas(w, h)
    c.rect(0, 0, w, h, ramp[2])
    c.hline(0, 0, w, ramp[3])
    c.hline(0, 1, w, ramp[4])
    c.hline(0, h - 1, w, ramp[1])
    for x in range(0, w, 6):
        c.vline(x, 1, h - 2, with_alpha(ramp[4], 60))
    return c


def boss_bar_frame(w: int = 160, h: int = 14) -> Canvas:
    c = Canvas(w, h)
    rounded_rect(c, 0, 0, w, h, UI_DARK[0], radius=2)
    c.frame(0, 0, w, h, BLOOD[1])
    c.frame(1, 1, w - 2, h - 2, BLOOD[3])
    for x in (6, w - 7):
        c.rect(x - 2, 2, 4, h - 4, METAL[3])
        c.hline(x - 2, 2, 4, METAL[4])
    for k in range(4):
        c.vline(w // 5 * (k + 1), 3, h - 6, with_alpha(UI_DARK[4], 150))
    return c


def crosshair(count: int = 2) -> list[Canvas]:
    """Two frames so the reticle can pulse when a shot is ready."""
    frames = []
    for i in range(count):
        gap = 3 + i
        c = Canvas(16, 16)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for k in range(3):
                c.put(8 + dx * (gap + k), 8 + dy * (gap + k),
                      SOLAR[4] if k == 0 else SOLAR[3])
        c.put(8, 8, with_alpha(SOLAR[4], 200))
        ring(c, 8, 8, 6.5, 1.0, with_alpha(SOLAR[3], 90))
        frames.append(c)
    return frames


def heart_ui(state: str) -> Canvas:
    """``full``, ``half`` or ``empty`` — the HUD version, flatter and more
    saturated than the floor pickup so it reads at a glance."""
    c = Canvas(14, 13)
    ramp = CLOTH_RED if state != "empty" else UI_DARK
    c.disc(4.5, 5, 3.4, ramp[2])
    c.disc(9.5, 5, 3.4, ramp[2])
    c.polygon([(1, 5), (13, 5), (7, 12)], ramp[2])
    if state != "empty":
        c.disc(4, 4.5, 1.8, ramp[3])
        c.put(3, 3, ramp[4])
    if state == "half":
        for y in range(13):
            for x in range(7, 14):
                if c.get(x, y)[3]:
                    c.set(x, y, UI_DARK[2])
    c.outline((10, 8, 14, 240))
    return c


def armor_ui() -> Canvas:
    c = Canvas(13, 13)
    c.polygon([(6, 0), (12, 3), (12, 7), (6, 12), (0, 7), (0, 3)], STEEL[3])
    c.polygon([(6, 2), (10, 4), (10, 7), (6, 10), (2, 7), (2, 4)], STEEL[4])
    c.outline((10, 8, 14, 240))
    return c


def ammo_icon() -> Canvas:
    c = Canvas(8, 12)
    c.rect(2, 3, 4, 8, COPPER[3])
    c.vline(3, 4, 6, COPPER[4])
    c.polygon([(4, 0), (6, 3), (2, 3)], GOLD[3])
    c.hline(2, 10, 4, COPPER[1])
    c.outline((10, 8, 14, 240))
    return c


def blank_icon() -> Canvas:
    c = Canvas(12, 12)
    c.disc(6, 6, 5.0, STEEL[3])
    ring(c, 6, 6, 3.0, 1.0, (240, 246, 255, 255))
    star(c, 6, 6, 2.2, 0.9, 6, (240, 246, 255, 255))
    c.outline((10, 8, 14, 240))
    return c


def key_icon() -> Canvas:
    c = Canvas(12, 10)
    ring(c, 3, 5, 2.4, 1.4, GOLD[3])
    c.rect(5, 4, 7, 2, GOLD[3])
    c.rect(9, 6, 2, 2, GOLD[3])
    c.outline((10, 8, 14, 240))
    return c


def coin_icon() -> Canvas:
    c = Canvas(10, 10)
    c.ellipse(5, 5, 3.4, 4.2, GOLD[2])
    c.ellipse(5, 5, 2.4, 3.2, GOLD[3])
    c.put(4, 3, GOLD[4])
    c.outline((10, 8, 14, 240))
    return c


def slot(active: bool = False) -> Canvas:
    """Weapon / item slot background."""
    c = Canvas(22, 22)
    rounded_rect(c, 0, 0, 22, 22, with_alpha(UI_DARK[2], 225), radius=3)
    accent = SOLAR if active else UI_LIGHT
    c.frame(0, 0, 22, 22, accent[1])
    c.frame(1, 1, 20, 20, accent[3] if active else UI_DARK[3])
    if active:
        soft_glow(c, 11, 11, 13, with_alpha(SOLAR[4], 45))
    return c


def minimap_room(kind: str) -> Canvas:
    """One cell of the minimap. Kinds mirror the room types in the generator."""
    c = Canvas(11, 9)
    fill = {
        "normal": UI_LIGHT[0],
        "current": UI_LIGHT[3],
        "cleared": UI_LIGHT[1],
        "unknown": UI_DARK[3],
        "shop": GOLD[2],
        "treasure": SOLAR[2],
        "boss": BLOOD[2],
        "start": PLASMA[2],
    }.get(kind, UI_LIGHT[0])
    rounded_rect(c, 0, 0, 11, 9, fill, radius=1)
    c.frame(0, 0, 11, 9, UI_DARK[0])
    c.hline(1, 1, 9, with_alpha((255, 255, 255, 255), 40))
    if kind == "boss":
        star(c, 5, 4, 3.0, 1.2, 5, BLOOD[4])
    elif kind == "shop":
        c.rect(4, 2, 3, 5, GOLD[4])
        c.hline(3, 3, 5, GOLD[4])
    elif kind == "treasure":
        c.rect(3, 3, 5, 3, SOLAR[4])
        c.hline(3, 3, 5, SOLAR[4])
    elif kind == "current":
        c.rect(4, 3, 3, 3, SOLAR[4])
    return c


def minimap_link(vertical: bool = False) -> Canvas:
    c = Canvas(5, 5) if not vertical else Canvas(5, 5)
    if vertical:
        c.rect(2, 0, 1, 5, UI_LIGHT[1])
    else:
        c.rect(0, 2, 5, 1, UI_LIGHT[1])
    return c


def damage_flash() -> Canvas:
    """Full-screen vignette tinted red; the renderer stretches it."""
    c = Canvas(32, 32)
    for y in range(32):
        for x in range(32):
            d = max(abs(x - 15.5), abs(y - 15.5)) / 15.5
            a = int(190 * max(0.0, d - 0.45) / 0.55)
            if a > 3:
                c.set(x, y, (190, 30, 40, a))
    return c


def vignette() -> Canvas:
    c = Canvas(32, 32)
    for y in range(32):
        for x in range(32):
            d = math.hypot(x - 15.5, y - 15.5) / 22.0
            a = int(150 * max(0.0, d - 0.5) / 0.5)
            if a > 3:
                c.set(x, y, (6, 5, 12, a))
    return c


def title_banner() -> Canvas:
    c = Canvas(160, 40)
    rounded_rect(c, 0, 6, 160, 28, with_alpha(UI_DARK[1], 235), radius=4)
    c.frame(0, 6, 160, 28, GOLD[1])
    c.frame(1, 7, 158, 26, GOLD[3])
    for x in range(6, 155, 12):
        c.put(x, 9, GOLD[4])
        c.put(x, 30, GOLD[4])
    for side in (10, 146):
        star(c, side, 20, 4.0, 1.6, 5, SOLAR[4])
    soft_glow(c, 80, 20, 60, with_alpha(SOLAR[4], 25))
    return c


def build_ui() -> dict[str, list[Canvas]]:
    out: dict[str, list[Canvas]] = {
        "panel": [panel()],
        "panel_arcane": [panel(ARCANE)],
        "panel_plain": [panel(UI_LIGHT)],
        "button": [button()],
        "button_pressed": [button(pressed=True)],
        "bar_frame": [bar_frame()],
        "bar_fill_health": [bar_fill(ramp=BLOOD)],
        "bar_fill_armor": [bar_fill(ramp=STEEL)],
        "bar_fill_charge": [bar_fill(ramp=PLASMA)],
        "bar_fill_boss": [bar_fill(w=156, h=8, ramp=BLOOD)],
        "boss_bar_frame": [boss_bar_frame()],
        "crosshair": crosshair(),
        "heart_full": [heart_ui("full")],
        "heart_half": [heart_ui("half")],
        "heart_empty": [heart_ui("empty")],
        "armor_ui": [armor_ui()],
        "ammo_icon": [ammo_icon()],
        "blank_icon": [blank_icon()],
        "key_icon": [key_icon()],
        "coin_icon": [coin_icon()],
        "slot": [slot(False)],
        "slot_active": [slot(True)],
        "minimap_link_h": [minimap_link(False)],
        "minimap_link_v": [minimap_link(True)],
        "damage_flash": [damage_flash()],
        "vignette": [vignette()],
        "title_banner": [title_banner()],
    }
    for kind in ("normal", "current", "cleared", "unknown", "shop",
                 "treasure", "boss", "start"):
        out[f"minimap_{kind}"] = [minimap_room(kind)]
    return out
