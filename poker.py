import math
import random
import time
import tkinter as tk
from tkinter import messagebox, simpledialog

W = 900
H = 540
CARD_W = 64
CARD_H = 90
FRAME_MS = 16
MAX_CHIPS = 100000
MAX_BETS = 4

DECK_X = 130
DECK_Y = 272
POT_X = 730
POT_Y = 272
BOT_Y = 120
YOU_Y = 425
BOT_BET_Y = 205
YOU_BET_Y = 362
PILE_X = 250
FELT = "#1d7a4a"

SUITS = "♠♥♦♣"
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
HAND_NAMES = ["high card", "pair", "two pair", "three of a kind", "straight",
              "flush", "full house", "four of a kind", "straight flush"]
STAGES = ["preflop", "flop", "turn", "river"]
CHIP_COLORS = ["#d63031", "#0984e3", "#00b894", "#2d3436", "#e1b12c"]

# chance the bot does each thing, by hand strength (0 = weak ... 4 = monster)
BET_CHANCE = [0.25, 0.5, 0.7, 0.8, 0.9]
CALL_CHANCE = [0.2, 0.5, 0.7, 0.85, 0.95]
RAISE_CHANCE = [0.05, 0.12, 0.25, 0.35, 0.5]


def mix(c1, c2, t):
    # blend two "#rrggbb" colors, t=0 gives c1 and t=1 gives c2
    result = "#"
    for i in range(1, 7, 2):
        a = int(c1[i:i + 2], 16)
        b = int(c2[i:i + 2], 16)
        result += format(int(a + (b - a) * t), "02x")
    return result


# ---------- objects ----------

class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
        self.x = DECK_X
        self.y = DECK_Y
        self.tx = DECK_X
        self.ty = DECK_Y
        self.delay = 0
        self.open = 0.0        # 0 is face down, 1 is face up
        self.want_open = 0.0
        self.glow = False

    def value(self):
        return RANKS.index(self.rank) + 2

    def color(self):
        if self.suit == "♥" or self.suit == "♦":
            return "#c0392b"
        return "#222222"

    def arrived(self, now):
        return now >= self.delay and self.x == self.tx and self.y == self.ty


class Chip:
    def __init__(self, x, y, tx, ty, delay, color):
        self.x = x
        self.y = y
        self.tx = tx
        self.ty = ty
        self.delay = delay
        self.color = color
        self.landed = None   # time it reached its target, None while flying


class Player:
    def __init__(self, name, chips):
        self.name = name
        self.chips = chips
        self.hand = []
        self.paid = 0          # chips put in during this betting round
        self.say = ""
        self.say_until = 0
        self.ante_paid = 0
        self.ante_until = 0

    def pay(self, amount):
        amount = min(amount, self.chips)
        self.chips -= amount
        return amount


class Move:
    # what the bot decided to do
    def __init__(self, action, amount):
        self.action = action
        self.amount = amount


# ---------- animation helpers ----------

def glide(obj, now):
    if now < obj.delay:
        return
    obj.x += (obj.tx - obj.x) * 0.2
    obj.y += (obj.ty - obj.y) * 0.2
    if abs(obj.tx - obj.x) < 0.5:
        obj.x = obj.tx
    if abs(obj.ty - obj.y) < 0.5:
        obj.y = obj.ty


def hop(chip, now):
    # pixels above its target a landed chip is drawn, for the bounce
    if chip.landed is None:
        return 0
    t = now - chip.landed
    if t > 0.4:
        return 0
    return -abs(math.sin(t * 14)) * 14 * (1 - t / 0.4)


# ---------- cards and scoring ----------

def make_deck():
    deck = []
    for suit in SUITS:
        for rank in RANKS:
            deck.append(Card(rank, suit))
    random.shuffle(deck)
    return deck


def score_five(cards):
    # returns [category, tiebreakers]; lists compare left to right,
    # so a bigger score always means a better hand
    values = []
    counts = []
    for i in range(15):
        counts.append(0)

    same_suit = True
    for card in cards:
        values.append(card.value())
        counts[card.value()] += 1
        if card.suit != cards[0].suit:
            same_suit = False
    values.sort(reverse=True)

    # pairs and trips first, then the high cards,
    # so a pair of 3s still beats ace high
    order = []
    shape = []
    for n in [4, 3, 2, 1]:
        for v in range(14, 1, -1):
            if counts[v] == n:
                order.append(v)
                shape.append(n)

    straight = len(order) == 5 and values[0] - values[4] == 4
    if values == [14, 5, 4, 3, 2]:   # A-2-3-4-5
        straight = True
        order = [5, 4, 3, 2, 1]

    if straight and same_suit:
        return [8, order]
    if shape == [4, 1]:
        return [7, order]
    if shape == [3, 2]:
        return [6, order]
    if same_suit:
        return [5, order]
    if straight:
        return [4, order]
    if shape == [3, 1, 1]:
        return [3, order]
    if shape == [2, 2, 1]:
        return [2, order]
    if shape == [2, 1, 1, 1]:
        return [1, order]
    return [0, order]


def all_fives(cards):
    # every 5 card hand that can be made from 5, 6 or 7 cards
    n = len(cards)
    hands = []
    if n == 5:
        hands.append(cards[:])
    elif n == 6:
        for skip in range(6):
            hand = []
            for i in range(6):
                if i != skip:
                    hand.append(cards[i])
            hands.append(hand)
    else:
        for a in range(7):
            for b in range(a + 1, 7):
                hand = []
                for i in range(7):
                    if i != a and i != b:
                        hand.append(cards[i])
                hands.append(hand)
    return hands


def best_five(cards):
    # returns [score, the five cards that make it]
    best = None
    best_cards = []
    for hand in all_fives(cards):
        score = score_five(hand)
        if best is None or score > best:
            best = score
            best_cards = hand
    return [best, best_cards]


# ---------- the bot's brain ----------

def bot_strength(bot, board):
    if len(board) == 0:
        a = bot.hand[0].value()
        b = bot.hand[1].value()
        if a == b:
            return 2
        if max(a, b) >= 12:
            return 1
        return 0
    return best_five(bot.hand + board)[0][0]


def bot_bet_size(strength, pot, limit):
    if strength >= 4 and random.random() < 0.2:
        return limit

    if strength >= 2:
        low = 0.4
        high = 1.5
    elif strength == 1:
        low = 0.2
        high = 1.0
    else:
        low = 0.1
        high = 0.6

    size = int(pot * random.uniform(low, high))
    if random.random() < 0.15:
        size = int(limit * random.uniform(0.1, 0.5))
    return max(1, min(size, limit))


def bot_raise_size(strength, pot, level, min_bet, limit):
    if strength >= 4 and random.random() < 0.2:
        return limit

    if strength >= 2:
        low = 0.5
        high = 1.5
    elif strength == 1:
        low = 0.3
        high = 1.0
    else:
        low = 0.2
        high = 0.7

    new_level = level + int(pot * random.uniform(low, high))
    smallest = min(limit, level + min_bet)
    return max(smallest, min(new_level, limit))


def bot_decide(bot, board, pot, to_call, level, min_bet, limit, can_raise):
    strength = min(bot_strength(bot, board), 4)

    if to_call == 0:
        if random.random() < BET_CHANCE[strength]:
            return Move("bet", bot_bet_size(strength, pot, limit))
        return Move("check", 0)

    if can_raise and random.random() < RAISE_CHANCE[strength]:
        return Move("raise", bot_raise_size(strength, pot, level, min_bet, limit))

    chance = CALL_CHANCE[strength]
    if to_call > pot - to_call:
        chance *= 0.6   # a bet bigger than the pot is scarier
    if random.random() < chance:
        return Move("call", to_call)
    return Move("fold", 0)


# ---------- the game ----------

class Game:
    def __init__(self, root):
        self.root = root
        root.title("Poker")
        root.configure(bg="#120d0a")

        self.canvas = tk.Canvas(root, width=W, height=H, highlightthickness=0, bg="#120d0a")
        self.canvas.pack()

        self.you = Player("you", 0)
        self.bot = Player("bot", 0)
        self.first = self.you
        self.you_first = True
        self.order = [self.you, self.bot]
        self.turn = 0
        self.deck = []
        self.board = []
        self.chips_flying = []
        self.in_flight = 0     # chips sliding to the pot that haven't landed yet
        self.pot = 0
        self.stage = 0
        self.level = 0
        self.limit = 0
        self.bets = 0
        self.checks = 0
        self.start = 1000
        self.bought = 0
        self.ante = 10
        self.min_bet = 20
        self.winner = None
        self.thinking = False
        self.game_over = False
        self.phase = "wait"    # idle, you or wait: what the game is waiting for
        self.message = "starting..."

        self.draw_table()
        self.build_controls()
        root.bind("<Key>", self.on_key)

        self.update_controls()
        self.frame()
        root.after(300, self.new_game)

    def build_controls(self):
        bar = tk.Frame(self.root, bg="#120d0a")
        bar.pack(fill="x", pady=8)

        font = "Helvetica 12"
        self.btn_next = tk.Button(bar, text="Next hand", width=10, font=font, command=self.next_hand)
        self.btn_next.pack(side="left", padx=(14, 3))
        self.btn_add = tk.Button(bar, text="Add chips", width=9, font=font, command=self.add_more)
        self.btn_add.pack(side="left", padx=3)

        self.btn_fold = tk.Button(bar, text="Fold", width=8, font=font, command=self.do_fold)
        self.btn_fold.pack(side="left", padx=(30, 3))
        self.btn_call = tk.Button(bar, text="Check", width=9, font=font, command=self.do_call)
        self.btn_call.pack(side="left", padx=3)

        self.amount = tk.IntVar(value=0)
        self.scale = tk.Scale(bar, from_=0, to=1, orient="horizontal", variable=self.amount,
                              length=190, showvalue=0, bg="#120d0a", highlightthickness=0)
        self.scale.pack(side="left", padx=6)

        self.btn_raise = tk.Button(bar, text="Bet", width=13, font=font, command=self.do_raise)
        self.btn_raise.pack(side="left", padx=3)
        self.btn_allin = tk.Button(bar, text="All in", width=7, font=font, command=self.do_allin)
        self.btn_allin.pack(side="left", padx=3)

        self.scale.config(command=self.on_scale)

    def on_key(self, event):
        key = event.keysym.lower()
        if key == "space":
            self.next_hand()
        elif key == "f":
            self.do_fold()
        elif key == "c":
            self.do_call()
        elif key == "b" or key == "r":
            self.do_raise()

    def on_scale(self, value=None):
        text = "Bet "
        if self.level > 0:
            text = "Raise to "
        self.btn_raise.config(text=text + str(self.amount.get()))

    def other(self, player):
        if player is self.you:
            return self.bot
        return self.you

    def can_raise(self):
        return self.level < self.limit and self.bets < MAX_BETS

    # ---------- setting up games and hands ----------

    def new_game(self):
        start = simpledialog.askinteger("Poker", "starting chips (100-" + str(MAX_CHIPS) + ")",
                                        parent=self.root, minvalue=100, maxvalue=MAX_CHIPS)
        if start is None:
            start = 1000

        self.start = start
        self.bought = start
        self.ante = max(1, start // 50)
        self.min_bet = max(1, start // 25)
        self.you = Player("you", start)
        self.bot = Player("bot", start)
        self.first = self.you
        self.you_first = True
        self.board = []
        self.pot = 0
        self.stage = 0
        self.game_over = False
        self.phase = "idle"
        self.message = "press space to deal"
        self.update_controls()

    def next_hand(self, event=None):
        if self.phase != "idle":
            return
        if self.game_over:
            self.new_game()
            return

        now = time.time()
        self.deck = make_deck()
        self.board = []
        self.chips_flying = []
        self.in_flight = 0
        self.pot = 0
        self.stage = 0
        self.you.hand = []
        self.bot.hand = []
        self.you.say = ""
        self.bot.say = ""

        # who acts first swaps every hand
        if self.you_first:
            self.first = self.you
        else:
            self.first = self.bot
        self.you_first = not self.you_first

        # deal one card at a time, you then bot, twice
        dealing = [self.you, self.bot, self.you, self.bot]
        for i in range(4):
            player = dealing[i]
            card = self.deck.pop()
            slot = len(player.hand)
            card.tx = 412 + slot * 76
            if player is self.you:
                card.ty = YOU_Y
                card.want_open = 1.0
            else:
                card.ty = BOT_Y
            card.delay = now + i * 0.25
            player.hand.append(card)

        self.slide_antes(now)

        self.phase = "wait"
        self.message = "dealing..."
        self.update_controls()
        self.root.after(1500, self.begin_round)

    def add_chips(self, amount):
        # the bot always gets the same amount, so the stacks stay even
        self.you.chips += amount
        self.bot.chips += amount
        self.bought += amount

    def add_more(self):
        if self.phase != "idle" or self.game_over:
            return
        room = MAX_CHIPS - self.you.chips
        if room < 1:
            return
        amount = simpledialog.askinteger("Add chips", "how many? (1-" + str(room) + ")",
                                         parent=self.root, minvalue=1, maxvalue=room)
        if amount is not None:
            self.add_chips(amount)
            self.message = "added " + str(amount) + " for you and the bot"

    # ---------- chips sliding around ----------

    def slide_antes(self, now):
        # take the ante from each player and send chips from their stack to the pot
        for player in [self.bot, self.you]:
            y = BOT_Y
            if player is self.you:
                y = YOU_Y

            paid = player.pay(self.ante)
            if paid <= 0:
                continue   # a short stack may have nothing left to post

            self.pot += paid
            self.in_flight += paid   # keeps the pot pile empty until the chips land
            player.ante_paid = paid
            player.ante_until = now + 1.2

            for i in range(3):
                self.chips_flying.append(Chip(PILE_X, y + 18 - i * 5,
                                              POT_X + random.randint(-10, 10),
                                              POT_Y + random.randint(-6, 6),
                                              now + i * 0.06,
                                              CHIP_COLORS[i % len(CHIP_COLORS)]))

        self.root.after(1200, self.land_sweep)

    def sweep_bets(self):
        # send each player's bet pile to the pot; returns True if anything moved
        now = time.time()
        moved = False
        for player in [self.bot, self.you]:
            y = BOT_BET_Y
            if player is self.you:
                y = YOU_BET_Y

            if player.paid <= 0:
                continue
            count = min(5, 1 + player.paid // max(1, self.start // 20))
            for i in range(count):
                self.chips_flying.append(Chip(450, y - i * 5,
                                              POT_X + random.randint(-10, 10),
                                              POT_Y + random.randint(-6, 6),
                                              now + i * 0.06,
                                              CHIP_COLORS[i % len(CHIP_COLORS)]))
            self.in_flight += player.paid
            player.paid = 0
            moved = True

        if moved:
            self.root.after(1100, self.land_sweep)
        return moved

    def land_sweep(self):
        # the chips have arrived, so the pot pile may show their value now
        self.in_flight = 0
        self.chips_flying = []

    # ---------- betting rounds ----------

    def begin_round(self):
        self.you.paid = 0
        self.bot.paid = 0
        self.level = 0
        self.bets = 0
        self.checks = 0
        self.limit = min(self.you.chips, self.bot.chips)
        self.order = [self.first, self.other(self.first)]
        self.turn = 0

        if self.limit == 0:   # someone is all in, nothing to bet
            self.phase = "wait"
            self.root.after(900, self.end_round)
            return
        self.next_turn()

    def next_turn(self):
        player = self.order[self.turn]
        if player is self.you:
            self.phase = "you"
            self.message = "your turn"
        else:
            self.phase = "wait"
            self.thinking = True
            self.message = "bot is thinking"
            self.root.after(random.randint(700, 1500), self.bot_move)
        self.update_controls()

    def bot_move(self):
        self.thinking = False
        to_call = self.level - self.bot.paid
        move = bot_decide(self.bot, self.board, self.pot, to_call, self.level,
                          self.min_bet, self.limit, self.can_raise())
        self.apply(self.bot, move.action, move.amount)

    def say(self, player, text):
        player.say = text
        player.say_until = time.time() + 2.4

    def put(self, player, amount):
        paid = player.pay(amount)
        player.paid += paid
        self.pot += paid

    def apply(self, player, action, amount):
        self.phase = "wait"
        self.update_controls()
        other = self.other(player)

        if action == "fold":
            self.say(player, "fold")
            self.finish_hand(other, player.name + " folded, " + other.name + " wins " + str(self.pot), 900)
            return

        if action == "check":
            self.say(player, "check")
            self.checks += 1
            if self.checks == 2:
                self.root.after(800, self.end_round)
                return
        elif action == "call":
            self.put(player, self.level - player.paid)
            self.say(player, "call")
            self.root.after(800, self.end_round)
            return
        else:
            # a bet or a raise: amount is the new level for the round
            self.put(player, amount - player.paid)
            self.level = amount
            self.bets += 1
            self.checks = 0
            if action == "bet":
                self.say(player, "bet " + str(amount))
            else:
                self.say(player, "raise to " + str(amount))

        self.turn = 1 - self.turn
        self.root.after(800, self.next_turn)

    def end_round(self):
        # slide the bets into the pot first, then move to the next stage
        if self.sweep_bets():
            self.root.after(1150, self.advance_stage)
        else:
            self.advance_stage()

    def advance_stage(self):
        self.you.paid = 0
        self.bot.paid = 0

        if self.stage == 3:
            self.showdown()
            return

        self.stage += 1
        count = 1
        if self.stage == 1:
            count = 3   # the flop is three cards

        now = time.time()
        for i in range(count):
            card = self.deck.pop()
            slot = len(self.board)
            card.tx = 450 + (slot - 2) * 80
            card.ty = DECK_Y
            card.delay = now + i * 0.25
            card.want_open = 1.0
            self.board.append(card)

        self.message = STAGES[self.stage]
        self.root.after(1500, self.begin_round)

    # ---------- your buttons ----------

    def do_fold(self):
        if self.phase != "you":
            return
        if self.level - self.you.paid == 0:
            return   # nothing to fold against, checking is free
        self.apply(self.you, "fold", 0)

    def do_call(self):
        if self.phase != "you":
            return
        to_call = self.level - self.you.paid
        if to_call == 0:
            self.apply(self.you, "check", 0)
        else:
            self.apply(self.you, "call", to_call)

    def send_raise(self, amount):
        low = min(self.limit, self.level + self.min_bet)
        amount = max(low, min(amount, self.limit))
        action = "bet"
        if self.level > 0:
            action = "raise"
        self.apply(self.you, action, amount)

    def do_raise(self):
        if self.phase != "you" or not self.can_raise():
            return
        self.send_raise(self.amount.get())

    def do_allin(self):
        if self.phase != "you" or not self.can_raise():
            return
        self.send_raise(self.limit)

    def update_controls(self):
        off = "disabled"
        self.btn_fold.config(state=off)
        self.btn_call.config(state=off, text="Check")
        self.btn_raise.config(state=off, text="Bet")
        self.btn_allin.config(state=off)
        self.scale.config(state=off)

        if self.phase == "you":
            to_call = self.level - self.you.paid
            if to_call > 0:
                self.btn_fold.config(state="normal")
                self.btn_call.config(state="normal", text="Call " + str(to_call))
            else:
                self.btn_call.config(state="normal", text="Check")
            if self.can_raise():
                low = min(self.limit, self.level + self.min_bet)
                self.scale.config(from_=low, to=self.limit, state="normal")
                self.amount.set(low)
                self.btn_raise.config(state="normal")
                self.btn_allin.config(state="normal")
                self.on_scale()

        if self.phase == "idle":
            self.btn_next.config(state="normal")
            if self.game_over:
                self.btn_next.config(text="New game")
                self.btn_add.config(state=off)
            else:
                self.btn_next.config(text="Next hand")
                self.btn_add.config(state="normal")
        else:
            self.btn_next.config(state=off)
            self.btn_add.config(state=off)

    # ---------- ending a hand ----------

    def showdown(self):
        self.phase = "wait"
        for card in self.bot.hand:
            card.want_open = 1.0

        mine_result = best_five(self.you.hand + self.board)
        their_result = best_five(self.bot.hand + self.board)
        mine = mine_result[0]
        theirs = their_result[0]

        if mine > theirs:
            winner = self.you
            glow = mine_result[1]
            text = "you win " + str(self.pot) + " with " + HAND_NAMES[mine[0]]
        elif theirs > mine:
            winner = self.bot
            glow = their_result[1]
            text = "bot wins " + str(self.pot) + " with " + HAND_NAMES[theirs[0]]
        else:
            winner = None
            glow = []
            text = "split pot, both have " + HAND_NAMES[mine[0]]

        for card in glow:
            card.glow = True
        self.finish_hand(winner, text, 1800)

    def finish_hand(self, winner, text, wait):
        self.phase = "wait"
        self.winner = winner
        self.message = text
        self.update_controls()
        if self.sweep_bets():   # a fold leaves bets on the table
            wait += 1150
        self.root.after(wait, self.start_payout)

    def start_payout(self):
        now = time.time()
        self.chips_flying = []
        for i in range(8):
            target = self.winner
            if target is None:   # split pot: chips go to both players
                if i % 2 == 0:
                    target = self.you
                else:
                    target = self.bot
            ty = BOT_Y
            if target is self.you:
                ty = YOU_Y
            self.chips_flying.append(Chip(POT_X + random.randint(-12, 12),
                                          POT_Y + random.randint(-8, 8),
                                          PILE_X, ty, now + i * 0.08,
                                          CHIP_COLORS[i % len(CHIP_COLORS)]))
        self.root.after(1500, self.finish_payout)

    def finish_payout(self):
        if self.winner is None:
            half = self.pot // 2
            self.you.chips += half
            self.bot.chips += self.pot - half
        else:
            self.winner.chips += self.pot
        self.pot = 0
        self.chips_flying = []
        self.phase = "idle"
        self.message = "press space for the next hand"
        self.check_game()
        self.update_controls()

    def check_game(self):
        if self.bot.chips < self.ante:
            self.game_over = True
            self.message = "bot is out of chips, you win the game!"
            return

        if self.you.chips < self.ante:
            self.message = "you're out of chips"
            if messagebox.askyesno("Out of chips", "rebuy?", parent=self.root):
                room = MAX_CHIPS - self.you.chips
                amount = simpledialog.askinteger("Rebuy",
                                                 "chips to add (" + str(self.ante) + "-" + str(room) + ")",
                                                 parent=self.root, minvalue=self.ante, maxvalue=room)
                if amount is not None:
                    self.add_chips(amount)
                    self.message = "rebought " + str(amount)
                    return
            self.game_over = True
            self.message = "game over"

    # ---------- drawing ----------

    def draw_table(self):
        # drawn once with the tag "bg", so it is never erased
        c = self.canvas
        c.create_oval(40, 35, 860, 515, fill="#4a2c14", outline="#2a180a", width=3, tags="bg")
        c.create_oval(52, 47, 848, 503, fill="#2b1a0c", outline="#1a0f06", width=2, tags="bg")
        for k in range(8):
            c.create_oval(62 + k * 14, 57 + k * 8, 838 - k * 14, 493 - k * 8,
                          fill=mix("#145c38", "#27935c", k / 7), outline="", tags="bg")
        c.create_oval(90, 85, 810, 465, fill="", outline="#d4af37", width=1, tags="bg")

    def rounded(self, x1, y1, x2, y2, r, fill, outline):
        r = min(r, (x2 - x1) / 2)
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
               x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
               x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        self.canvas.create_polygon(pts, smooth=True, fill=fill, outline=outline, tags="fg")

    def draw_back(self, x, y, w):
        x1 = x - w / 2
        x2 = x + w / 2
        y1 = y - CARD_H / 2
        y2 = y + CARD_H / 2
        self.rounded(x1, y1, x2, y2, 7, "#274690", "white")
        if w > CARD_W * 0.9:
            self.rounded(x1 + 6, y1 + 6, x2 - 6, y2 - 6, 4, "#1b3270", "#8fa8ff")
            self.canvas.create_polygon(x, y - 18, x + 14, y, x, y + 18, x - 14, y,
                                       fill="#8fa8ff", outline="", tags="fg")

    def draw_card(self, card):
        c = self.canvas
        # the flip squeezes the card's width to nothing and back
        scale = abs(math.cos(math.pi * card.open))
        w = max(4, CARD_W * scale)
        x1 = card.x - w / 2
        x2 = card.x + w / 2
        y1 = card.y - CARD_H / 2
        y2 = card.y + CARD_H / 2

        self.rounded(x1 + 3, y1 + 5, x2 + 3, y2 + 5, 7, "#0c3a24", "")
        if card.glow:
            self.rounded(x1 - 4, y1 - 4, x2 + 4, y2 + 4, 10, "#f1c40f", "")

        if card.open > 0.5:
            self.rounded(x1, y1, x2, y2, 7, "white", "#9a9a9a")
            if scale > 0.9:
                color = card.color()
                c.create_text(x1 + 11, y1 + 14, text=card.rank, fill=color,
                              font="Helvetica 14 bold", tags="fg")
                c.create_text(x1 + 11, y1 + 31, text=card.suit, fill=color,
                              font="Helvetica 14", tags="fg")
                c.create_text(card.x, card.y + 2, text=card.suit, fill=color,
                              font="Helvetica 32", tags="fg")
                c.create_text(x2 - 11, y2 - 14, text=card.rank, fill=color,
                              font="Helvetica 14 bold", tags="fg")
        else:
            self.draw_back(card.x, card.y, w)

    def draw_chip(self, x, y, color):
        c = self.canvas
        c.create_oval(x - 13, y - 3, x + 13, y + 9, fill="#101010", outline="", tags="fg")
        c.create_oval(x - 13, y - 6, x + 13, y + 6, fill=color, outline="#101010", tags="fg")
        c.create_oval(x - 8, y - 3.5, x + 8, y + 3.5, fill="", outline="white", tags="fg")

    def pile(self, x, y, amount, unit):
        if amount <= 0:
            return
        count = min(8, 1 + amount // max(1, unit))
        for i in range(count):
            self.draw_chip(x, y - i * 5, CHIP_COLORS[i % len(CHIP_COLORS)])

    def draw_panel(self, player, y, now):
        c = self.canvas
        c.create_text(360, y - 16, text=player.name.upper(), anchor="e", fill="white",
                      font="Helvetica 15 bold", tags="fg")
        c.create_text(360, y + 8, text=str(player.chips) + " chips", anchor="e",
                      fill="#ffd966", font="Helvetica 13", tags="fg")
        if player is self.first and len(self.you.hand) > 0:
            c.create_text(360, y + 30, text="acts first", anchor="e", fill="#9fd8b5",
                          font="Helvetica 10", tags="fg")
        self.pile(PILE_X, y + 18, player.chips, max(1, self.start // 4))

        # ante label: floats up and fades into the felt while it lasts
        if now < player.ante_until:
            age = 1.2 - (player.ante_until - now)
            rise = age * 14

            # stays fully visible for the first half, then fades
            t = max(0, (age / 1.2 - 0.5) * 2)
            color = mix("#ff9f9f", FELT, t)

            c.create_text(PILE_X - 24, y + 18 - rise, text="ante -" + str(player.ante_paid),
                          anchor="e", fill=color, font="Helvetica 12 bold", tags="fg")

    def draw_bet(self, player, y):
        if player.paid <= 0:
            return
        self.pile(450, y, player.paid, max(1, self.start // 20))
        self.canvas.create_text(474, y - 4, text=str(player.paid), anchor="w", fill="white",
                                font="Helvetica 13 bold", tags="fg")

    def draw_bubble(self, player, y, now):
        left = player.say_until - now
        if player.say == "" or left <= 0:
            return

        # solid for most of its life, then every color blends into the felt
        t = max(0, 1 - left / 0.6)
        fill = mix("#ffffff", FELT, t)
        edge = mix("#333333", FELT, t)
        ink = mix("#222222", FELT, t)

        w = 26 + 8 * len(player.say)
        self.rounded(620 - w / 2, y - 15, 620 + w / 2, y + 15, 10, fill, edge)
        self.canvas.create_text(620, y, text=player.say, fill=ink,
                                font="Helvetica 12 bold", tags="fg")

    def draw(self, now):
        c = self.canvas
        c.delete("fg")

        for i in range(3):
            self.draw_back(DECK_X - i * 2, DECK_Y - i * 2, CARD_W)

        self.draw_panel(self.bot, BOT_Y, now)
        self.draw_panel(self.you, YOU_Y, now)
        self.draw_bet(self.bot, BOT_BET_Y)
        self.draw_bet(self.you, YOU_BET_Y)

        # the pile only shows chips that have actually landed
        shown = self.pot - self.you.paid - self.bot.paid - self.in_flight
        if shown > 0:
            self.pile(POT_X, POT_Y, shown, max(1, self.start // 10))
            c.create_text(POT_X, POT_Y + 24, text="pot " + str(shown), fill="white",
                          font="Helvetica 14 bold", tags="fg")

        for card in self.you.hand + self.bot.hand + self.board:
            self.draw_card(card)

        for chip in self.chips_flying:
            self.draw_chip(chip.x, chip.y + hop(chip, now), chip.color)

        self.draw_bubble(self.bot, BOT_Y, now)
        self.draw_bubble(self.you, YOU_Y, now)

        if len(self.board) >= 3 and len(self.you.hand) == 2:
            name = HAND_NAMES[best_five(self.you.hand + self.board)[0][0]]
            c.create_text(450, 487, text="you have: " + name, fill="#d9f2e3",
                          font="Helvetica 12 italic", tags="fg")

        text = self.message
        if self.thinking:
            text += "." * (int(now * 3) % 4)
        c.create_text(450, 20, text=text, fill="#f5f5f5", font="Helvetica 15 bold", tags="fg")

        if len(self.you.hand) > 0:
            c.create_text(20, 20, text=STAGES[self.stage].upper(), anchor="w",
                          fill="#9a8f84", font="Helvetica 12 bold", tags="fg")

        net = self.you.chips - self.bought
        net_text = str(net)
        if net >= 0:
            net_text = "+" + str(net)
        c.create_text(880, 20, anchor="e", fill="#9a8f84", font="Helvetica 11", tags="fg",
                      text="bought in " + str(self.bought) + "   net " + net_text)

    def frame(self):
        now = time.time()

        for card in self.you.hand + self.bot.hand + self.board:
            glide(card, now)
            if card.arrived(now):
                if card.open < card.want_open:
                    card.open = min(card.want_open, card.open + 0.08)
                elif card.open > card.want_open:
                    card.open = max(card.want_open, card.open - 0.08)

        for chip in self.chips_flying:
            glide(chip, now)
            if chip.landed is None and now >= chip.delay:
                if chip.x == chip.tx and chip.y == chip.ty:
                    chip.landed = now

        self.draw(now)
        self.root.after(FRAME_MS, self.frame)


def main():
    root = tk.Tk()
    root.resizable(False, False)
    Game(root)
    root.mainloop()


if __name__ == "__main__":
    main()