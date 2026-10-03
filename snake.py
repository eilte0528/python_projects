import math
import random
import time
import tkinter as tk

CELL = 24
COLS = 24
ROWS = 20
START_DELAY = 130
MIN_DELAY = 70
FRAME_MS = 25
BONUS_POINTS = 3
BONUS_SECONDS = 5
BONUS_CHANCE = 0.02

FRUITS = ["apple", "green apple", "orange", "cherry"]


class Palette:
    def __init__(self, a, b, head, outline, belly, spot):
        self.a = a
        self.b = b
        self.head = head
        self.outline = outline
        self.belly = belly
        self.spot = spot


ALIVE = Palette("#3fae49", "#35993f", "#47bb52", "#1b5524", "#a9e38e", "#1f6f2c")
DEAD = Palette("#8a9a8c", "#7d8c7f", "#93a395", "#3b463d", "#c9d3ca", "#566358")


def direction_for(key):
    if key == "up" or key == "w":
        return [0, -1]
    if key == "down" or key == "s":
        return [0, 1]
    if key == "left" or key == "a":
        return [-1, 0]
    if key == "right" or key == "d":
        return [1, 0]
    return None


def fruit_dark(kind):
    if kind == "apple":
        return "#6e0b08"
    if kind == "green apple":
        return "#3f6a10"
    if kind == "orange":
        return "#b04400"
    return "#4a0010"


def fruit_light(kind):
    if kind == "apple":
        return "#ff6a58"
    if kind == "green apple":
        return "#d2ee78"
    if kind == "orange":
        return "#ffb84d"
    return "#e8394f"


def mix(c1, c2, t):
    result = "#"
    for i in range(1, 7, 2):
        a = int(c1[i:i + 2], 16)
        b = int(c2[i:i + 2], 16)
        value = int(a + (b - a) * t)
        result += format(value, "02x")
    return result


class Snake:
    def __init__(self):
        self.body = [[5, 10], [4, 10], [3, 10]]
        self.old = self.body[:]
        self.direction = [1, 0]
        self.pending = [1, 0]
        self.grow = 0

    def head(self):
        return self.body[0]

    def turn(self, dx, dy):
        if dx == -self.direction[0] and dy == -self.direction[1]:
            return
        self.pending = [dx, dy]

    def move(self, food_pos, bonus_pos, wrap):
        self.old = self.body[:]
        self.direction = self.pending
        nx = self.head()[0] + self.direction[0]
        ny = self.head()[1] + self.direction[1]
        if wrap:
            nx = nx % COLS
            ny = ny % ROWS
        new_head = [nx, ny]
        self.body.insert(0, new_head)

        eaten = None
        if new_head == food_pos:
            eaten = "food"
            self.grow += 1
        elif new_head == bonus_pos:
            eaten = "bonus"
            self.grow += BONUS_POINTS

        if self.grow > 0:
            self.grow -= 1
        else:
            self.body.pop()
        return eaten

    def hit_wall(self):
        x = self.head()[0]
        y = self.head()[1]
        return x < 0 or x >= COLS or y < 0 or y >= ROWS

    def hit_self(self):
        return self.head() in self.body[1:]


class Food:
    def __init__(self, kinds):
        self.kinds = kinds
        self.kind = kinds[0]
        self.pos = None
        self.expires = None

    def place(self, taken):
        free = []
        for x in range(COLS):
            for y in range(ROWS):
                if [x, y] not in taken:
                    free.append([x, y])

        if len(free) == 0:
            self.pos = None
            return False
        self.pos = random.choice(free)
        self.kind = random.choice(self.kinds)
        return True

    def clear(self):
        self.pos = None
        self.expires = None


class Game:
    def __init__(self, root):
        self.root = root
        root.title("Snake")
        self.canvas = tk.Canvas(root, width=COLS * CELL, height=ROWS * CELL,
                                highlightthickness=0)
        self.canvas.pack()
        self.best = 0
        self.wrap = False

        self.draw_grass()
        root.bind("<Key>", self.on_key)
        self.reset()
        self.frame()

    def reset(self):
        self.snake = Snake()
        self.food = Food(FRUITS)
        self.bonus = Food(["mouse"])
        self.food.place(self.snake.body)
        self.score = 0
        self.over = False
        self.won = False
        self.last_step = time.time()

    def on_key(self, event):
        key = event.keysym.lower()
        if key == "m":
            self.wrap = not self.wrap
        elif self.over:
            if key == "space" or key == "r":
                self.reset()
        else:
            d = direction_for(key)
            if d is not None:
                self.snake.turn(d[0], d[1])

    def update_bonus(self):
        if self.bonus.pos is not None and time.time() > self.bonus.expires:
            self.bonus.clear()
        elif self.bonus.pos is None and random.random() < BONUS_CHANCE:
            if self.bonus.place(self.snake.body + [self.food.pos]):
                self.bonus.expires = time.time() + BONUS_SECONDS

    def step(self):
        eaten = self.snake.move(self.food.pos, self.bonus.pos, self.wrap)

        if self.snake.hit_self():
            self.over = True
            return
        if not self.wrap and self.snake.hit_wall():
            self.over = True
            return

        if eaten == "food":
            self.score += 1
            if not self.food.place(self.snake.body + [self.bonus.pos]):
                self.over = True
                self.won = True
        elif eaten == "bonus":
            self.score += BONUS_POINTS
            self.bonus.clear()

        self.best = max(self.best, self.score)
        self.update_bonus()

    def draw_grass(self):
        for x in range(COLS):
            for y in range(ROWS):
                color = "#9bcd60"
                if (x + y) % 2 == 0:
                    color = "#a5d66b"
                self.canvas.create_rectangle(
                    x * CELL, y * CELL, (x + 1) * CELL, (y + 1) * CELL,
                    fill=color, outline="", tags="bg")

    def center_x(self, pos):
        return (pos[0] + 0.5) * CELL

    def center_y(self, pos):
        return (pos[1] + 0.5) * CELL

    def shadow(self, cx, cy, rx, ry):
        self.canvas.create_oval(cx - rx, cy - ry, cx + rx, cy + ry,
                                fill="#7da84b", outline="", tags="fg")

    def ball(self, cx, cy, rx, ry, dark, light, steps):
        for k in range(steps):
            f = k / (steps - 1)
            sx = rx * (1 - f * 0.62)
            sy = ry * (1 - f * 0.62)
            ox = -rx * 0.3 * f
            oy = -ry * 0.3 * f
            outline = ""
            if k == 0:
                outline = dark
            self.canvas.create_oval(cx + ox - sx, cy + oy - sy,
                                    cx + ox + sx, cy + oy + sy,
                                    fill=mix(dark, light, f),
                                    outline=outline, tags="fg")

    def leaf(self, x, y, dx, dy, length):
        px = -dy
        py = dx
        w = length * 0.3
        mx = x + dx * length * 0.5
        my = y + dy * length * 0.5
        shape = [x, y,
                 mx + px * w, my + py * w,
                 x + dx * length, y + dy * length,
                 mx - px * w, my - py * w]
        self.canvas.create_polygon(shape, smooth=True, fill="#3aa04a",
                                   outline="#1f6b2a", tags="fg")
        self.canvas.create_line(x, y, x + dx * length * 0.9, y + dy * length * 0.9,
                                fill="#7bd48a", tags="fg")

    def highlight(self, cx, cy, r):
        self.canvas.create_oval(cx - r * 0.55, cy - r * 0.6,
                                cx - r * 0.15, cy - r * 0.3,
                                fill="#ffffff", outline="", tags="fg")

    def draw_apple(self, cx, cy, r, kind):
        dark = fruit_dark(kind)
        light = fruit_light(kind)
        self.ball(cx, cy + 1, r, r * 0.92, dark, light, 8)
        self.canvas.create_oval(cx - r * 0.32, cy - r * 0.82,
                                cx + r * 0.32, cy - r * 0.5,
                                fill=dark, outline="", tags="fg")
        self.canvas.create_line(cx, cy - r * 0.65, cx + 2, cy - r * 1.2,
                                fill="#5d3a1a", width=2, tags="fg")
        self.leaf(cx + 2, cy - r * 1.0, 0.93, -0.37, r * 0.9)
        self.highlight(cx, cy, r)

    def draw_orange(self, cx, cy, r, pos):
        dark = fruit_dark("orange")
        light = fruit_light("orange")
        self.ball(cx, cy + 1, r, r, dark, light, 8)
        rng = random.Random(pos[0] * 100 + pos[1])
        for i in range(14):
            ang = rng.uniform(0, 2 * math.pi)
            dist = rng.uniform(0.1, 0.8) * r
            x = cx + math.cos(ang) * dist
            y = cy + 1 + math.sin(ang) * dist
            self.canvas.create_oval(x - 0.8, y - 0.8, x + 0.8, y + 0.8,
                                    fill="#c25a00", outline="", tags="fg")
        self.canvas.create_oval(cx - 3, cy - r * 0.95, cx + 3, cy - r * 0.6,
                                fill="#3b8a3a", outline="#1f6b2a", tags="fg")
        self.leaf(cx + 1, cy - r * 0.85, 0.9, -0.43, r * 0.8)
        self.highlight(cx, cy, r)

    def draw_cherry(self, cx, cy, r):
        dark = fruit_dark("cherry")
        light = fruit_light("cherry")
        top_x = cx + 1
        top_y = cy - r
        for side in [-1, 1]:
            bx = cx + side * r * 0.5
            by = cy + r * 0.4
            self.canvas.create_line(bx, by - r * 0.4,
                                    (bx + top_x) / 2 + side * 2, (by + top_y) / 2,
                                    top_x, top_y,
                                    smooth=True, fill="#4f6b1f", width=2, tags="fg")
        for side in [-1, 1]:
            bx = cx + side * r * 0.5
            by = cy + r * 0.4
            self.ball(bx, by, r * 0.58, r * 0.58, dark, light, 8)
            self.highlight(bx, by, r * 0.58)
        self.leaf(top_x, top_y, 0.9, -0.1, r * 0.9)

    def draw_food(self, food):
        cx = self.center_x(food.pos)
        cy = self.center_y(food.pos)
        pulse = 1 + 0.04 * math.sin(time.time() * 4)
        r = CELL * 0.36 * pulse
        self.shadow(cx, cy + r * 0.95, r * 0.9, r * 0.28)

        if food.kind == "orange":
            self.draw_orange(cx, cy, r, food.pos)
        elif food.kind == "cherry":
            self.draw_cherry(cx, cy, r)
        else:
            self.draw_apple(cx, cy, r, food.kind)

    def draw_ear(self, ex, ey, u):
        self.ball(ex, ey, 3.4 * u, 3.4 * u, "#5e5e5e", "#b4b4b4", 5)
        self.canvas.create_oval(ex - 1.8 * u, ey - 1.8 * u,
                                ex + 1.8 * u, ey + 1.8 * u,
                                fill="#f4a8ba", outline="", tags="fg")

    def draw_mouse(self, pos):
        cx = self.center_x(pos)
        cy = self.center_y(pos)
        u = CELL / 30
        self.shadow(cx, cy + 9 * u, 11 * u, 3 * u)

        self.canvas.create_line(cx - 9 * u, cy + 3 * u, cx - 15 * u, cy + 5 * u,
                                cx - 14 * u, cy + 10 * u, cx - 18 * u, cy + 9 * u,
                                smooth=True, fill="#e3a3a8", width=2, tags="fg")

        self.ball(cx - 1 * u, cy + 1 * u, 9 * u, 6.5 * u, "#5e5e5e", "#c8c8c8", 8)

        self.draw_ear(cx + 2 * u, cy - 6 * u, u)
        self.draw_ear(cx + 7 * u, cy - 7 * u, u)

        self.ball(cx + 7 * u, cy - 1 * u, 5.4 * u, 4.4 * u, "#5e5e5e", "#cfcfcf", 8)

        self.canvas.create_oval(cx + 10.5 * u, cy - 2.2 * u,
                                cx + 13.5 * u, cy + 0.8 * u,
                                fill="#f08aa4", outline="#9a4a5e", tags="fg")
        self.canvas.create_oval(cx + 7.4 * u, cy - 3.8 * u,
                                cx + 9.8 * u, cy - 1.4 * u,
                                fill="black", outline="", tags="fg")
        self.canvas.create_oval(cx + 8.1 * u, cy - 3.5 * u,
                                cx + 8.9 * u, cy - 2.7 * u,
                                fill="white", outline="", tags="fg")

        for dy in [-2, 1.5]:
            self.canvas.create_line(cx + 10 * u, cy + dy * u * 0.4,
                                    cx + 16 * u, cy + dy * u * 1.8,
                                    fill="#f2f2f2", tags="fg")

        for fx in [cx - 5 * u, cx + 3 * u]:
            self.canvas.create_oval(fx - 2.4 * u, cy + 6 * u,
                                    fx + 2.4 * u, cy + 8.6 * u,
                                    fill="#f0a0b0", outline="#9a4a5e", tags="fg")

    def points(self, t):
        pts = []
        old = self.snake.old
        for i in range(len(self.snake.body)):
            cell = self.snake.body[i]
            o = old[min(i, len(old) - 1)]
            if abs(cell[0] - o[0]) > 1 or abs(cell[1] - o[1]) > 1:
                o = cell
            gx = o[0] + (cell[0] - o[0]) * t
            gy = o[1] + (cell[1] - o[1]) * t
            pts.append([(gx + 0.5) * CELL, (gy + 0.5) * CELL])
        return pts

    def draw_body(self, pts, colors):
        n = len(pts)
        widths = []
        for i in range(n):
            taper = min(1.0, (n - 1 - i) / 6)
            widths.append(CELL * (0.3 + 0.5 * taper))

        for i in range(n - 1, 0, -1):
            x1 = pts[i][0]
            y1 = pts[i][1]
            x2 = pts[i - 1][0]
            y2 = pts[i - 1][1]
            if math.hypot(x2 - x1, y2 - y1) > CELL * 1.6:
                continue
            self.canvas.create_line(x1, y1, x2, y2, width=widths[i] + 4,
                                    fill=colors.outline, capstyle="round", tags="fg")

        for i in range(n - 1, 0, -1):
            x1 = pts[i][0]
            y1 = pts[i][1]
            x2 = pts[i - 1][0]
            y2 = pts[i - 1][1]
            if math.hypot(x2 - x1, y2 - y1) > CELL * 1.6:
                continue
            fill = colors.b
            if i % 2 == 1:
                fill = colors.a
            self.canvas.create_line(x1, y1, x2, y2, width=widths[i],
                                    fill=fill, capstyle="round", tags="fg")
            self.canvas.create_line(x1, y1, x2, y2, width=widths[i] * 0.3,
                                    fill=colors.belly, capstyle="round", tags="fg")

        for i in range(1, n - 1, 3):
            x = pts[i][0]
            y = pts[i][1]
            r = widths[i] * 0.2
            self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                    fill=colors.spot, outline="", tags="fg")

    def draw_head(self, pos, colors, dead):
        dx = self.snake.direction[0]
        dy = self.snake.direction[1]
        px = -dy
        py = dx
        a = CELL * 0.62
        b = CELL * 0.5
        cx = pos[0] + dx * CELL * 0.12
        cy = pos[1] + dy * CELL * 0.12

        shape = []
        for k in range(20):
            ang = 2 * math.pi * k / 20
            u = math.cos(ang) * a
            v = math.sin(ang) * b
            shape.append(cx + dx * u + px * v)
            shape.append(cy + dy * u + py * v)
        self.canvas.create_polygon(shape, fill=colors.head, outline=colors.outline,
                                   width=2, smooth=True, tags="fg")

        if not dead and int(time.time() * 3) % 3 == 0:
            bx = cx + dx * a
            by = cy + dy * a
            tx = bx + dx * CELL * 0.5
            ty = by + dy * CELL * 0.5
            self.canvas.create_line(bx, by, tx, ty, fill="#e5195e", width=2, tags="fg")
            for side in [-1, 1]:
                fx = tx + dx * CELL * 0.25 + px * CELL * 0.18 * side
                fy = ty + dy * CELL * 0.25 + py * CELL * 0.18 * side
                self.canvas.create_line(tx, ty, fx, fy, fill="#e5195e", width=2, tags="fg")

        for side in [-1, 1]:
            ex = cx + dx * a * 0.3 + px * b * 0.55 * side
            ey = cy + dy * a * 0.3 + py * b * 0.55 * side
            if dead:
                s = CELL * 0.12
                self.canvas.create_line(ex - s, ey - s, ex + s, ey + s,
                                        fill="black", width=2, tags="fg")
                self.canvas.create_line(ex - s, ey + s, ex + s, ey - s,
                                        fill="black", width=2, tags="fg")
            else:
                r = CELL * 0.17
                self.canvas.create_oval(ex - r, ey - r, ex + r, ey + r,
                                        fill="white", outline=colors.outline, tags="fg")
                q = CELL * 0.08
                qx = ex + dx * 2
                qy = ey + dy * 2
                self.canvas.create_oval(qx - q, qy - q, qx + q, qy + q,
                                        fill="black", outline="", tags="fg")

    def draw(self, t):
        self.canvas.delete("fg")

        if self.food.pos is not None:
            self.draw_food(self.food)

        if self.bonus.pos is not None:
            left = self.bonus.expires - time.time()
            blink_off = left < 2 and int(left * 4) % 2 == 0
            if not blink_off:
                self.draw_mouse(self.bonus.pos)

        dead = self.over and not self.won
        colors = ALIVE
        if dead:
            colors = DEAD
        pts = self.points(t)
        self.draw_body(pts, colors)
        self.draw_head(pts[0], colors, dead)

        mode = "walls"
        if self.wrap:
            mode = "wrap"
        self.canvas.create_text(
            8, 8, anchor="nw", fill="#1b3a14", font="Courier 12 bold", tags="fg",
            text="score " + str(self.score) + "   best " + str(self.best)
                 + "   mode " + mode + " (m)")

        if self.over:
            w = COLS * CELL
            h = ROWS * CELL
            self.canvas.create_rectangle(0, 0, w, h, fill="black",
                                         stipple="gray50", outline="", tags="fg")
            title = "game over"
            if self.won:
                title = "you win"
            self.canvas.create_text(w // 2, h // 2 - 14, fill="white",
                                    font="Courier 28 bold", text=title, tags="fg")
            self.canvas.create_text(w // 2, h // 2 + 22, fill="#dddddd",
                                    font="Courier 12", text="space or r to restart",
                                    tags="fg")

    def frame(self):
        now = time.time()
        delay = max(MIN_DELAY, START_DELAY - self.score * 3) / 1000

        if not self.over and now - self.last_step >= delay:
            self.step()
            self.last_step = now

        t = 1.0
        if not self.over:
            t = min(1.0, (now - self.last_step) / delay)
        self.draw(t)
        self.root.after(FRAME_MS, self.frame)


def main():
    root = tk.Tk()
    root.resizable(False, False)
    Game(root)
    root.mainloop()


if __name__ == "__main__":
    main()