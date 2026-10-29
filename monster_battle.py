import math
import re
import sys
from os import listdir, path
from random import choice, random, sample, uniform

import pygame

WIDTH, HEIGHT = 1280, 720
FPS = 60
PANEL_Y = 540
ENERGY_REGEN_INTERVAL = 30  # giay
ENERGY_REGEN_AMOUNT = 20

if getattr(sys, "frozen", False):
    BASE_DIR = path.dirname(sys.executable)
else:
    BASE_DIR = path.dirname(path.abspath(__file__))
IMAGE_DIR = path.join(BASE_DIR, "images")

COLORS = {
    "Fire": (232, 85, 58),
    "Water": (58, 143, 232),
    "Plant": (76, 191, 90),
    "Normal": (170, 170, 170),
}

element_data = {
    "Fire": {"Fire": 1, "Water": 0.5, "Plant": 2, "Normal": 1},
    "Water": {"Fire": 2, "Water": 1, "Plant": 0.5, "Normal": 1},
    "Plant": {"Fire": 0.5, "Water": 2, "Plant": 1, "Normal": 1},
    "Normal": {"Fire": 1, "Water": 1, "Plant": 1, "Normal": 1},
}

abilities_data = {
    "Tackle": {"damage": 15, "element": "Normal", "cost": 5},
    "Ember": {"damage": 25, "element": "Fire", "cost": 20},
    "Inferno": {"damage": 45, "element": "Fire", "cost": 40},
    "Splash": {"damage": 25, "element": "Water", "cost": 20},
    "Tsunami": {"damage": 45, "element": "Water", "cost": 40},
    "Vine Whip": {"damage": 25, "element": "Plant", "cost": 20},
    "Solar Beam": {"damage": 45, "element": "Plant", "cost": 40},
}

monster_data = {
    "Flamy": {"element": "Fire", "health": 100, "abilities": ["Tackle", "Ember", "Inferno"]},
    "Aqua": {"element": "Water", "health": 110, "abilities": ["Tackle", "Splash", "Tsunami"]},
    "Leafo": {"element": "Plant", "health": 105, "abilities": ["Tackle", "Vine Whip", "Solar Beam"]},
    "Pyrox": {"element": "Fire", "health": 100, "abilities": ["Tackle", "Ember", "Inferno"]},
    "Tidal": {"element": "Water", "health": 110, "abilities": ["Tackle", "Splash", "Tsunami"]},
    "Thornle": {"element": "Plant", "health": 105, "abilities": ["Tackle", "Vine Whip", "Solar Beam"]},
}

ELEMENT_ABILITIES = {
    "Fire": ["Tackle", "Ember", "Inferno"],
    "Water": ["Tackle", "Splash", "Tsunami"],
    "Plant": ["Tackle", "Vine Whip", "Solar Beam"],
}


def load_monsters_from_images():
    """Bo anh nao vao images/ cung duoc (tru background): moi anh = 1 quai vat.
    Ten quai lay tu ten file, he tu dong chon. Moi van game boc ngau nhien
    6 quai trong kho."""
    if not path.isdir(IMAGE_DIR):
        return
    known = {}
    for name in monster_data:
        known[name.lower()] = name

    stems = []
    for file in sorted(listdir(IMAGE_DIR)):
        stem, ext = path.splitext(file)
        if ext.lower() in (".png", ".jpg", ".jpeg", ".webp") and stem not in stems:
            stems.append(stem)

    for stem in stems:
        key = stem.lower()
        if key == "background" or key in known:
            continue
        element = list(ELEMENT_ABILITIES)[sum(ord(c) for c in key) % 3]

        display = re.sub(r"[_\-\.\(\)\[\]\s]+", " ", stem).strip().title()[:12].strip()
        if display == "":
            display = "Monster"
        unique = display
        n = 2
        while unique in monster_data:
            unique = display + " " + str(n)
            n += 1

        monster_data[unique] = {
            "element": element,
            "health": 95 + sum(ord(c) for c in key) % 21,
            "abilities": ELEMENT_ABILITIES[element],
            "image": stem,
        }


load_monsters_from_images()

image_cache = {}


def is_white(color):
    return color[0] > 225 and color[1] > 225 and color[2] > 225 and color[3] > 0


def remove_white_background(image):
    width, height = image.get_size()
    corners = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    if not is_white(image.get_at(corners[0])):
        return image
    todo = list(corners)
    visited = set(corners)
    while len(todo) > 0:
        x, y = todo.pop()
        if not is_white(image.get_at((x, y))):
            continue
        image.set_at((x, y), (255, 255, 255, 0))
        for nx, ny in [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]:
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                visited.add((nx, ny))
                todo.append((nx, ny))
    return image


def fit_image(image, max_width, max_height):
    ratio = min(max_width / image.get_width(), max_height / image.get_height())
    new_width = max(1, int(image.get_width() * ratio))
    new_height = max(1, int(image.get_height() * ratio))
    return pygame.transform.smoothscale(image, (new_width, new_height))


def load_image(name, max_size=None, size=None):
    key = (name, max_size, size)
    if key in image_cache:
        return image_cache[key]
    image = None
    candidates = []
    for ext in ["png", "jpg", "jpeg", "webp"]:
        candidates.append(path.join(IMAGE_DIR, name + "." + ext))
        candidates.append(path.join(IMAGE_DIR, name.lower() + "." + ext))
    for file in candidates:
        if path.exists(file):
            try:
                raw = pygame.image.load(file).convert_alpha()
                if size:
                    image = pygame.transform.smoothscale(raw, size)
                else:
                    image = fit_image(raw, 400, 400)
                    image = remove_white_background(image)
                    box = image.get_bounding_rect()
                    if box.width > 0 and box.height > 0:
                        image = image.subsurface(box).copy()
                    image = fit_image(image, max_size[0], max_size[1])
            except pygame.error:
                image = None
            break
    image_cache[key] = image
    return image


def make_attack_frames(element):
    color = COLORS[element]
    frames = []
    for i in range(10):
        frame = pygame.Surface((300, 300), pygame.SRCALPHA)
        radius = 20 + i * 12
        alpha = 255 - i * 22
        pygame.draw.circle(frame, color + (alpha,), (150, 150), radius, 14)
        for k in range(8):
            angle = k * math.pi / 4 + i * 0.25
            px = 150 + math.cos(angle) * (radius + 14)
            py = 150 + math.sin(angle) * (radius + 14)
            pygame.draw.circle(frame, (255, 255, 255, alpha), (int(px), int(py)), 8)
        frames.append(frame)
    return frames


class AttackAnimationSprite(pygame.sprite.Sprite):
    def __init__(self, target, frames, groups):
        super().__init__(groups)
        self.frames = frames
        self.frame_index = 0
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=target.center)

    def update(self, dt):
        self.frame_index += 12 * dt
        if self.frame_index < len(self.frames):
            self.image = self.frames[int(self.frame_index)]
        else:
            self.kill()


class Timer:
    def __init__(self, duration, function=None):
        self.duration = duration
        self.function = function
        self.passed = 0
        self.active = False

    def activate(self):
        self.active = True
        self.passed = 0

    def update(self, dt):
        if self.active:
            self.passed += dt
            if self.passed >= self.duration:
                self.active = False
                if self.function:
                    self.function()


class Monster:
    def __init__(self, name):
        data = monster_data[name]
        self.name = name
        self.image_name = data.get("image", name)
        self.element = data["element"]
        self.max_health = data["health"]
        self.health = data["health"]
        self.disp_health = float(data["health"])
        self.abilities = data["abilities"]
        self.energy = 60
        self.max_energy = 100
        self.defending = False
        self.flash = 0
        self.center = (0, 0)
        self.scale = 1
        self.phase = uniform(0, 6.28)


def draw_monster(screen, mon, t):
    if mon.disp_health < 0.5:
        return
    if mon.flash > 0 and (mon.flash // 4) % 2 == 0:
        return

    x, y = mon.center
    scale = mon.scale
    bob = math.sin(t * 3 + mon.phase) * 6 * scale
    image = load_image(mon.image_name, max_size=(int(300 * scale), int(290 * scale)))
    if image:
        screen.blit(image, image.get_rect(midbottom=(int(x), int(y + 115 * scale + bob))))
        return

    y = y + bob
    color = COLORS[mon.element]
    light = (min(255, color[0] + 60), min(255, color[1] + 60), min(255, color[2] + 60))
    dark = (max(0, color[0] - 70), max(0, color[1] - 70), max(0, color[2] - 70))
    top = y - 100 * scale

    if mon.element == "Fire":
        points = [(-30, 25), (-20, -25), (-6, 0), (0, -55), (8, -2), (22, -28), (30, 25)]
        pygame.draw.polygon(screen, (255, 150, 40), [(x + px * scale, top + py * scale) for px, py in points])
        points = [(-14, 25), (0, -20), (14, 25)]
        pygame.draw.polygon(screen, (255, 225, 80), [(x + px * scale, top + py * scale) for px, py in points])
    elif mon.element == "Water":
        pygame.draw.circle(screen, light, (int(x), int(top + 8 * scale)), int(24 * scale))
        pygame.draw.polygon(screen, light, [(x - 21 * scale, top), (x, top - 48 * scale), (x + 21 * scale, top)])
    else:
        pygame.draw.polygon(screen, (60, 170, 70), [(x, top - 8 * scale), (x - 48 * scale, top - 40 * scale), (x - 12 * scale, top + 8 * scale)])
        pygame.draw.polygon(screen, (90, 210, 100), [(x, top - 8 * scale), (x + 48 * scale, top - 40 * scale), (x + 12 * scale, top + 8 * scale)])

    for side in [-1, 1]:
        arm = pygame.Rect(0, 0, int(40 * scale), int(70 * scale))
        arm.center = (int(x + side * 88 * scale), int(y + 20 * scale))
        pygame.draw.ellipse(screen, dark, arm)
        foot = pygame.Rect(0, 0, int(55 * scale), int(30 * scale))
        foot.center = (int(x + side * 40 * scale), int(y + 100 * scale))
        pygame.draw.ellipse(screen, dark, foot)

    body = pygame.Rect(0, 0, int(170 * scale), int(200 * scale))
    body.center = (int(x), int(y))
    pygame.draw.ellipse(screen, color, body)
    pygame.draw.ellipse(screen, dark, body, 4)
    belly = pygame.Rect(0, 0, int(110 * scale), int(115 * scale))
    belly.center = (int(x), int(y + 35 * scale))
    pygame.draw.ellipse(screen, light, belly)

    for side in [-1, 1]:
        eye_x = int(x + side * 34 * scale)
        eye_y = int(y - 35 * scale)
        pygame.draw.circle(screen, (255, 255, 255), (eye_x, eye_y), int(19 * scale))
        pygame.draw.circle(screen, (20, 20, 30), (eye_x + 3, eye_y + 2), int(9 * scale))
    mouth = pygame.Rect(0, 0, int(50 * scale), int(30 * scale))
    mouth.center = (int(x), int(y + 2 * scale))
    pygame.draw.arc(screen, (40, 20, 20), mouth, math.pi, 2 * math.pi, 4)


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Monster Battle")
        self.clock = pygame.time.Clock()
        self.big_font = pygame.font.Font(None, 64)
        self.font = pygame.font.Font(None, 40)
        self.small_font = pygame.font.Font(None, 28)
        self.t = 0.0

        self.attack_frames = {}
        for attack in abilities_data:
            self.attack_frames[attack] = make_attack_frames(abilities_data[attack]["element"])
        self.all_sprites = pygame.sprite.Group()

        self.timers = {
            "start": Timer(1.5, self.start_player_turn),
            "player_end": Timer(1.8, self.player_turn_end),
            "opponent_end": Timer(1.8, self.opponent_turn_end),
            "new_opponent": Timer(1.5, self.start_player_turn),
        }
        self.reset()

    def reset(self):
        picks = sample(list(monster_data), 6)
        self.player_team = [Monster(name) for name in picks[:3]]
        self.opponent_team = [Monster(name) for name in picks[3:]]
        for mon in self.player_team:
            mon.center = (300, 365)
            mon.scale = 1.2
        for mon in self.opponent_team:
            mon.center = (960, 235)
            mon.scale = 0.9

        self.monster_index = 0
        self.opponent_index = 0
        self.winner = None
        self.regen_timer = 0.0
        self.forced = False
        self.menu = "main"
        self.cursor = 0
        self.all_sprites.empty()
        for timer in self.timers.values():
            timer.active = False

        self.state = "waiting"
        self.message = "A rival trainer challenges you! Go, " + self.monster.name + "!"
        self.timers["start"].activate()

    @property
    def monster(self):
        return self.player_team[self.monster_index]

    @property
    def opponent(self):
        return self.opponent_team[self.opponent_index]

    def label(self, mon):
        if mon in self.opponent_team:
            return "Enemy " + mon.name
        return mon.name

    def start_player_turn(self):
        self.state = "player_turn"
        self.menu = "main"
        self.cursor = 0
        self.forced = False

    def apply_attack(self, target, attack, attack_data):
        AttackAnimationSprite(
            target=target,
            frames=self.attack_frames[attack],
            groups=self.all_sprites,
        )

        base_damage = attack_data["damage"]
        attack_element = attack_data["element"]
        target_element = target.element
        attack_multiplier = element_data[attack_element][target_element]
        total_damage = base_damage * attack_multiplier
        if target.defending:
            total_damage = total_damage * 0.5
        total_damage = int(total_damage)

        target.health = max(0, target.health - total_damage)
        target.flash = 40

        result = "It deals " + str(total_damage) + " damage."
        if attack_multiplier > 1:
            result = "It's super effective! " + result
        elif attack_multiplier < 1:
            result = "It's not very effective... " + result
        if target.health <= 0:
            result = result + " " + self.label(target) + " fainted!"
        return result

    def player_turn(self, action):
        self.state = "waiting"
        if action[0] == "attack":
            attack = action[1]
            attack_data = abilities_data[attack]
            self.monster.energy -= attack_data["cost"]
            result = self.apply_attack(self.opponent, attack, attack_data)
            self.message = self.monster.name + " uses " + attack + "! " + result
        elif action[0] == "defend":
            self.monster.defending = True
            self.monster.energy = min(self.monster.max_energy, self.monster.energy + 25)
            self.message = self.monster.name + " braces itself and recovers energy!"
        else:
            old_name = self.monster.name
            self.monster_index = action[1]
            self.message = old_name + ", come back! Go, " + self.monster.name + "!"
        self.timers["player_end"].activate()

    def player_turn_end(self):
        if self.opponent.health > 0:
            self.opponent_turn()
            return

        next_index = None
        for i in range(len(self.opponent_team)):
            if self.opponent_team[i].health > 0:
                next_index = i
                break
        if next_index is None:
            self.winner = "player"
            self.state = "game_over"
        else:
            self.opponent_index = next_index
            self.message = "Enemy sends out " + self.opponent.name + "!"
            self.timers["new_opponent"].activate()

    def opponent_turn(self):
        self.opponent.defending = False
        usable = []
        for attack in self.opponent.abilities:
            if abilities_data[attack]["cost"] <= self.opponent.energy:
                usable.append(attack)

        if len(usable) == 0 or random() < 0.1:
            self.opponent.defending = True
            self.opponent.energy = min(self.opponent.max_energy, self.opponent.energy + 25)
            self.message = self.label(self.opponent) + " braces itself and recovers energy!"
        else:
            attack = choice(usable)
            attack_data = abilities_data[attack]
            self.opponent.energy -= attack_data["cost"]
            result = self.apply_attack(self.monster, attack, attack_data)
            self.message = self.label(self.opponent) + " uses " + attack + "! " + result
        self.timers["opponent_end"].activate()

    def opponent_turn_end(self):
        self.monster.defending = False
        for mon in [self.monster, self.opponent]:
            mon.energy = min(mon.max_energy, mon.energy + 10)

        if self.monster.health > 0:
            self.start_player_turn()
            return

        has_alive = False
        for mon in self.player_team:
            if mon.health > 0:
                has_alive = True
        if has_alive:
            self.state = "player_turn"
            self.menu = "switch"
            self.forced = True
            for i in range(len(self.player_team)):
                if self.player_team[i].health > 0:
                    self.cursor = i
                    break
        else:
            self.winner = "opponent"
            self.state = "game_over"

    def handle_key(self, key):
        up = key == pygame.K_UP or key == pygame.K_w
        down = key == pygame.K_DOWN or key == pygame.K_s
        ok = key == pygame.K_RETURN or key == pygame.K_SPACE
        back = key == pygame.K_ESCAPE

        if self.state == "game_over":
            if ok:
                self.reset()
            return
        if self.state != "player_turn":
            return

        if self.menu == "main":
            self.move_cursor(up, down, 3)
            if ok:
                if self.cursor == 0:
                    self.menu = "attack"
                    self.cursor = 0
                elif self.cursor == 1:
                    self.player_turn(["defend"])
                else:
                    self.menu = "switch"
                    self.cursor = 0
                    self.forced = False

        elif self.menu == "attack":
            self.move_cursor(up, down, len(self.monster.abilities))
            if back:
                self.menu = "main"
                self.cursor = 0
            elif ok:
                attack = self.monster.abilities[self.cursor]
                if abilities_data[attack]["cost"] <= self.monster.energy:
                    self.player_turn(["attack", attack])

        elif self.menu == "switch":
            self.move_cursor(up, down, len(self.player_team))
            if back and not self.forced:
                self.menu = "main"
                self.cursor = 0
            elif ok:
                i = self.cursor
                if self.player_team[i].health > 0 and i != self.monster_index:
                    if self.forced:
                        self.monster_index = i
                        self.message = "Go, " + self.monster.name + "!"
                        self.start_player_turn()
                    else:
                        self.player_turn(["switch", i])

    def move_cursor(self, up, down, count):
        if up:
            self.cursor = (self.cursor - 1) % count
        if down:
            self.cursor = (self.cursor + 1) % count

    def update(self, dt):
        self.t += dt
        for timer in self.timers.values():
            timer.update(dt)
        self.all_sprites.update(dt)
        if self.state != "game_over":
            self.regen_timer += dt
            if self.regen_timer >= ENERGY_REGEN_INTERVAL:
                self.regen_timer = 0.0
                for mon in self.player_team + self.opponent_team:
                    if mon.health > 0:
                        mon.energy = min(mon.max_energy, mon.energy + ENERGY_REGEN_AMOUNT)
        for mon in self.player_team + self.opponent_team:
            if mon.flash > 0:
                mon.flash -= 1
            diff = mon.health - mon.disp_health
            if abs(diff) < 0.3:
                mon.disp_health = mon.health
            else:
                mon.disp_health += diff * min(1, dt * 6)

    def draw_background(self):
        image = load_image("background", size=(WIDTH, PANEL_Y))
        if image:
            self.screen.blit(image, (0, 0))
            return
        self.screen.fill((135, 200, 235))
        pygame.draw.rect(self.screen, (110, 175, 95), (0, 300, WIDTH, PANEL_Y - 300))
        for cx, cy in [(200, 90), (620, 140), (1100, 70)]:
            pygame.draw.circle(self.screen, (250, 250, 255), (cx, cy), 34)
            pygame.draw.circle(self.screen, (250, 250, 255), (cx + 36, cy + 8), 28)
            pygame.draw.circle(self.screen, (250, 250, 255), (cx - 36, cy + 10), 26)
        pygame.draw.ellipse(self.screen, (85, 150, 75), (810, 325, 300, 50))
        pygame.draw.ellipse(self.screen, (85, 150, 75), (110, 470, 380, 70))

    def draw_bar(self, x, y, w, h, ratio, color):
        pygame.draw.rect(self.screen, (40, 40, 50), (x, y, w, h), border_radius=6)
        ratio = max(0, min(1, ratio))
        if ratio > 0:
            pygame.draw.rect(self.screen, color, (x, y, int(w * ratio), h), border_radius=6)

    def draw_info(self, mon, x, y, w, is_player):
        h = 95
        if is_player:
            h = 125
        pygame.draw.rect(self.screen, (245, 245, 250), (x, y, w, h), border_radius=14)
        pygame.draw.rect(self.screen, (40, 40, 60), (x, y, w, h), 4, border_radius=14)
        self.screen.blit(self.font.render(mon.name, True, (30, 30, 40)), (x + 16, y + 10))

        tag = self.small_font.render(mon.element, True, (255, 255, 255))
        tag_rect = tag.get_rect(topright=(x + w - 16, y + 14)).inflate(16, 6)
        pygame.draw.rect(self.screen, COLORS[mon.element], tag_rect, border_radius=8)
        self.screen.blit(tag, tag.get_rect(center=tag_rect.center))

        ratio = mon.disp_health / mon.max_health
        bar_color = (230, 70, 60)
        if ratio > 0.5:
            bar_color = (80, 200, 90)
        elif ratio > 0.25:
            bar_color = (240, 200, 60)
        self.screen.blit(self.small_font.render("HP", True, (30, 30, 40)), (x + 16, y + 52))
        self.draw_bar(x + 56, y + 54, w - 76, 16, ratio, bar_color)

        if is_player:
            hp_text = str(int(round(mon.disp_health))) + "/" + str(mon.max_health)
            self.screen.blit(self.small_font.render(hp_text, True, (30, 30, 40)), (x + w - 100, y + 74))
            self.screen.blit(self.small_font.render("EN", True, (30, 30, 40)), (x + 16, y + 92))
            self.draw_bar(x + 56, y + 94, w - 76, 12, mon.energy / mon.max_energy, (70, 140, 240))

    def wrap_text(self, text, width):
        lines = []
        line = ""
        for word in text.split():
            test = (line + " " + word).strip()
            if self.font.size(test)[0] <= width:
                line = test
            else:
                lines.append(line)
                line = word
        lines.append(line)
        return lines

    def draw_menu(self, items, enabled):
        for i in range(len(items)):
            color = (120, 120, 130)
            if enabled[i]:
                color = (255, 255, 255)
            if i == self.cursor:
                self.screen.blit(self.font.render(">", True, (255, 220, 80)), (34, PANEL_Y + 28 + i * 44))
            self.screen.blit(self.font.render(items[i], True, color), (70, PANEL_Y + 28 + i * 44))

    def draw_hint(self, first_line):
        lines = [
            first_line,
            "Fire > Plant > Water > Fire  (x2 damage)",
            "Energy is spent on attacks; Defend halves damage",
        ]
        for i in range(len(lines)):
            text = self.small_font.render(lines[i], True, (160, 160, 180))
            self.screen.blit(text, text.get_rect(topright=(WIDTH - 40, PANEL_Y + 28 + i * 34)))

    def draw(self):
        self.draw_background()
        draw_monster(self.screen, self.opponent, self.t)
        draw_monster(self.screen, self.monster, self.t)
        self.all_sprites.draw(self.screen)
        self.draw_info(self.opponent, 40, 40, 420, False)
        self.draw_info(self.monster, 800, 395, 440, True)

        pygame.draw.rect(self.screen, (35, 35, 55), (0, PANEL_Y, WIDTH, HEIGHT - PANEL_Y))
        pygame.draw.rect(self.screen, (255, 220, 80), (0, PANEL_Y, WIDTH, 6))

        if self.state == "waiting":
            lines = self.wrap_text(self.message, WIDTH - 140)
            for i in range(len(lines)):
                self.screen.blit(self.font.render(lines[i], True, (255, 255, 255)), (70, PANEL_Y + 30 + i * 44))

        elif self.state == "player_turn":
            if self.menu == "main":
                self.draw_menu(["Attack", "Defend (recover energy)", "Switch monster"], [True, True, True])
                self.draw_hint("UP/DOWN to choose, ENTER to confirm")

            elif self.menu == "attack":
                items = []
                enabled = []
                for attack in self.monster.abilities:
                    data = abilities_data[attack]
                    items.append(attack + "  [" + data["element"] + "]  damage " + str(data["damage"]) + "  cost " + str(data["cost"]))
                    enabled.append(data["cost"] <= self.monster.energy)
                self.draw_menu(items, enabled)
                self.draw_hint("ESC to go back")

            elif self.menu == "switch":
                items = []
                enabled = []
                for i in range(len(self.player_team)):
                    mon = self.player_team[i]
                    note = ""
                    if i == self.monster_index:
                        note = " (in battle)"
                    elif mon.health <= 0:
                        note = " (fainted)"
                    items.append(mon.name + "  [" + mon.element + "]  HP " + str(mon.health) + "/" + str(mon.max_health) + note)
                    enabled.append(mon.health > 0 and i != self.monster_index)
                self.draw_menu(items, enabled)
                if self.forced:
                    self.draw_hint("Choose your next monster")
                else:
                    self.draw_hint("ESC to go back")

        elif self.state == "game_over":
            if self.winner == "player":
                self.screen.blit(self.big_font.render("YOU WIN!", True, (120, 230, 120)), (70, PANEL_Y + 35))
            else:
                self.screen.blit(self.big_font.render("YOU LOSE...", True, (240, 100, 90)), (70, PANEL_Y + 35))
            self.screen.blit(self.font.render("Press ENTER to play again", True, (255, 255, 255)), (70, PANEL_Y + 105))

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    self.handle_key(event.key)
            self.update(dt)
            self.draw()
            pygame.display.update()


if __name__ == "__main__":
    Game().run()