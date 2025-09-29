# fractal_forest_full.py
# Satu file: Fractal Forest interaktif lengkap dengan background, daun rontok, burung, awan, dan kontrol.
# Jalankan: python fractal_forest_full.py

import turtle
import math
import random
import time
from collections import deque

# ---------------- Config ----------------
WIDTH, HEIGHT = 1000, 700
GROUND_Y = -300
TREE_BASE_Y = GROUND_Y
TREE_COUNT = 3
TREE_SPACING = 280
TREE_DEPTH = 7            # jangan terlalu besar agar tetap cepat
TRUNK_LENGTH = 90
LEAF_SIZE = 4
FPS = 20                  # update per detik
AUTO_LEAF_FALL_RATE = 0.6 # per detik (rata-rata)
MAX_FALLING = 200
MAX_PILE = 1000
# ----------------------------------------

screen = turtle.Screen()
screen.setup(WIDTH, HEIGHT)
screen.title("Fractal Forest — Interactive")
screen.tracer(0, 0)
screen.bgcolor("black")
screen.colormode(1.0)

# Turtles terpisah untuk performance/pembersihan
bg_t = turtle.Turtle(visible=False)    # background (gradien, bintang, moon)
tree_t = turtle.Turtle(visible=False)  # branches & trunks
leaf_t = turtle.Turtle(visible=False)  # leaves dynamic
obj_t = turtle.Turtle(visible=False)   # birds, clouds, UI
for t in (bg_t, tree_t, leaf_t, obj_t):
    t.speed(0)
    t.hideturtle()
    t.penup()

# State containers
season_colors = [
    ["#4CAF50", "#81C784", "#A5D6A7"],   # spring
    ["#FFC107", "#FFD54F", "#FFF176"],   # summer
    ["#FF7043", "#FF8A65", "#F4511E"],   # autumn
    ["#B0BEC5", "#90A4AE", "#CFD8DC"]    # winter
]
season_names = ["Spring", "Summer", "Autumn", "Winter"]
current_season = 0
last_season_change = time.time()

pan_x, pan_y = 0, 0  # camera offset (simple)
global_wind_gust = 0.0   # temporary gust (decays)
wind_strength = 1.0      # base wind multiplier

leaf_id_counter = 0

class Tree:
    def __init__(self, base_x, base_y, trunk_length=TRUNK_LENGTH, depth=TREE_DEPTH):
        self.base_x = base_x
        self.base_y = base_y
        self.trunk_length = trunk_length
        self.depth = depth
        self.leaves = {}  # id -> (rel_x, rel_y, color)
        self.segments = []  # list of branch segments for drawing caching (start->end)
        self._generate_structure()

    def _generate_structure(self):
        """Generate geometry of tree as relative coordinates (base is (0,0))"""
        self.leaves.clear()
        self.segments.clear()
        global leaf_id_counter

        def rec(x, y, angle_deg, length, depth):
            # compute end point
            rad = math.radians(angle_deg)
            ex = x + math.cos(rad) * length
            ey = y + math.sin(rad) * length
            # store segment (relative)
            self.segments.append(((x, y), (ex, ey), depth))
            if depth <= 1 or length < 8:
                # leaf: store relative to base
                lid = leaf_id_counter + 1
                # add slight jitter to leaf pos
                lx = ex + random.uniform(-3, 3)
                ly = ey + random.uniform(-3, 3)
                color = random.choice(season_colors[current_season])
                self.leaves[lid] = (lx, ly, color)
                nonlocal_leaf_increment()
                return
            # left branch
            l_ang = angle_deg + random.uniform(16, 28)
            r_ang = angle_deg - random.uniform(16, 28)
            # shrink length
            nl = length * (0.68 + random.uniform(-0.05, 0.05))
            # rec left
            rec(ex, ey, l_ang, nl, depth-1)
            # rec right
            rec(ex, ey, r_ang, nl, depth-1)

        # helper to increment global id safely in closure
        def nonlocal_leaf_increment():
            global leaf_id_counter
            leaf_id_counter += 1

        # start from trunk base vertical (90 deg)
        rec(0, 0, 90, self.trunk_length, self.depth)

    def draw(self, drawer, sway, color_trunk="#8B5A2B"):
        """Draw branches using segments but rotated by sway (in degrees)."""
        # We will rotate each point by sway around base (0,0) then translate by base coords & pan
        drawer.penup()
        drawer.color(color_trunk)
        drawer.width(2)
        for (sx, sy), (ex, ey), depth in self.segments:
            # rotate points
            rsx, rsy = rotate_point(sx, sy, math.radians(sway))
            rex, rey = rotate_point(ex, ey, math.radians(sway))
            # transform to world coords
            wx1 = self.base_x + rsx + pan_x
            wy1 = self.base_y + rsy + pan_y
            wx2 = self.base_x + rex + pan_x
            wy2 = self.base_y + rey + pan_y
            drawer.penup()
            drawer.goto(wx1, wy1)
            drawer.pendown()
            drawer.goto(wx2, wy2)
            drawer.penup()

    def draw_leaves(self, drawer, sway, season_idx):
        """Draw remaining leaves (not yet fallen). Return list of (id, world_x, world_y, color)."""
        out = []
        drawer.width(1)
        for lid, (lx, ly, color) in list(self.leaves.items()):
            # rotate leaf around base by sway
            rx, ry = rotate_point(lx, ly, math.radians(sway))
            wx = self.base_x + rx + pan_x
            wy = self.base_y + ry + pan_y
            out.append((lid, wx, wy, color))
            drawer.penup()
            drawer.goto(wx, wy)
            drawer.pendown()
            drawer.dot(LEAF_SIZE, color)
            drawer.penup()
        return out

    def remove_leaf(self, lid):
        if lid in self.leaves:
            return self.leaves.pop(lid)
        return None

# Helpers
def rotate_point(x, y, rad):
    cx = x*math.cos(rad) - y*math.sin(rad)
    cy = x*math.sin(rad) + y*math.cos(rad)
    return cx, cy

# Falling leaf physics
class FallingLeaf:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        angle = random.uniform(-1.0, 1.0)
        self.vx = angle * 20.0
        self.vy = -random.uniform(10, 30)
        self.color = color
        self.birth = time.time()
        self.toss = random.uniform(0, 2 * math.pi)  # phase for side-to-side motion

    def update(self, dt):
        # wind influences vx (global wind + gust) and side oscillation
        wind = (math.sin(time.time()*0.8) * 0.6 + global_wind_gust*1.5) * wind_strength
        # side-to-side oscillation
        self.x += (self.vx + wind) * dt
        self.y += self.vy * dt + (-9.8 * dt * 0.5)  # gravity-ish weak
        # gentle turbulence
        self.x += math.sin((time.time() + self.toss) * 3.0) * (1.5 * dt) * 30
        self.vy += -15 * dt  # accelerate downward a bit
        # clamp
        return

falling_leaves = []  # list of FallingLeaf
leaf_pile = []       # landed leaves positions and colors

# Clouds & birds
class Cloud:
    def __init__(self, x, y, size, speed):
        self.x = x; self.y = y; self.size = size; self.speed = speed
    def update(self, dt):
        self.x += self.speed * dt
        if self.x > WIDTH/2 + 200:
            self.x = -WIDTH/2 - 200

class Bird:
    def __init__(self, x, y, speed, amp=30.0):
        self.x = x; self.y = y; self.speed = speed; self.amp = amp; self.start = time.time()
    def update(self, dt):
        self.x += self.speed * dt
        self.y += math.sin((time.time()-self.start)*2.0) * (self.amp * dt)
        if self.x > WIDTH/2 + 200:
            self.x = -WIDTH/2 - 200

clouds = [Cloud(random.uniform(-WIDTH/2, WIDTH/2), random.uniform(50, 280), random.uniform(80,160), random.uniform(10,30)) for _ in range(6)]
birds = [Bird(random.uniform(-WIDTH/2, WIDTH/2), random.uniform(100, 240), random.uniform(40,120), amp=random.uniform(10,40)) for _ in range(4)]

# Trees initialization
trees = []
def spawn_initial_trees():
    trees.clear()
    mid = 0
    start_x = mid - (TREE_COUNT//2)*TREE_SPACING
    for i in range(TREE_COUNT):
        tx = start_x + i * TREE_SPACING
        t = Tree(tx, TREE_BASE_Y, trunk_length=TRUNK_LENGTH, depth=TREE_DEPTH)
        trees.append(t)

spawn_initial_trees()

# UI helper
def draw_background():
    bg_t.clear()
    # gradient: draw horizontal lines
    for i in range(HEIGHT//2 + 50):
        # top to bottom: dark navy -> deeper blue
        frac = i / float(HEIGHT//2 + 50)
        r = 0.03 + 0.25* (1-frac)
        g = 0.03 + 0.12* (1-frac)
        b = 0.08 + 0.6 * (1-frac)
        bg_t.color(r,g,b)
        bg_t.penup()
        y = -HEIGHT/2 + i
        bg_t.goto(-WIDTH/2, y)
        bg_t.pendown()
        bg_t.forward(WIDTH)
        bg_t.penup()
    # stars
    for _ in range(90):
        x = random.randint(-WIDTH//2 + 20, WIDTH//2 - 20)
        y = random.randint(HEIGHT//6, HEIGHT//2 - 30)
        s = random.choice([1,1,2])
        bg_t.goto(x + pan_x*0.02, y + pan_y*0.02)
        bg_t.dot(s, "white")
    # moon
    bg_t.goto(WIDTH//4 + pan_x*0.02, HEIGHT//4 + pan_y*0.02)
    bg_t.dot(80, "#FFF6C8")
    bg_t.goto(WIDTH//4 + 8 + pan_x*0.02, HEIGHT//4 + 8 + pan_y*0.02)
    bg_t.dot(70, (0,0,0))
    # mountains silhouette
    bg_t.color(0.03, 0.05, 0.08)
    bg_t.penup()
    bg_t.goto(-WIDTH//2 - 50 + pan_x*0.2, GROUND_Y - 30 + pan_y*0.2)
    bg_t.begin_fill()
    bg_t.pendown()
    # draw simple jagged mountains
    x = -WIDTH//2 - 50
    while x < WIDTH//2 + 100:
        h = random.randint(30, 110)
        bg_t.goto(x + pan_x*0.2, GROUND_Y - 30 + h + pan_y*0.2)
        x += random.randint(80, 160)
    bg_t.goto(WIDTH//2 + 100 + pan_x*0.2, GROUND_Y - 30 + pan_y*0.2)
    bg_t.goto(-WIDTH//2 - 50 + pan_x*0.2, GROUND_Y - 30 + pan_y*0.2)
    bg_t.end_fill()

def draw_clouds_and_birds(dt):
    obj_t.clear()
    # clouds
    for cl in clouds:
        cl.update(dt)
        # cloud composed of several circles
        cx = cl.x + pan_x*0.05
        cy = cl.y + pan_y*0.05
        for i in range(4):
            obj_t.goto(cx + i*cl.size*0.14, cy + math.sin(i)*3)
            obj_t.dot(cl.size*0.5, (0.93,0.95,0.98))
    # birds
    for b in birds:
        b.update(dt)
        bx = b.x + pan_x*0.02
        by = b.y + pan_y*0.02
        # draw simple V
        obj_t.penup()
        obj_t.goto(bx-8, by)
        obj_t.pendown()
        obj_t.goto(bx, by+6)
        obj_t.goto(bx+8, by)
        obj_t.penup()

# Click handling: click leaf or spawn tree if clicking near ground
def on_click(x, y):
    # first search near leaves
    # build list of current leaf world positions
    found = False
    for t in trees:
        sway = math.sin(time.time()*0.8 + (t.base_x/200.0)) * 6 + global_wind_gust*4
        for lid, (lx, ly, color) in list(t.leaves.items()):
            rx, ry = rotate_point(lx, ly, math.radians(sway))
            wx = t.base_x + rx + pan_x
            wy = t.base_y + ry + pan_y
            if (x - wx)**2 + (y - wy)**2 <= 12**2:
                # trigger falling for this leaf
                data = t.remove_leaf(lid)
                if data:
                    fl = FallingLeaf(wx, wy, data[2])
                    if len(falling_leaves) < MAX_FALLING:
                        falling_leaves.append(fl)
                    found = True
                    break
        if found: break
    if not found:
        # if clicked near ground, spawn a tree
        if y < GROUND_Y + 40:
            new_tx = x - pan_x
            new_tree = Tree(new_tx, TREE_BASE_Y, trunk_length=TRUNK_LENGTH, depth=TREE_DEPTH)
            trees.append(new_tree)

def on_key_a():
    global global_wind_gust
    global_wind_gust = 3.0
def on_key_s():
    global current_season, last_season_change
    current_season = (current_season + 1) % len(season_colors)
    last_season_change = time.time()
    # update all tree leaf colors
    for t in trees:
        for lid in t.leaves:
            # recolor leaves
            t.leaves[lid] = (t.leaves[lid][0], t.leaves[lid][1], random.choice(season_colors[current_season]))
def on_key_d():
    # make all leaves fall
    for t in trees:
        for lid, (lx, ly, color) in list(t.leaves.items()):
            rx, ry = rotate_point(lx, ly, math.radians(0))
            wx = t.base_x + rx + pan_x
            wy = t.base_y + ry + pan_y
            data = t.remove_leaf(lid)
            if data:
                fl = FallingLeaf(wx, wy, data[2])
                if len(falling_leaves) < MAX_FALLING:
                    falling_leaves.append(fl)

def on_key_left():
    global pan_x
    pan_x += 30
def on_key_right():
    global pan_x
    pan_x -= 30
def on_key_up():
    global pan_y
    pan_y -= 20
def on_key_down():
    global pan_y
    pan_y += 20

screen.onclick(on_click)
screen.listen()
screen.onkey(on_key_a, "a")
screen.onkey(on_key_s, "s")
screen.onkey(on_key_d, "d")
screen.onkey(on_key_left, "Left")
screen.onkey(on_key_right, "Right")
screen.onkey(on_key_up, "Up")
screen.onkey(on_key_down, "Down")

# auto leaf fall timer
last_auto_fall = time.time()

# main update loop
last_time = time.time()
def update():
    global last_time, last_auto_fall, global_wind_gust

    now = time.time()
    dt = max(0.001, now - last_time)
    last_time = now

    # gradually decay gust
    global_wind_gust *= 0.93

    # background and static
    draw_background()

    # random automatic leaf fall
    if random.random() < AUTO_LEAF_FALL_RATE * dt:
        # pick a random tree and random leaf
        if trees:
            t = random.choice(trees)
            if t.leaves:
                lid = random.choice(list(t.leaves.keys()))
                data = t.remove_leaf(lid)
                if data:
                    # compute world pos with 0 sway (approx)
                    rx, ry = rotate_point(data[0], data[1], 0.0)
                    wx = t.base_x + rx + pan_x
                    wy = t.base_y + ry + pan_y
                    fl = FallingLeaf(wx, wy, data[2])
                    if len(falling_leaves) < MAX_FALLING:
                        falling_leaves.append(fl)

    # draw clouds and birds first (under trees)
    draw_clouds_and_birds(dt)

    # draw trees
    tree_t.clear()
    for i, t_obj in enumerate(trees):
        sway = math.sin(time.time()*0.8 + i) * 6 + global_wind_gust*4
        t_obj.draw(tree_t, sway)
    # draw leaves (static ones)
    leaf_t.clear()
    all_leaf_world = []  # (tree_obj, lid, x, y, color)
    for i, t_obj in enumerate(trees):
        sway = math.sin(time.time()*0.8 + i) * 6 + global_wind_gust*4
        lv = t_obj.draw_leaves(leaf_t, sway, current_season)
        for lid, wx, wy, color in lv:
            all_leaf_world.append((t_obj, lid, wx, wy, color))

    # update & draw falling leaves
    # update physics
    for fl in list(falling_leaves):
        fl.update(dt)
    # draw falling leaves, remove landed ones to pile
    new_falling = []
    for fl in falling_leaves:
        # draw leaf as dot
        leaf_t.penup()
        leaf_t.goto(fl.x, fl.y)
        leaf_t.pendown()
        leaf_t.dot(LEAF_SIZE+2, fl.color)
        leaf_t.penup()
        # if landed (below ground), add to pile
        if fl.y <= GROUND_Y + 5:
            if len(leaf_pile) < MAX_PILE:
                leaf_pile.append((fl.x, GROUND_Y + random.uniform(-6, 6), fl.color))
        else:
            new_falling.append(fl)
    # keep the new list
    falling_leaves[:] = new_falling

    # draw leaf pile
    leaf_t.width(1)
    for (x, y, color) in leaf_pile:
        leaf_t.penup()
        leaf_t.goto(x, y)
        leaf_t.dot(random.uniform(3,6), color)

    # draw UI text (season + controls)
    obj_t.penup()
    obj_t.goto(-WIDTH/2 + 16, HEIGHT/2 - 36)
    obj_t.color(1,1,1)
    obj_t.write(f"Season: {season_names[current_season]}   Trees: {len(trees)}   Falling: {len(falling_leaves)}", font=("Arial", 12, "normal"))

    # small instructions
    obj_t.goto(-WIDTH/2 + 16, -HEIGHT/2 + 16)
    obj_t.write("Click leaf to drop it. Click ground to plant tree. A=gust S=season D=drop all. Arrows=pan", font=("Arial", 10, "normal"))

    screen.update()
    # schedule next frame
    screen.ontimer(update, int(1000 / FPS))

# start
draw_background()
last_time = time.time()
screen.ontimer(update, int(1000 / FPS))
screen.mainloop()
