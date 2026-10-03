import random

WIDTH = 800
GROUND = 190
GRAVITY = 0.6
JUMP = -11.5


def touching(a, b):
    # boxes are [left, top, right, bottom]
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


class Dino:
    def __init__(self):
        self.x = 60
        self.feet = GROUND
        self.vy = 0
        self.ducking = False
        self.steps = 0

    def jump(self):
        if self.feet >= GROUND:
            self.vy = JUMP

    def update(self, dt, down):
        g = GRAVITY
        if down and self.vy > 0:
            g = GRAVITY * 3  # fall faster when holding down
        self.vy += g * dt
        self.feet += self.vy * dt

        if self.feet >= GROUND:
            self.feet = GROUND
            self.vy = 0
            self.steps += dt  # only counts while running
        self.ducking = down and self.feet >= GROUND

    def boxes(self):
        # hitboxes are a bit smaller than the drawing so near misses feel fair
        if self.ducking:
            return [[self.x + 4, self.feet - 22, self.x + 54, self.feet - 2]]
        top = self.feet - 42
        return [[self.x + 10, top + 14, self.x + 32, self.feet - 2],
                [self.x + 22, top + 2, self.x + 42, top + 16]]


class Cactus:
    def __init__(self, x, large, count):
        self.kind = "cactus"
        self.x = x
        self.count = count
        self.unit = 17
        self.height = 36
        if large:
            self.unit = 25
            self.height = 52
        self.width = self.unit * count

    def update(self, speed, dt):
        self.x -= speed * dt

    def boxes(self):
        return [[self.x + 3, GROUND - self.height + 3,
                 self.x + self.width - 3, GROUND]]


class Rock:
    def __init__(self, x, big):
        self.kind = "rock"
        self.x = x
        self.width = 28
        self.height = 18
        if big:
            self.width = 42
            self.height = 26

    def update(self, speed, dt):
        self.x -= speed * 1.15 * dt  # rocks are a bit faster than the ground

    def boxes(self):
        return [[self.x + 4, GROUND - self.height + 4,
                 self.x + self.width - 4, GROUND]]


class Bird:
    def __init__(self, x, lift):
        self.kind = "bird"
        self.x = x
        self.width = 48
        self.height = 28
        self.top = GROUND - lift - self.height
        self.flap = 0

    def update(self, speed, dt):
        self.x -= (speed + 1) * dt
        self.flap += dt

    def wings_up(self):
        return int(self.flap / 8) % 2 == 0

    def boxes(self):
        return [[self.x + 4, self.top + 6, self.x + 44, self.top + 22]]


class Cloud:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def update(self, speed, dt):
        self.x -= speed * 0.2 * dt
        if self.x < -70:
            self.x = WIDTH + random.randint(0, 200)
            self.y = random.randint(25, 110)

import os
import random
import time
import tkinter as tk

# The game entities are defined in this file; importing from a separate
# `entities` module fails when the file is run directly.

HEIGHT = 240
FRAME_MS = 16
START_SPEED = 6
MAX_SPEED = 14
ACCEL = 0.002
BIRD_HEIGHTS = [10, 30, 62]

DAY_BG = "#f7f7f7"
DAY_FG = "#535353"
NIGHT_BG = "#1c1c1c"
NIGHT_FG = "#d8d8d8"

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trex_best.txt")


def mix(c1, c2, t):
    # blend two "#rrggbb" colors, t=0 gives c1 and t=1 gives c2
    result = "#"
    for i in range(1, 7, 2):
        a = int(c1[i:i + 2], 16)
        b = int(c2[i:i + 2], 16)
        result += format(int(a + (b - a) * t), "02x")
    return result


def load_best():
    if not os.path.exists(SAVE_FILE):
        return 0
    with open(SAVE_FILE) as f:
        text = f.read().strip()
    if text.isdigit():
        return int(text)
    return 0


def save_best(score):
    with open(SAVE_FILE, "w") as f:
        f.write(str(score))


class Game:
    def __init__(self, root):
        self.root = root
        root.title("T-Rex Run")
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, highlightthickness=0)
        self.canvas.pack()

        self.best = load_best()
        self.down = False
        self.down_press = 0
        self.down_release = 0
        self.last = time.time()

        root.bind("<KeyPress>", self.on_press)
        root.bind("<KeyRelease>", self.on_release)
        self.reset()
        self.frame()

    def reset(self):
        self.dino = Dino()
        self.obstacles = []

        self.clouds = []
        for i in range(3):
            self.clouds.append(Cloud(random.randint(0, WIDTH), random.randint(25, 110)))

        # each bump is [x, width, how far below the ground line]
        self.bumps = []
        for i in range(30):
            self.bumps.append([i * 30 + random.randint(0, 20),
                               random.randint(2, 10), random.randint(4, 14)])

        self.stars = []
        for i in range(25):
            self.stars.append([random.randint(0, WIDTH), random.randint(10, 120)])

        self.speed = START_SPEED
        self.distance = 0
        self.score = 0
        self.night = 0  # 0 is day, 1 is night, fades in between
        self.gap = 0
        self.flash_until = 0
        self.started = False
        self.over = False
        self.over_time = 0

    def on_press(self, event):
        key = event.keysym.lower()
        now = time.time()

        if key == "space" or key == "up" or key == "w":
            if self.over:
                # small delay so a late jump press doesn't restart instantly
                if now - self.over_time > 0.4:
                    self.reset()
                    self.started = True
            else:
                self.started = True
                self.dino.jump()
        elif key == "down" or key == "s":
            self.down = True
            self.down_press = now

    def on_release(self, event):
        key = event.keysym.lower()
        if key == "down" or key == "s":
            self.down_release = time.time()

    def spawn(self):
        # wait until the last obstacle is far enough away
        room = WIDTH
        if len(self.obstacles) > 0:
            last = self.obstacles[-1]
            room = WIDTH - (last.x + last.width)

        if room < self.gap:
            return

        if self.score >= 300 and random.random() < 0.25:
            self.obstacles.append(Bird(WIDTH, random.choice(BIRD_HEIGHTS)))
        elif self.score >= 150 and random.random() < 0.2:
            self.obstacles.append(Rock(WIDTH, random.random() < 0.5))
        else:
            self.obstacles.append(Cactus(WIDTH, random.random() < 0.5, random.randint(1, 3)))

        base = int(self.speed * 30 + 150)
        self.gap = random.randint(base, base + 250)

    def crashed(self):
        for ob in self.obstacles:
            for mine in self.dino.boxes():
                for theirs in ob.boxes():
                    if touching(mine, theirs):
                        return True
        return False

    def game_over(self, now):
        self.over = True
        self.over_time = now
        if self.score > self.best:
            self.best = self.score
            save_best(self.best)

    def update(self, dt, now):
        self.speed = min(MAX_SPEED, self.speed + ACCEL * dt)
        self.distance += self.speed * dt

        old = self.score
        self.score = int(self.distance * 0.03)
        if self.score // 100 > old // 100:
            self.flash_until = now + 0.9

        # every 700 points switch between day and night
        goal = 0
        if (self.score // 700) % 2 == 1:
            goal = 1
        if self.night < goal:
            self.night = min(goal, self.night + 0.02 * dt)
        elif self.night > goal:
            self.night = max(goal, self.night - 0.02 * dt)

        self.dino.update(dt, self.down)

        for bump in self.bumps:
            bump[0] -= self.speed * dt
            if bump[0] + bump[1] < 0:
                bump[0] += WIDTH + random.randint(0, 60)
                bump[1] = random.randint(2, 10)
                bump[2] = random.randint(4, 14)

        for cloud in self.clouds:
            cloud.update(self.speed, dt)

        still_on_screen = []
        for ob in self.obstacles:
            ob.update(self.speed, dt)
            if ob.x + ob.width > 0:
                still_on_screen.append(ob)
        self.obstacles = still_on_screen

        self.spawn()
        if self.crashed():
            self.game_over(now)

    # ---------- drawing ----------

    def rect(self, x1, y1, x2, y2, color):
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

    def poly(self, points, color):
        self.canvas.create_polygon(points, fill=color, outline="")

    def draw_cactus(self, c, color):
        h = c.height
        w = c.unit - 2
        for i in range(c.count):
            x = c.x + i * c.unit
            self.rect(x + w * 0.36, GROUND - h, x + w * 0.64, GROUND, color)
            # left arm
            self.rect(x + w * 0.08, GROUND - h * 0.58, x + w * 0.36, GROUND - h * 0.46, color)
            self.rect(x + w * 0.08, GROUND - h * 0.78, x + w * 0.22, GROUND - h * 0.46, color)
            # right arm
            self.rect(x + w * 0.64, GROUND - h * 0.50, x + w * 0.92, GROUND - h * 0.38, color)
            self.rect(x + w * 0.78, GROUND - h * 0.70, x + w * 0.92, GROUND - h * 0.38, color)

    def draw_rock(self, r, color, bg):
        x = r.x
        w = r.width
        h = r.height
        self.poly([x, GROUND,
                   x + w * 0.08, GROUND - h * 0.55,
                   x + w * 0.32, GROUND - h,
                   x + w * 0.68, GROUND - h * 0.88,
                   x + w * 0.95, GROUND - h * 0.42,
                   x + w, GROUND], color)
        # crack
        self.canvas.create_line(x + w * 0.42, GROUND - h * 0.78,
                                x + w * 0.52, GROUND - h * 0.45,
                                x + w * 0.46, GROUND - h * 0.2,
                                fill=bg, width=2)

    def draw_bird(self, b, color):
        x = b.x
        t = b.top
        self.canvas.create_oval(x + 8, t + 10, x + 40, t + 22, fill=color, outline="")
        self.poly([x, t + 14, x + 12, t + 10, x + 12, t + 18], color)        # beak
        self.poly([x + 36, t + 14, x + 48, t + 9, x + 48, t + 19], color)    # tail
        if b.wings_up():
            self.poly([x + 14, t + 13, x + 26, t, x + 33, t + 13], color)
        else:
            self.poly([x + 14, t + 19, x + 26, t + 28, x + 33, t + 19], color)

    def draw_cloud(self, c, color):
        self.canvas.create_oval(c.x, c.y + 8, c.x + 56, c.y + 24, fill=color, outline="")
        self.canvas.create_oval(c.x + 10, c.y, c.x + 32, c.y + 18, fill=color, outline="")
        self.canvas.create_oval(c.x + 28, c.y + 3, c.x + 48, c.y + 18, fill=color, outline="")

    def draw_eye(self, x, y, bg):
        if self.over:
            self.canvas.create_line(x - 2, y - 2, x + 3, y + 3, fill=bg, width=2)
            self.canvas.create_line(x - 2, y + 3, x + 3, y - 2, fill=bg, width=2)
        else:
            self.rect(x - 1, y - 1, x + 3, y + 3, bg)

    def draw_dino(self, fg, bg):
        d = self.dino
        x = d.x
        f = d.feet

        # lift one foot at a time while running
        left = f
        right = f
        if f >= GROUND and self.started and not self.over:
            if int(d.steps / 6) % 2 == 0:
                left = f - 5
            else:
                right = f - 5

        if d.ducking:
            self.rect(x + 4, f - 20, x + 44, f - 6, fg)
            self.rect(x + 38, f - 22, x + 56, f - 10, fg)
            self.poly([x + 4, f - 18, x - 8, f - 21, x - 4, f - 12, x + 4, f - 8], fg)
            self.rect(x + 12, f - 6, x + 18, left, fg)
            self.rect(x + 28, f - 6, x + 34, right, fg)
            self.draw_eye(x + 49, f - 19, bg)
        else:
            self.rect(x + 14, f - 30, x + 36, f - 12, fg)
            self.rect(x + 22, f - 42, x + 44, f - 28, fg)
            self.poly([x + 14, f - 28, x - 2, f - 32, x + 2, f - 22, x + 14, f - 14], fg)
            self.rect(x + 34, f - 24, x + 42, f - 20, fg)
            self.rect(x + 16, f - 12, x + 22, left, fg)
            self.rect(x + 28, f - 12, x + 34, right, fg)
            self.draw_eye(x + 34, f - 39, bg)

    def draw(self, now):
        bg = mix(DAY_BG, NIGHT_BG, self.night)
        fg = mix(DAY_FG, NIGHT_FG, self.night)
        faded = mix(bg, fg, 0.6)

        self.canvas.config(bg=bg)
        self.canvas.delete("all")

        if self.night > 0.05:
            star_color = mix(bg, fg, self.night * 0.7)
            for star in self.stars:
                self.rect(star[0], star[1], star[0] + 2, star[1] + 2, star_color)
            # moon is a circle with a second circle cut out of it
            self.canvas.create_oval(666, 46, 694, 74, fill=mix(bg, fg, self.night), outline="")
            self.canvas.create_oval(674, 44, 702, 72, fill=bg, outline="")

        for cloud in self.clouds:
            self.draw_cloud(cloud, mix(bg, fg, 0.15))

        self.canvas.create_line(0, GROUND + 1, WIDTH, GROUND + 1, fill=fg, width=2)
        for bump in self.bumps:
            y = GROUND + bump[2]
            self.canvas.create_line(bump[0], y, bump[0] + bump[1], y, fill=faded, width=2)

        for ob in self.obstacles:
            if ob.kind == "cactus":
                self.draw_cactus(ob, fg)
            elif ob.kind == "rock":
                self.draw_rock(ob, fg, bg)
            else:
                self.draw_bird(ob, fg)

        self.draw_dino(fg, bg)

        score = str(self.score).zfill(5)
        if now < self.flash_until and int(now * 8) % 2 == 0:
            score = "     "  # blink on every 100 points
        self.canvas.create_text(WIDTH - 20, 14, anchor="ne", fill=fg, font="Courier 16 bold",
                                text="HI " + str(self.best).zfill(5) + "  " + score)

        if not self.started:
            self.canvas.create_text(WIDTH // 2, 70, fill=fg, font="Courier 18 bold",
                                    text="PRESS SPACE TO START")
            self.canvas.create_text(WIDTH // 2, 98, fill=faded, font="Courier 12",
                                    text="up = jump   down = duck")

        if self.over:
            self.canvas.create_text(WIDTH // 2, 70, fill=fg, font="Courier 28 bold",
                                    text="G A M E   O V E R")
            self.canvas.create_text(WIDTH // 2, 106, fill=faded, font="Courier 12",
                                    text="press space to restart")

    def frame(self):
        now = time.time()
        # dt is 1.0 at 60 fps, capped so a lag spike can't teleport the dino
        dt = min(2.5, (now - self.last) * 60)
        self.last = now

        # some systems send fake release events while a key is held
        if self.down and self.down_release > self.down_press:
            if now - self.down_release > 0.06:
                self.down = False

        if self.started and not self.over:
            self.update(dt, now)

        self.draw(now)
        self.root.after(FRAME_MS, self.frame)


def main():
    root = tk.Tk()
    root.resizable(False, False)
    Game(root)
    root.mainloop()


# TODO: reset-best key, sound


if __name__ == "__main__":
    main()