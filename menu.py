import os
# center the SDL window on the desktop before initializing pygame
os.environ.setdefault("SDL_VIDEO_CENTERED", "1")

import pygame
import sys
import random
import math
from typing import List, Tuple, Optional, Callable
import game  # game.py must be in the same folder

pygame.init()

# --- Config ---
SCREEN_SIZE = (1550, 900)
FPS = 60

BG_COLOR = (18, 18, 30)
ACCENT = (255, 200, 60)

FONT_NAME = None
FONT_SIZE = 28
TITLE_FONT_SIZE = 56

# Panel layout (used for positioning/title and footer)
BUTTON_WIDTH = 420
BUTTON_HEIGHT = 72
BUTTON_PADDING = 56

# Image paths
BACKGROUND_IMAGE = "assets/Background/jungle.png"
LOGO_IMAGE = ""

# Bitmap font sheet (for title only)
BITMAP_FONT_FILE = "assets/Menu/Text/Text_Font.png"
LETTER_SPACING = 3

# --- Sprite sheet config ---
SPRITE_SHEET_PATH = "assets/Menu/Buttons/Green_Button.png"
SPRITE_SHEET_W = 768
SPRITE_SHEET_H = 416

# START (uses grid-based slicing)
START_FRAME_W = 64.50
START_FRAME_H = 30
START_NORMAL_COL, START_NORMAL_ROW   = 0, 0
START_HOVER_COL,  START_HOVER_ROW    = 2, 0
START_PRESSED_COL, START_PRESSED_ROW = 0, 6
START_SCALE_NORMAL  = 3
START_SCALE_HOVER   = 3
START_SCALE_PRESSED = 0

# QUIT (independent, supports pixel coordinates or grid)
QUIT_FRAME_W = 62
QUIT_FRAME_H = 30
QUIT_NORMAL_COL,  QUIT_NORMAL_ROW  = 0 , 6
QUIT_HOVER_COL,   QUIT_HOVER_ROW   = 2 , 6
QUIT_PRESSED_COL, QUIT_PRESSED_ROW = 1, 6

# Option B: pixel-based slicing (top-left pixel coordinates inside the sheet)
QUIT_NORMAL_PIXEL = (1, 193)      # (x, y) top-left in pixels for quit normal frame
QUIT_HOVER_PIXEL = (129, 192)
QUIT_PRESSED_PIXEL = None

# QUIT per-state integer scales (independent from START)
QUIT_SCALE_NORMAL  = 3
QUIT_SCALE_HOVER   = 3
QUIT_SCALE_PRESSED = 3

# Adjustable positioning and spacing
BUTTON_BLOCK_TOP_OFFSET = 220   # distance from panel top to the first button block (pushes buttons lower from title)
BUTTON_SPACING = 48             # vertical spacing between buttons (after scaling)

# --- Image loader (nearest-neighbor for pixel art) ---
def load_image(path: str, size: Optional[Tuple[int, int]] = None) -> pygame.Surface:
    img = pygame.image.load(path).convert_alpha()
    if size:
        img = pygame.transform.scale(img, size)
    return img

def nearest_scale(surface: pygame.Surface, size: Tuple[int, int]) -> pygame.Surface:
    return pygame.transform.scale(surface, size)

# --- Simple blur helper using downscale/upscale (smoothscale) ---
def blur_surface(surface: pygame.Surface, radius: int) -> pygame.Surface:
    if radius <= 0:
        return surface.copy()
    w, h = surface.get_size()
    factor = max(1, min(16, radius))
    small_w = max(1, w // factor)
    small_h = max(1, h // factor)
    try:
        small = pygame.transform.smoothscale(surface, (small_w, small_h))
        blurred = pygame.transform.smoothscale(small, (w, h))
    except Exception:
        blurred = surface.copy()
    return blurred

# --- Pixel-perfect BitmapFont class (used for title) ---
class BitmapFont:
    def __init__(self, sheet: pygame.Surface, chars: str,
                 glyph_w: int, glyph_h: int,
                 cols: int, rows: int,
                 margin_x: int = 0, margin_y: int = 0,
                 spacing_x: int = 0, spacing_y: int = 0,
                 alpha_threshold: int = 128, padding: int = 0):
        self.sheet = sheet.convert_alpha()
        self.chars = chars
        self.glyph_w = glyph_w
        self.glyph_h = glyph_h
        self.cols = cols
        self.rows = rows
        self.margin_x = margin_x
        self.margin_y = margin_y
        self.spacing_x = spacing_x
        self.spacing_y = spacing_y
        self.alpha_threshold = max(0, min(255, alpha_threshold))
        self.padding = max(0, padding)
        self.glyphs = {}
        self._slice_glyphs()

    def _binarize_alpha(self, surf: pygame.Surface) -> pygame.Surface:
        w, h = surf.get_size()
        dst = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            for x in range(w):
                r, g, b, a = surf.get_at((x, y))
                a2 = 255 if a >= self.alpha_threshold else 0
                dst.set_at((x, y), (r, g, b, a2))
        return dst

    def _slice_glyphs(self):
        idx = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if idx >= len(self.chars):
                    return
                x = self.margin_x + c * (self.glyph_w + self.spacing_x) - self.padding
                y = self.margin_y + r * (self.glyph_h + self.spacing_y) - self.padding
                w = self.glyph_w + 2 * self.padding
                h = self.glyph_h + 2 * self.padding
                x = max(0, x)
                y = max(0, y)
                if x + w > self.sheet.get_width():
                    w = self.sheet.get_width() - x
                if y + h > self.sheet.get_height():
                    h = self.sheet.get_height() - y
                rect = pygame.Rect(x, y, w, h)
                glyph = pygame.Surface((w, h), pygame.SRCALPHA)
                glyph.blit(self.sheet, (0, 0), rect)
                glyph = self._binarize_alpha(glyph)
                self.glyphs[self.chars[idx]] = glyph
                idx += 1

    def render(self, text: str, scale: float = 1.0, letter_spacing: int = 0) -> pygame.Surface:
        text = text.upper()
        int_scale = max(1, int(round(scale)))
        gw = self.glyph_w * int_scale
        gh = self.glyph_h * int_scale
        spacing = letter_spacing * int_scale

        width = sum(gw + spacing for _ in text)
        if width <= 0:
            width = 1
        surf = pygame.Surface((width, gh), pygame.SRCALPHA)
        x = 0
        for ch in text:
            glyph = self.glyphs.get(ch)
            if glyph is None:
                glyph = pygame.Surface((self.glyph_w, self.glyph_h), pygame.SRCALPHA)
            g = nearest_scale(glyph, (gw, gh))
            surf.blit(g, (x, 0))
            x += gw + spacing
        return surf

# --- Easing helpers ---
def ease_out_cubic(t: float) -> float:
    return 1 - pow(1 - t, 3)

def smoothstep(t: float) -> float:
    return t * t * (3 - 2 * t)

# --- Sprite slicing helpers ---
def slice_frame_grid(sheet: pygame.Surface, col: int, row: int, frame_w: int, frame_h: int) -> pygame.Surface:
    col = int(col)
    row = int(row)
    x = col * frame_w
    y = row * frame_h
    rect = pygame.Rect(x, y, frame_w, frame_h)
    frame = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
    frame.blit(sheet, (0, 0), rect)
    return frame

def slice_frame_pixels(sheet: pygame.Surface, x: int, y: int, frame_w: int, frame_h: int) -> pygame.Surface:
    x = int(x)
    y = int(y)
    rect = pygame.Rect(x, y, frame_w, frame_h)
    frame = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
    frame.blit(sheet, (0, 0), rect)
    return frame

# --- Button helper (sprite-based, with per-state scales and hover/pressed states) ---
class Button:
    def __init__(self, text: str, rect: pygame.Rect, action: Optional[Callable] = None,
                 image: Optional[pygame.Surface] = None,
                 image_hover: Optional[pygame.Surface] = None,
                 image_pressed: Optional[pygame.Surface] = None,
                 scale_normal: int = 1, scale_hover: int = 1, scale_pressed: int = 1):
        self.text = text  # kept for expansion logic but not drawn
        self.rect = rect
        self.action = action
        self.image_normal = image
        self.image_hover = image_hover or image
        self.image_pressed = image_pressed or image_hover or image
        self.scale_normal = max(1, int(scale_normal))
        self.scale_hover = max(1, int(scale_hover))
        self.scale_pressed = max(1, int(scale_pressed))
        self.hovered = False
        self.pressed = False
        self.text_alpha = 255

    def current_image_and_scale(self) -> Tuple[Optional[pygame.Surface], int]:
        if self.pressed and self.image_pressed:
            return self.image_pressed, self.scale_pressed
        if self.hovered and self.image_hover:
            return self.image_hover, self.scale_hover
        return self.image_normal, self.scale_normal

    def draw(self, surf: pygame.Surface, font: pygame.font.Font, bitmap_font: Optional[BitmapFont], font_scale: float):
        img, scale = self.current_image_and_scale()
        if not img:
            return
        eff_w = img.get_width() * scale
        eff_h = img.get_height() * scale
        scaled = nearest_scale(img, (eff_w, eff_h))
        img_rect = scaled.get_rect(center=self.rect.center)
        surf.blit(scaled, img_rect.topleft)

    def update(self, dt: float):
        pass

    def handle_event(self, event: pygame.event.Event, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hovered:
            self.pressed = True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed and self.hovered and self.action:
                self.action()
            self.pressed = False

# --- Menu runner ---
def run_menu(screen: pygame.Surface, clock: pygame.time.Clock, title: str, items: List[Tuple[str, Callable]]):
    font = pygame.font.Font(FONT_NAME, FONT_SIZE)

    # load assets
    bg_img = None
    try:
        bg_img = load_image(BACKGROUND_IMAGE, size=screen.get_size()) if BACKGROUND_IMAGE else None
    except Exception:
        bg_img = None

    # Load the sprite sheet for START/QUIT
    try:
        sheet_buttons = load_image(SPRITE_SHEET_PATH)
    except Exception:
        sheet_buttons = None

    # Slice START frames (grid-based)
    start_normal = slice_frame_grid(sheet_buttons, START_NORMAL_COL, START_NORMAL_ROW, START_FRAME_W, START_FRAME_H) if sheet_buttons else None
    start_hover  = slice_frame_grid(sheet_buttons, START_HOVER_COL,  START_HOVER_ROW,  START_FRAME_W, START_FRAME_H) if sheet_buttons else None
    start_press  = slice_frame_grid(sheet_buttons, START_PRESSED_COL, START_PRESSED_ROW, START_FRAME_W, START_FRAME_H) if sheet_buttons else None

    # Slice QUIT frames (pixel-based if provided, otherwise grid-based)
    if sheet_buttons and QUIT_NORMAL_PIXEL:
        qnx, qny = QUIT_NORMAL_PIXEL
        quit_normal = slice_frame_pixels(sheet_buttons, qnx, qny, QUIT_FRAME_W, QUIT_FRAME_H)
    else:
        quit_normal = slice_frame_grid(sheet_buttons, QUIT_NORMAL_COL, QUIT_NORMAL_ROW, QUIT_FRAME_W, QUIT_FRAME_H) if sheet_buttons else None

    if sheet_buttons and QUIT_HOVER_PIXEL:
        qhx, qhy = QUIT_HOVER_PIXEL
        quit_hover = slice_frame_pixels(sheet_buttons, qhx, qhy, QUIT_FRAME_W, QUIT_FRAME_H)
    else:
        quit_hover = slice_frame_grid(sheet_buttons, QUIT_HOVER_COL, QUIT_HOVER_ROW, QUIT_FRAME_W, QUIT_FRAME_H) if sheet_buttons else None

    if sheet_buttons and QUIT_PRESSED_PIXEL:
        qpx, qpy = QUIT_PRESSED_PIXEL
        quit_press = slice_frame_pixels(sheet_buttons, qpx, qpy, QUIT_FRAME_W, QUIT_FRAME_H)
    else:
        quit_press = slice_frame_grid(sheet_buttons, QUIT_PRESSED_COL, QUIT_PRESSED_ROW, QUIT_FRAME_W, QUIT_FRAME_H) if sheet_buttons else None

    # quick sanity prints (optional)
    print("start_normal size:", getattr(start_normal, "get_size", lambda: None)())
    print("start_hover  size:", getattr(start_hover,  "get_size", lambda: None)())
    print("quit_normal  size:", getattr(quit_normal,  "get_size", lambda: None)())
    print("quit_hover   size:", getattr(quit_hover,   "get_size", lambda: None)())

    logo_img = None
    try:
        logo_img = load_image(LOGO_IMAGE, size=(300, 120)) if LOGO_IMAGE else None
    except Exception:
        logo_img = None

    # button image holder (map keys to images and scales and frame sizes)
    BUTTON_IMAGE_HOLDER = {
        "play": {
            "imgs": (start_normal, start_hover, start_press or start_hover),
            "scales": (START_SCALE_NORMAL, START_SCALE_HOVER, START_SCALE_PRESSED),
            "frame_size": (START_FRAME_W, START_FRAME_H)
        },
        "exit": {
            "imgs": (quit_normal, quit_hover, quit_press or quit_hover),
            "scales": (QUIT_SCALE_NORMAL, QUIT_SCALE_HOVER, QUIT_SCALE_PRESSED),
            "frame_size": (QUIT_FRAME_W, QUIT_FRAME_H)
        }
    }

    # layout: virtual panel_rect for positioning (centered inside the window)
    panel_w = BUTTON_WIDTH + 120
    panel_h = (BUTTON_HEIGHT + BUTTON_PADDING) * len(items) + 220
    panel_rect = pygame.Rect(0, 0, panel_w, panel_h)
    panel_rect.center = screen.get_rect().center

    # create buttons
    buttons: List[Button] = []

    # Title and button block positions
    title_y = panel_rect.y + 60
    start_y = panel_rect.y + BUTTON_BLOCK_TOP_OFFSET

    for i, (label, action) in enumerate(items):
        bx = panel_rect.centerx

        entry = BUTTON_IMAGE_HOLDER.get(label.lower())
        if entry:
            imgs = entry["imgs"]
            scales = entry["scales"]
            frame_w, frame_h = entry["frame_size"]
        else:
            imgs = (None, None, None)
            scales = (1, 1, 1)
            frame_w, frame_h = (START_FRAME_W, START_FRAME_H)

        normal, hover, press = imgs
        scale_n, scale_h, scale_p = scales

        # Use the maximum scale among states to size the collision rect so hover fits
        max_scale = max(1, scale_n, scale_h, scale_p)

        base_w = int(frame_w * max_scale)
        base_h = int(frame_h * max_scale)

        by = start_y + i * (base_h + BUTTON_SPACING)
        rect = pygame.Rect(0, 0, base_w, base_h)
        rect.center = (bx, by)

        if label.lower().startswith("play"):
            def make_trigger(act):
                def trigger():
                    trigger._trigger = True
                trigger._trigger = False
                trigger._orig = act
                return trigger
            wrapped = make_trigger(action)
            buttons.append(Button("", rect, wrapped,
                                  image=normal, image_hover=hover, image_pressed=press,
                                  scale_normal=scale_n, scale_hover=scale_h, scale_pressed=scale_p))
        else:
            buttons.append(Button("", rect, action,
                                  image=normal, image_hover=hover, image_pressed=press,
                                  scale_normal=scale_n, scale_hover=scale_h, scale_pressed=scale_p))

    selected_idx = 0
    if buttons:
        buttons[selected_idx].hovered = True

    width, height = screen.get_size()

    # particles
    particles = []
    for _ in range(28):
        pos = pygame.math.Vector2(random.random() * width, random.random() * height)
        vel = pygame.math.Vector2((random.random() - 0.5) * 20, (random.random() - 0.5) * 12)
        size = int(2 + random.random() * 4)
        alpha = int(30 + random.random() * 80)
        particles.append({"pos": pos, "vel": vel, "size": size, "alpha": alpha})

    # load bitmap font (title only)
    sheet = load_image(BITMAP_FONT_FILE)

    # measured grid values (from detector)
    glyph_w = 6
    glyph_h = 8
    cols = 10
    rows = 5
    margin_x = 1
    margin_y = 1
    spacing_x = 2
    spacing_y = 2

    CHARS_ORDER = (
        "ABCDEFGHIJ"
        "KLMNOPQRST"
        "UVWXYZ0123"
        "456789.,:?!()+-"
    )

    bitmap_font = BitmapFont(sheet, CHARS_ORDER, glyph_w, glyph_h,
                             cols, rows, margin_x, margin_y, spacing_x, spacing_y,
                             alpha_threshold=128, padding=0)

    expanding = False
    expand_button: Optional[Button] = None
    expand_duration = 1.2
    expand_elapsed = 0.0

    title_scale = max(2.0, min(4.0, 3.0 * (glyph_w / 6.0)))
    button_font_scale = max(1.0, glyph_w / 6.0 * 1.6)

    # --- Scrolling background state ---
    scroll_x = 0.0
    scroll_speed = 100
    sway_amplitude = 0
    sway_frequency = 0

    while True:
        dt = clock.tick(FPS) / 1000.0
        mouse_pos = pygame.mouse.get_pos()

        # detect play trigger
        if not expanding:
            for b in buttons:
                if callable(b.action) and getattr(b.action, "_trigger", False):
                    expanding = True
                    expand_button = b
                    expand_elapsed = 0.0
                    b.action._trigger = False
                    b.text_alpha = 255
                    for p in particles:
                        p["vel"] *= 1.6
                    break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if not expanding:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        buttons[selected_idx].hovered = False
                        selected_idx = (selected_idx + 1) % len(buttons)
                        buttons[selected_idx].hovered = True
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        buttons[selected_idx].hovered = False
                        selected_idx = (selected_idx - 1) % len(buttons)
                        buttons[selected_idx].hovered = True
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if buttons[selected_idx].action:
                            buttons[selected_idx].action()
            for b in buttons:
                b.handle_event(event, mouse_pos)

        if not expanding:
            for i, b in enumerate(buttons):
                if b.rect.collidepoint(mouse_pos):
                    if not b.hovered:
                        buttons[selected_idx].hovered = False
                        selected_idx = i
                    b.hovered = True
                else:
                    if i != selected_idx:
                        b.hovered = False

        for b in buttons:
            if not expanding:
                b.update(dt)

        # background (horizontal looping scroll + subtle vertical sway)
        if bg_img:
            scroll_x = (scroll_x + scroll_speed * dt) % width
            sx = int(scroll_x)
            t = pygame.time.get_ticks() / 1000.0
            offset_y = int(sway_amplitude * math.sin(2 * math.pi * sway_frequency * t))
            screen.blit(bg_img, (-sx, offset_y))
            screen.blit(bg_img, (width - sx, offset_y))
        else:
            top = pygame.Surface(screen.get_size())
            for y in range(screen.get_height()):
                tt = y / screen.get_height()
                rcol = int(BG_COLOR[0] * (1 - tt) + 10 * tt)
                gcol = int(BG_COLOR[1] * (1 - tt) + 20 * tt)
                bcol = int(BG_COLOR[2] * (1 - tt) + 40 * tt)
                pygame.draw.line(top, (rcol, gcol, bcol), (0, y), (screen.get_width(), y))
            screen.blit(top, (0, 0))

        # particles
        for p in particles:
            if expanding:
                p["pos"] += p["vel"] * dt * 2.2
            else:
                p["pos"] += p["vel"] * dt
            if p["pos"].x < -20:
                p["pos"].x = width + 20
            if p["pos"].x > width + 20:
                p["pos"].x = -20
            if p["pos"].y < -20:
                p["pos"].y = height + 20
            if p["pos"].y > height + 20:
                p["pos"].y = -20
            surf = pygame.Surface((p["size"] * 2, p["size"] * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 255, 255, p["alpha"]), (p["size"], p["size"]), p["size"])
            screen.blit(surf, (p["pos"].x - p["size"], p["pos"].y - p["size"]))

        # title / logo
        if logo_img:
            logo_rect = logo_img.get_rect(center=(panel_rect.centerx, title_y))
            screen.blit(logo_img, logo_rect)
        else:
            title_surf = bitmap_font.render(title, scale=title_scale, letter_spacing=LETTER_SPACING)
            title_rect = title_surf.get_rect(center=(panel_rect.centerx, title_y))
            screen.blit(title_surf, title_rect)

        # expansion animation (blur preview from play button image)
        if expanding and expand_button:
            expand_elapsed += dt
            t = min(expand_elapsed / expand_duration, 1.0)
            e = ease_out_cubic(smoothstep(t))

            start = expand_button.rect
            start_center = pygame.math.Vector2(start.centerx, start.centery)
            target_center = pygame.math.Vector2(width / 2, height / 2)
            center = start_center.lerp(target_center, e)

            start_size = pygame.math.Vector2(start.w, start.h)
            target_size = pygame.math.Vector2(width * 1.02, height * 1.02)
            size = start_size.lerp(target_size, e)
            r = pygame.Rect(0, 0, max(1, int(size.x)), max(1, int(size.y)))
            r.center = (int(center.x), int(center.y))

            # shadow (kept for expansion only; buttons themselves have no shadows)
            shadow = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            shadow.fill((0, 0, 0, int(120 * e)))
            screen.blit(shadow, (r.x + 8, r.y + 8))

            img_for_preview, _ = expand_button.current_image_and_scale()
            if img_for_preview:
                scaled_img = nearest_scale(img_for_preview, (r.w, r.h))
                diag = int((r.w * r.w + r.h * r.h) ** 0.5)
                blur_radius = max(2, min(18, diag // 120))
                blurred = blur_surface(scaled_img, blur_radius)
                preview_copy = blurred.copy()
                preview_copy.set_alpha(128)  # 50% opacity
                screen.blit(preview_copy, r.topleft)
            else:
                color = (
                    int(BG_COLOR[0] + (ACCENT[0] - BG_COLOR[0]) * e),
                    int(BG_COLOR[1] + (ACCENT[1] - BG_COLOR[1]) * e),
                    int(BG_COLOR[2] + (ACCENT[2] - BG_COLOR[2]) * e),
                )
                pygame.draw.rect(screen, color, r, border_radius=max(6, int(24 * (1 - (1 - e) * 0.8))))

            # subtle border
            border = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            pygame.draw.rect(border, (255, 255, 255, int(30 * (1 - e))), border.get_rect(), width=2, border_radius=8)
            screen.blit(border, r.topleft)

            # subtle overlay flash near completion
            if t > 0.85:
                flash_alpha = int(255 * (t - 0.85) / 0.15)
                flash = pygame.Surface((width, height), pygame.SRCALPHA)
                flash.fill((255, 255, 255, min(120, flash_alpha)))
                screen.blit(flash, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

            # push particles outward slightly
            for p in particles:
                dir_vec = (p["pos"] - center)
                if dir_vec.length() == 0:
                    dir_vec = pygame.math.Vector2(random.random() - 0.5, random.random() - 0.5)
                dir_vec = dir_vec.normalize()
                p["pos"] += dir_vec * (30 * e) * dt

            # when animation completes, ensure final preview is visible then call original action
            if t >= 1.0:
                if img_for_preview:
                    final_img = nearest_scale(img_for_preview, (width, height))
                    final_blurred = blur_surface(final_img, max(2, int((width * width + height * height) ** 0.5) // 120))
                    final_blurred.set_alpha(128)
                    screen.blit(final_blurred, (0, 0))
                    pygame.display.flip()
                orig = getattr(expand_button.action, "_orig", None)
                if callable(orig):
                    result = orig()
                    if result == "quit":
                        pygame.quit()
                        sys.exit()
                expanding = False
                expand_button.text_alpha = 255
                expand_button = None

        else:
            for b in buttons:
                b.draw(screen, font, bitmap_font, button_font_scale)

        # footer hint
        hint = pygame.font.Font(FONT_NAME, 16).render("Use arrow keys or mouse. Press Enter to select.", True, (200, 200, 210))
        hint_rect = hint.get_rect(center=(panel_rect.centerx, panel_rect.bottom - 28))
        screen.blit(hint, hint_rect)

        pygame.display.flip()

# --- Main ---
def main():
    window = pygame.display.set_mode(SCREEN_SIZE)
    pygame.display.set_caption("Game Menu")
    clock = pygame.time.Clock()

    def start_action():
        # This function is called when Play finishes expanding.
        return game.main(window)

    def quit_action():
        pygame.quit()
        sys.exit()

    menu_items = [
        ("Play", start_action),
        ("Exit", quit_action),
    ]

    run_menu(window, clock, "CAPTURE THE FLAG", menu_items)

if __name__ == "__main__":
    main()
