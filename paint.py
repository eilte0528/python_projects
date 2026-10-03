import math
import random
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox

CANVAS_W = 820       # size of the window onto the page, not the size of the page
CANVAS_H = 520
SWATCH = 32          # size of each palette square, in pixels
GRID = 40            # distance between the faint guide lines

HEADER = "paint-v1"  # first line of every project file

TOOLS = ["hand", "pen", "eraser", "spray", "line", "rectangle", "oval", "fill", "picker"]
KINDS = ["pen", "eraser", "spray", "line", "rectangle", "oval", "fill"]
NEEDS_TWO_POINTS = ["line", "rectangle", "oval"]

# chalk colors: bright ones read well on a dark board
CHALK = [
    "white", "#cccccc", "#888888", "#444444",
    "#ff6b6b", "#ffa94d", "#ffe066", "#69db7c",
    "#38d9a9", "#4dabf7", "#748ffc", "#da77f2",
    "#f783ac", "#c08a5a", "#ffd8a8", "#d8f5a2",
]

# marker colors for the whiteboard
INK = [
    "black", "#555555", "#999999", "white",
    "#e74c3c", "#e67e22", "#f1c40f", "#2ecc71",
    "#1abc9c", "#3498db", "#2c3e50", "#9b59b6",
    "#e84393", "#8e5a2b", "#fd9644", "#a5d66b",
]


# ---------- shapes and saving ----------

def is_number(text):
    # True for "12" and "-12". Checking first means we never crash on bad input.
    if text.startswith("-"):
        text = text[1:]
    return text.isdigit()


class Shape:
    # One thing the user drew (a stroke, a line, a fill...).
    # items holds the canvas ids so undo can hide them,
    # points holds the page coordinates so we can redraw or save it later.
    def __init__(self, kind, color, size, filled=False):
        self.kind = kind
        self.color = color
        self.size = size
        self.filled = filled
        self.points = []
        self.items = []
        self.group = []   # only used by a "clear" shape: the shapes it wiped

    def to_line(self):
        # one shape becomes one line of text:
        # kind|color|size|filled|x,y x,y x,y
        filled = "0"
        if self.filled:
            filled = "1"

        coords = []
        for p in self.points:
            coords.append(str(p[0]) + "," + str(p[1]))

        parts = [self.kind, self.color, str(self.size), filled, " ".join(coords)]
        return "|".join(parts)


def load_shape(line):
    # Turns a line of text back into a Shape.
    # Returns None if the line is damaged, so the caller can skip it.
    parts = line.split("|")
    if len(parts) != 5:
        return None
    if parts[0] not in KINDS:
        return None
    if not is_number(parts[2]):
        return None

    shape = Shape(parts[0], parts[1], int(parts[2]), parts[3] == "1")

    if parts[4] != "":
        for pair in parts[4].split(" "):
            xy = pair.split(",")
            if len(xy) != 2 or not is_number(xy[0]) or not is_number(xy[1]):
                return None
            shape.points.append([int(xy[0]), int(xy[1])])

    if len(shape.points) == 0:
        return None
    if shape.kind in NEEDS_TWO_POINTS and len(shape.points) < 2:
        return None
    return shape


class Raster:
    # A grid of color names, one per pixel, covering ONE window-sized piece
    # of the infinite page. ox and oy say where that piece starts on the page.
    # The canvas can't tell us what color a pixel is, so we keep our own copy
    # for the fill and picker tools.
    def __init__(self, width, height, paper):
        self.width = width
        self.height = height
        self.paper = paper
        self.ox = 0
        self.oy = 0
        self.grid = []
        self.clear()

    def set_origin(self, ox, oy):
        self.ox = ox
        self.oy = oy

    def clear(self):
        self.grid = []
        for y in range(self.height):
            self.grid.append([self.paper] * self.width)

    def inside(self, x, y):
        return x >= 0 and x < self.width and y >= 0 and y < self.height

    def span(self, y, left, right, color):
        # paint one horizontal run of pixels, clipped to the grid
        if y < 0 or y >= self.height:
            return
        left = max(0, left)
        right = min(self.width - 1, right)
        if left <= right:
            self.grid[y][left:right + 1] = [color] * (right - left + 1)

    def stamp(self, x, y, r, color):
        # a filled circle, built one row at a time
        x = int(x)
        y = int(y)
        for dy in range(-int(r), int(r) + 1):
            half = int(math.sqrt(r * r - dy * dy))
            self.span(y + dy, x - half, x + half, color)

    def line(self, x1, y1, x2, y2, size, color):
        # a thick line is a row of circles stamped along it
        r = size / 2
        dist = max(abs(x2 - x1), abs(y2 - y1))
        step = max(1, int(r / 2))
        count = max(1, int(dist / step))
        for i in range(count + 1):
            t = i / count
            self.stamp(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, r, color)

    def rect(self, x1, y1, x2, y2, size, color, filled):
        left = int(min(x1, x2))
        right = int(max(x1, x2))
        top = int(min(y1, y2))
        bottom = int(max(y1, y2))
        if filled:
            for y in range(top, bottom + 1):
                self.span(y, left, right, color)
        self.line(left, top, right, top, size, color)
        self.line(right, top, right, bottom, size, color)
        self.line(right, bottom, left, bottom, size, color)
        self.line(left, bottom, left, top, size, color)

    def oval(self, x1, y1, x2, y2, size, color, filled):
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        rx = max(abs(x2 - x1) / 2, 0.5)
        ry = max(abs(y2 - y1) / 2, 0.5)
        if filled:
            for y in range(int(cy - ry), int(cy + ry) + 1):
                t = (y - cy) / ry
                if abs(t) <= 1:
                    half = rx * math.sqrt(1 - t * t)
                    self.span(y, int(cx - half), int(cx + half), color)
        # outline: stamp circles around the edge
        count = int(2 * (rx + ry)) + 8
        for i in range(count):
            a = 2 * math.pi * i / count
            self.stamp(cx + rx * math.cos(a), cy + ry * math.sin(a), size / 2, color)

    def flood(self, x, y, color):
        # Scanline flood fill. Fills a whole row-run at a time, then looks at
        # the rows above and below for more of the same color.
        # x and y are grid coordinates. Returns the runs it filled as
        # [left, y, right] lists, also in grid coordinates.
        spans = []
        if not self.inside(x, y):
            return spans

        target = self.grid[y][x]
        if target == color:
            return spans

        stack = [[x, y]]
        while len(stack) > 0:
            seed = stack.pop()
            sx = seed[0]
            sy = seed[1]
            row = self.grid[sy]
            if row[sx] != target:
                continue  # already filled by an earlier run

            left = sx
            while left > 0 and row[left - 1] == target:
                left -= 1
            right = sx
            while right < self.width - 1 and row[right + 1] == target:
                right += 1

            row[left:right + 1] = [color] * (right - left + 1)
            spans.append([left, sy, right])

            for ny in [sy - 1, sy + 1]:
                if ny < 0 or ny >= self.height:
                    continue
                inside = False
                for i in range(left, right + 1):
                    if self.grid[ny][i] == target:
                        if not inside:
                            stack.append([i, ny])  # one seed per run
                            inside = True
                    else:
                        inside = False
        return spans

    def draw_shape(self, shape):
        if len(shape.points) == 0:
            return  # also covers "clear" shapes, which draw nothing

        # move the shape from page coordinates into this grid's coordinates
        points = []
        for p in shape.points:
            points.append([p[0] - self.ox, p[1] - self.oy])

        kind = shape.kind
        color = shape.color
        size = shape.size

        if kind == "pen" or kind == "eraser":
            self.stamp(points[0][0], points[0][1], size / 2, color)
            for i in range(1, len(points)):
                self.line(points[i - 1][0], points[i - 1][1],
                          points[i][0], points[i][1], size, color)
        elif kind == "spray":
            for p in points:
                self.stamp(p[0], p[1], 0.5, color)
        elif kind == "fill":
            self.flood(points[0][0], points[0][1], color)
        elif len(points) >= 2:
            a = points[0]
            b = points[1]
            if kind == "line":
                self.line(a[0], a[1], b[0], b[1], size, color)
            elif kind == "rectangle":
                self.rect(a[0], a[1], b[0], b[1], size, color, shape.filled)
            elif kind == "oval":
                self.oval(a[0], a[1], b[0], b[1], size, color, shape.filled)

    def rebuild(self, shapes):
        # start from blank paper and replay everything that is still visible
        self.clear()
        for shape in shapes:
            self.draw_shape(shape)


# ---------- board settings ----------
# Each board has a paper color, a default pen color, a palette and a grid color.
# These are functions (not variables) so there is one place to add a new board.

def paper_for(board):
    if board == "blackboard":
        return "#161616"
    return "white"


def ink_for(board):
    if board == "blackboard":
        return "white"
    return "black"


def palette_for(board):
    if board == "blackboard":
        return CHALK
    return INK


def grid_for(board):
    # just a little different from the paper, so it guides without distracting
    if board == "blackboard":
        return "#262626"
    return "#ebebeb"


def other_board(board):
    if board == "blackboard":
        return "whiteboard"
    return "blackboard"


def remap(color, old_board, new_board):
    # Paper turns into the new paper and the default ink into the new ink,
    # so a white chalk drawing becomes a black marker drawing.
    # Every other color is left alone.
    if color == paper_for(old_board):
        return paper_for(new_board)
    if color == ink_for(old_board):
        return ink_for(new_board)
    return color


# ---------- the app ----------

class Paint:
    def __init__(self, root):
        self.root = root
        root.title("Paint")
        root.configure(bg="#2b2b2b")

        # the board decides the paper, the starting pen color and the palette
        self.board = "blackboard"
        self.paper = paper_for(self.board)
        self.colors = palette_for(self.board)
        self.color = ink_for(self.board)

        self.tool = tk.StringVar(value="pen")
        self.size = tk.IntVar(value=6)
        self.fill = tk.IntVar(value=0)

        self.done = []       # shapes currently on the page, oldest first
        self.undone = []     # shapes that were undone, waiting for redo
        self.current = None  # the shape being drawn right now
        self.panning = False # True while the view is being dragged

        self.saved = True    # a blank page has nothing to lose

        # ask before the window closes, not just before New
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        # our own pixel grid, used by the fill and picker tools
        self.raster = Raster(CANVAS_W, CANVAS_H, self.paper)

        self.start_x = 0
        self.start_y = 0
        self.last_x = 0
        self.last_y = 0

        self.build_toolbar()
        self.build_palette()
        self.build_actions()
        self.build_canvas()
        self.build_status()
        self.bind_keys()

    # ---------- building the window ----------

    def build_toolbar(self):
        bar = tk.Frame(self.root, bg="#2b2b2b")
        bar.pack(fill="x", padx=8, pady=(8, 2))

        # one radio button per tool; indicatoron=False makes them look like buttons
        for name in TOOLS:
            tk.Radiobutton(bar, text=name, variable=self.tool, value=name,
                           indicatoron=False, width=8, selectcolor="#4da3ff",
                           command=self.show_status).pack(side="left", padx=1)

        tk.Scale(bar, from_=1, to=40, orient="horizontal", variable=self.size,
                 length=110, label="size", bg="#2b2b2b", fg="white",
                 highlightthickness=0).pack(side="left", padx=10)

        tk.Checkbutton(bar, text="fill shapes", variable=self.fill,
                       bg="#2b2b2b", fg="white", selectcolor="#2b2b2b",
                       activebackground="#2b2b2b",
                       activeforeground="white").pack(side="left")

    def build_palette(self):
        row = tk.Frame(self.root, bg="#2b2b2b")
        row.pack(fill="x", padx=8, pady=2)

        # box that shows the color we are painting with
        self.color_box = tk.Label(row, width=4, bg=self.color, relief="sunken")
        self.color_box.pack(side="left", padx=(0, 8))

        # both palettes have 16 colors, so the width never changes
        self.palette = tk.Canvas(row, width=SWATCH * len(self.colors), height=SWATCH,
                                 bg="#2b2b2b", highlightthickness=0)
        self.palette.pack(side="left")
        self.palette.bind("<Button-1>", self.pick_swatch)
        self.draw_palette()

        tk.Button(row, text="Custom...", command=self.pick_custom).pack(side="left", padx=8)

    def build_actions(self):
        row = tk.Frame(self.root, bg="#2b2b2b")
        row.pack(fill="x", padx=8, pady=2)

        tk.Button(row, text="Undo", command=self.undo).pack(side="left", padx=2)
        tk.Button(row, text="Redo", command=self.redo).pack(side="left", padx=2)
        tk.Button(row, text="New", command=self.new_drawing).pack(side="left", padx=2)
        tk.Button(row, text="Clear", command=self.clear_page).pack(side="left", padx=2)
        tk.Button(row, text="Home", command=self.view_home).pack(side="left", padx=2)
        tk.Button(row, text="Open", command=self.open_file).pack(side="left", padx=(16, 2))
        tk.Button(row, text="Save", command=self.save).pack(side="left", padx=2)
        tk.Button(row, text="Export .ps", command=self.export).pack(side="left", padx=2)

        # keep a reference so the text can change when the board does
        self.board_button = tk.Button(row, text="Board: " + self.board,
                                      width=18, command=self.toggle_board)
        self.board_button.pack(side="right", padx=2)

    def build_canvas(self):
        # confine=False lets the view slide past the edge of the drawn items,
        # which is what makes the page infinite
        self.canvas = tk.Canvas(self.root, width=CANVAS_W, height=CANVAS_H,
                                bg=self.paper, highlightthickness=0,
                                cursor="crosshair", confine=False)
        self.canvas.pack(padx=8, pady=4)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Motion>", self.on_move)

        # right or middle button drags the view with any tool
        # (the middle button is number 2 on most systems, the right one is 2 on a Mac)
        for number in ["2", "3"]:
            self.canvas.bind("<ButtonPress-" + number + ">", self.start_pan)
            self.canvas.bind("<B" + number + "-Motion>", self.on_drag)
            self.canvas.bind("<ButtonRelease-" + number + ">", self.on_release)

        self.draw_grid()

    def build_status(self):
        self.status = tk.Label(self.root, text="", anchor="w", bg="#2b2b2b",
                               fg="#aaaaaa", font="Courier 11")
        self.status.pack(fill="x", padx=8, pady=(0, 8))
        self.show_status()

    def bind_keys(self):
        self.root.bind("<Control-z>", self.undo)
        self.root.bind("<Control-y>", self.redo)
        self.root.bind("<Control-s>", self.save)
        self.root.bind("<Control-o>", self.open_file)
        self.root.bind("<Control-b>", self.toggle_board)
        self.root.bind("<Control-n>", self.new_drawing)
        self.root.bind("<Control-l>", self.clear_page)
        self.root.bind("<Home>", self.view_home)

    # ---------- the infinite page ----------

    def world(self, event):
        # A mouse position is relative to the window. The page may be scrolled,
        # so convert it to a position ON the page. Whole numbers only, because
        # the save file stores integers.
        x = int(self.canvas.canvasx(event.x))
        y = int(self.canvas.canvasy(event.y))
        return [x, y]

    def start_pan(self, event):
        # remember where the drag began; scan_dragto measures from here
        self.canvas.scan_mark(event.x, event.y)
        self.panning = True

    def do_pan(self, event):
        # gain=1 makes the page follow the mouse exactly
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.draw_grid()
        self.show_view()

    def view_home(self, event=None):
        # slide the view back so the page point (0, 0) is in the top-left corner
        left = int(self.canvas.canvasx(0))
        top = int(self.canvas.canvasy(0))
        self.canvas.scan_mark(0, 0)
        self.canvas.scan_dragto(left, top, gain=1)
        self.draw_grid()
        self.status.config(text="back to the start of the page")

    def draw_grid(self):
        # Faint guide lines so you can see the page moving. They only cover the
        # part you can see, so the cost stays the same however far you pan.
        self.canvas.delete("grid")
        left = int(self.canvas.canvasx(0))
        top = int(self.canvas.canvasy(0))
        color = grid_for(self.board)

        # start on the last grid line at or before the edge of the view
        for x in range(left - left % GRID, left + CANVAS_W + GRID, GRID):
            self.canvas.create_line(x, top, x, top + CANVAS_H, fill=color, tags="grid")
        for y in range(top - top % GRID, top + CANVAS_H + GRID, GRID):
            self.canvas.create_line(left, y, left + CANVAS_W, y, fill=color, tags="grid")

        # the guides must never cover a drawing
        self.canvas.tag_lower("grid")

    # ---------- unsaved changes ----------

    def mark_dirty(self):
        # call this whenever the drawing changes
        self.saved = False
        self.update_title()

    def update_title(self):
        title = "Paint"
        if not self.saved:
            title += " *"
        self.root.title(title)

    def confirm_discard(self, action):
        # True means "go ahead". Nothing unsaved means we don't even ask.
        if self.saved:
            return True

        # askyesnocancel gives True (Yes), False (No) or None (Cancel)
        answer = messagebox.askyesnocancel(
            "Unsaved changes", "Save your changes before you " + action + "?")

        if answer is None:
            return False        # Cancel: stay in the program
        if answer:
            return self.save()  # Yes: continue only if the file was really written
        return True             # No: throw the changes away

    def on_close(self):
        if self.confirm_discard("quit"):
            self.root.destroy()

    def new_drawing(self, event=None):
        if not self.confirm_discard("start a new drawing"):
            return
        self.clear()
        self.view_home()
        self.status.config(text="new drawing")

    # ---------- board switching ----------

    def toggle_board(self, event=None):
        self.set_board(other_board(self.board))

    def set_board(self, new_board):
        old_board = self.board
        if new_board == old_board:
            return

        # recolor the saved shapes: old paper -> new paper, old ink -> new ink
        for shape in self.done:
            shape.color = remap(shape.color, old_board, new_board)

        # undone shapes still have the old colors, so redo history is dropped
        self.undone = []

        self.board = new_board
        self.paper = paper_for(new_board)
        self.colors = palette_for(new_board)
        self.raster.paper = self.paper
        self.canvas.config(bg=self.paper)
        self.board_button.config(text="Board: " + new_board)

        # set_color also redraws the palette, which now uses the new colors
        self.set_color(remap(self.color, old_board, new_board))

        self.replay()
        self.mark_dirty()
        self.status.config(text="switched to " + new_board)

    def replay(self):
        # Wipes the canvas and draws every shape in self.done again, in order.
        # Used after a board switch and after opening a file.
        shapes = self.done
        self.canvas.delete("all")
        self.done = []

        for shape in shapes:
            if shape.kind == "clear":
                continue   # the canvas was just wiped, so there is nothing left to restore
            shape.items = []  # the old canvas ids are gone
            if shape.kind == "fill":
                # a fill is replayed by flooding again on what is already drawn
                shape = self.apply_fill(shape.points[0][0], shape.points[0][1], shape.color)
                if shape is None:
                    continue
            else:
                self.draw_shape(shape)
            self.done.append(shape)

        # delete("all") removed the guide lines too
        self.draw_grid()

    # ---------- colors ----------

    def draw_palette(self):
        self.palette.delete("all")
        for i in range(len(self.colors)):
            x = i * SWATCH
            # thick white border marks the selected color
            border = "#2b2b2b"
            width = 1
            if self.colors[i] == self.color:
                border = "white"
                width = 3
            self.palette.create_rectangle(x + 2, 2, x + SWATCH - 2, SWATCH - 2,
                                          fill=self.colors[i], outline=border, width=width)

    def set_color(self, color):
        self.color = color
        self.color_box.config(bg=color)
        self.draw_palette()

    def pick_swatch(self, event):
        index = event.x // SWATCH
        if index < len(self.colors):
            self.set_color(self.colors[index])

    def pick_custom(self):
        result = colorchooser.askcolor(color=self.color)
        # result looks like (rgb, "#rrggbb"); the second part is None if cancelled
        if result[1] is not None:
            self.set_color(result[1])

    def pick_from_canvas(self, x, y):
        # Center our pixel grid on the click, replay the visible shapes onto it,
        # then read the pixel in the middle.
        middle_x = CANVAS_W // 2
        middle_y = CANVAS_H // 2
        self.raster.set_origin(x - middle_x, y - middle_y)
        self.raster.rebuild(self.done)
        color = self.raster.grid[middle_y][middle_x]
        self.set_color(color)
        self.status.config(text="picked " + color)

    # ---------- mouse handling ----------

    def on_press(self, event):
        tool = self.tool.get()

        # the hand tool only moves the view, it draws nothing
        if tool == "hand":
            self.start_pan(event)
            return

        pos = self.world(event)
        x = pos[0]
        y = pos[1]

        # fill and picker are single clicks, not drags, so they return early
        if tool == "fill":
            self.fill_at(x, y)
            return
        if tool == "picker":
            self.pick_from_canvas(x, y)
            return

        color = self.color
        size = self.size.get()
        if tool == "eraser":
            color = self.paper
            size = size * 3  # an eraser feels better when it is wide

        self.current = Shape(tool, color, size, self.fill.get() == 1)
        self.start_x = x
        self.start_y = y
        self.last_x = x
        self.last_y = y

        # drawing something new throws away the redo history
        self.forget_redo()

        if tool == "pen" or tool == "eraser":
            self.current.points.append([x, y])
            self.dab(x, y)  # so a single click leaves a dot
        elif tool == "spray":
            self.spray(x, y)

    def on_drag(self, event):
        # dragging with the hand tool or the right button moves the view
        if self.panning:
            self.do_pan(event)
            return

        if self.current is None:
            return

        pos = self.world(event)
        x = pos[0]
        y = pos[1]
        tool = self.current.kind

        if tool == "pen" or tool == "eraser":
            item = self.canvas.create_line(self.last_x, self.last_y, x, y,
                                           fill=self.current.color,
                                           width=self.current.size,
                                           capstyle="round")
            self.current.items.append(item)
            self.current.points.append([x, y])
            self.last_x = x
            self.last_y = y
        elif tool == "spray":
            self.spray(x, y)
        else:
            self.preview_shape(x, y)

    def on_release(self, event):
        if self.panning:
            self.panning = False
            return
        if self.current is None:
            return
        # the stroke is finished, so it becomes undoable
        if len(self.current.items) > 0:
            self.done.append(self.current)
            self.mark_dirty()
        self.current = None

    def on_move(self, event):
        pos = self.world(event)
        self.show_status(pos[0], pos[1])

    # ---------- drawing helpers ----------

    def dab(self, x, y):
        r = self.current.size / 2
        item = self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                       fill=self.current.color, outline="")
        self.current.items.append(item)

    def spray(self, x, y):
        reach = self.current.size * 2
        for i in range(12):
            dx = random.randint(-reach, reach)
            dy = random.randint(-reach, reach)
            # keep only the dots inside the circle, otherwise the spray is a square
            if dx * dx + dy * dy <= reach * reach:
                item = self.canvas.create_oval(x + dx, y + dy, x + dx + 1, y + dy + 1,
                                               fill=self.current.color, outline="")
                self.current.items.append(item)
                self.current.points.append([x + dx, y + dy])

    def preview_shape(self, x, y):
        # a shape is redrawn from scratch on every drag so it follows the mouse
        for item in self.current.items:
            self.canvas.delete(item)
        self.current.items = []
        self.current.points = [[self.start_x, self.start_y], [x, y]]

        tool = self.current.kind
        color = self.current.color
        width = self.current.size

        fill = ""
        if self.current.filled:
            fill = color

        if tool == "line":
            item = self.canvas.create_line(self.start_x, self.start_y, x, y,
                                           fill=color, width=width, capstyle="round")
        elif tool == "rectangle":
            item = self.canvas.create_rectangle(self.start_x, self.start_y, x, y,
                                                outline=color, fill=fill, width=width)
        else:
            item = self.canvas.create_oval(self.start_x, self.start_y, x, y,
                                           outline=color, fill=fill, width=width)
        self.current.items.append(item)

    def draw_shape(self, shape):
        # Draws a finished shape onto the canvas. Used by replay(), where
        # there is no mouse to draw it live.
        kind = shape.kind
        color = shape.color
        size = shape.size
        points = shape.points

        if kind == "pen" or kind == "eraser":
            r = size / 2
            item = self.canvas.create_oval(points[0][0] - r, points[0][1] - r,
                                           points[0][0] + r, points[0][1] + r,
                                           fill=color, outline="")
            shape.items.append(item)
            for i in range(1, len(points)):
                item = self.canvas.create_line(points[i - 1][0], points[i - 1][1],
                                               points[i][0], points[i][1],
                                               fill=color, width=size, capstyle="round")
                shape.items.append(item)
        elif kind == "spray":
            for p in points:
                item = self.canvas.create_oval(p[0], p[1], p[0] + 1, p[1] + 1,
                                               fill=color, outline="")
                shape.items.append(item)
        else:
            fill = ""
            if shape.filled:
                fill = color
            a = points[0]
            b = points[1]
            if kind == "line":
                item = self.canvas.create_line(a[0], a[1], b[0], b[1],
                                               fill=color, width=size, capstyle="round")
            elif kind == "rectangle":
                item = self.canvas.create_rectangle(a[0], a[1], b[0], b[1],
                                                    outline=color, fill=fill, width=size)
            else:
                item = self.canvas.create_oval(a[0], a[1], b[0], b[1],
                                               outline=color, fill=fill, width=size)
            shape.items.append(item)

    # ---------- flood fill ----------

    def apply_fill(self, x, y, color):
        # Floods from the page point (x, y) and draws the result. Returns the
        # new Shape, or None if there was nothing to fill.
        # The page has no edges, so a fill can only look at a window-sized box
        # centered on the click. The box depends only on the click, which means
        # replaying the fill later gives the same result.
        middle_x = CANVAS_W // 2
        middle_y = CANVAS_H // 2
        self.raster.set_origin(x - middle_x, y - middle_y)
        self.raster.rebuild(self.done)
        spans = self.raster.flood(middle_x, middle_y, color)
        if len(spans) == 0:
            return None

        # draw each filled run as a 1 pixel tall rectangle, back in page coordinates
        ox = self.raster.ox
        oy = self.raster.oy
        shape = Shape("fill", color, 1)
        shape.points.append([x, y])  # enough to redo the fill later
        for span in spans:
            item = self.canvas.create_rectangle(span[0] + ox, span[1] + oy,
                                                span[2] + 1 + ox, span[1] + 1 + oy,
                                                fill=color, outline="")
            shape.items.append(item)
        return shape

    def fill_at(self, x, y):
        self.forget_redo()
        shape = self.apply_fill(x, y, self.color)
        if shape is None:
            self.status.config(text="nothing to fill there")
            return
        self.done.append(shape)
        self.mark_dirty()

    # ---------- undo, redo, clear ----------

    def set_state(self, shape, state):
        # state is "hidden" or "normal"
        for item in shape.items:
            self.canvas.itemconfigure(item, state=state)

    def page_is_empty(self):
        # a clear marker draws nothing, so it doesn't count as something on the page
        for shape in self.done:
            if shape.kind != "clear":
                return False
        return True

    def clear_page(self, event=None):
        if self.page_is_empty():
            self.status.config(text="the page is already empty")
            return

        self.forget_redo()

        # one "clear" shape stands in for everything that was on the page
        marker = Shape("clear", self.color, 1)
        marker.group = self.done

        for shape in self.done:
            self.set_state(shape, "hidden")

        self.done = [marker]
        self.mark_dirty()
        self.status.config(text="page cleared (ctrl+z to bring it back)")

    def undo(self, event=None):
        if len(self.done) == 0:
            return
        shape = self.done.pop()

        if shape.kind == "clear":
            # show everything the clear hid, and put it back on the page
            for old in shape.group:
                self.set_state(old, "normal")
            self.done = shape.group[:]
        else:
            # hiding is cheaper than deleting, and lets redo bring it back
            self.set_state(shape, "hidden")

        self.undone.append(shape)
        self.mark_dirty()

    def redo(self, event=None):
        if len(self.undone) == 0:
            return
        shape = self.undone.pop()

        if shape.kind == "clear":
            # wipe again: hide whatever is on the page right now
            for old in self.done:
                self.set_state(old, "hidden")
            shape.group = self.done
            self.done = [shape]
        else:
            self.set_state(shape, "normal")
            self.done.append(shape)

        self.mark_dirty()

    def forget_redo(self):
        # the hidden shapes can never come back now, so remove them for real
        for shape in self.undone:
            for item in shape.items:
                self.canvas.delete(item)
        self.undone = []

    def clear(self):
        # the hard wipe used by New: deletes everything, no undo
        self.canvas.delete("all")
        self.draw_grid()    # delete("all") removed the guide lines too
        self.done = []
        self.undone = []
        self.saved = True   # a blank page has nothing to lose
        self.update_title()

    # ---------- files ----------

    def save(self, event=None):
        # line 1 is the header, line 2 is the board, then one line per shape
        # returns True if a file was written, False if the user cancelled
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path == "":
            return False  # user cancelled

        lines = [HEADER, "board|" + self.board]
        for shape in self.done:
            if shape.kind != "clear":   # a clear has no points, so it isn't saved
                lines.append(shape.to_line())

        with open(path, "w") as f:
            f.write("\n".join(lines))
        self.saved = True
        self.update_title()
        self.status.config(text="saved " + str(len(lines) - 2) + " shapes to " + path)
        return True

    def open_file(self, event=None):
        path = filedialog.askopenfilename()
        if path == "":
            return

        with open(path) as f:
            lines = f.read().split("\n")

        # the header stops us from loading some random text file
        if lines[0] != HEADER:
            self.status.config(text="that is not a paint file")
            return

        # opening replaces the drawing, so ask first
        if not self.confirm_discard("open another file"):
            return

        # files from before the board switch have no board line, so keep the current one
        start = 1
        if len(lines) > 1 and lines[1].startswith("board|"):
            name = lines[1][6:]
            if name == "blackboard" or name == "whiteboard":
                self.set_board(name)
            start = 2

        loaded = []
        skipped = 0
        for line in lines[start:]:
            if line.strip() == "":
                continue
            shape = load_shape(line)
            if shape is None:
                skipped += 1
                continue
            loaded.append(shape)

        self.undone = []
        self.done = loaded
        self.replay()
        self.view_home()    # the file doesn't remember where you were looking
        self.saved = True   # set_board above marked it dirty, so reset here
        self.update_title()

        text = "opened " + str(len(self.done)) + " shapes"
        if skipped > 0:
            text += " (" + str(skipped) + " damaged lines skipped)"
        self.status.config(text=text)

    def export(self):
        # a .ps file can't be reopened, so this doesn't count as saving.
        # It exports the part of the page you can see, without the guide lines.
        path = filedialog.asksaveasfilename(defaultextension=".ps")
        if path == "":
            return
        self.canvas.delete("grid")
        self.canvas.postscript(file=path, colormode="color")
        self.draw_grid()
        self.status.config(text="exported to " + path)

    # ---------- status bar ----------

    def show_view(self):
        # while panning, show where the top-left corner of the view is
        left = int(self.canvas.canvasx(0))
        top = int(self.canvas.canvasy(0))
        self.status.config(text="view: " + str(left) + ", " + str(top)
                           + "   (Home goes back to 0, 0)")

    def show_status(self, x=None, y=None):
        text = "tool: " + self.tool.get() + "   size: " + str(self.size.get())
        if x is not None:
            text += "   x: " + str(x) + "  y: " + str(y)
        self.status.config(text=text)


def main():
    root = tk.Tk()
    root.resizable(False, False)
    Paint(root)
    root.mainloop()


# TODO: zoom, remember the view in the save file, custom Save/Discard/Cancel dialog

if __name__ == "__main__":
    main()