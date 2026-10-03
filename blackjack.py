import array
import math
import random
import shutil
import subprocess
import sys
import tempfile
import time
import tkinter as tk
import wave
from tkinter import messagebox, simpledialog

# winsound only exists on Windows
if sys.platform == "win32":
    import winsound

W = 900
H = 540
CARD_W = 64
CARD_H = 90
FRAME_MS = 16
MAX_CHIPS = 100000
DEALER_STAND = 17

DECK_X = 120
DECK_Y = 270
DEALER_CARD_Y = 160
YOU_CARD_Y = 365
DEALER_PANEL_Y = 70
YOU_PANEL_Y = 462
PILE_X = 330
BET_X = 730
BET_Y = 290
FELT = "#1d7a4a"

SUITS = "♠♥♦♣"
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
CHIP_COLORS = ["#d63031", "#0984e3", "#00b894", "#2d3436", "#e1b12c"]


def mix(c1, c2, t):
    # blend two "#rrggbb" colors, t=0 gives c1 and t=1 gives c2
    result = "#"
    for i in range(1, 7, 2):
        a = int(c1[i:i + 2], 16)
        b = int(c2[i:i + 2], 16)
        result += format(int(a + (b - a) * t), "02x")
    return result


# ---------- sound ----------
# Every sound is built from numbers: a sine wave for a ring or a ping,
# random noise for clicks and rustles. Each one fades out quickly,
# which is what makes it sound like an object and not a beep.

RATE = 22050   # samples per second


def silence(seconds):
    samples = []
    for i in range(int(seconds * RATE)):
        samples.append(0.0)
    return samples


def tone(samples, start, length, freq, volume, decay):
    # add a fading sine wave into samples, beginning at index start
    for i in range(length):
        if start + i >= len(samples):
            return
        t = i / RATE
        samples[start + i] += math.sin(2 * math.pi * freq * t) * volume * math.exp(-decay * t)


def noise(samples, start, length, volume, decay, smooth):
    # add a fading burst of random noise; a higher smooth makes it duller
    last = 0.0
    for i in range(length):
        if start + i >= len(samples):
            return
        t = i / RATE
        last = last * smooth + random.uniform(-1, 1) * (1 - smooth)
        samples[start + i] += last * volume * math.exp(-decay * t)


def make_chips():
    # four quick clicks, like chips being dropped onto each other
    samples = silence(0.4)
    offsets = [0.0, 0.07, 0.12, 0.2]
    for offset in offsets:
        start = int(offset * RATE)
        tone(samples, start, int(0.12 * RATE), 2600, 0.5, 60)
        tone(samples, start, int(0.10 * RATE), 3900, 0.25, 80)
        noise(samples, start, int(0.03 * RATE), 0.6, 150, 0.2)
    return samples


def make_shuffle():
    # a riffle: lots of tiny rustles, then a soft thump as the halves merge
    samples = silence(0.95)
    for i in range(30):
        start = int((i * 0.026 + random.uniform(0, 0.01)) * RATE)
        noise(samples, start, int(0.022 * RATE), 0.5, 110, 0.5)
    tone(samples, int(0.8 * RATE), int(0.12 * RATE), 110, 0.5, 30)
    return samples


def make_win():
    # a rising four note jingle: C E G and a high C
    samples = silence(0.9)
    notes = [523, 659, 784, 1047]
    for i in range(len(notes)):
        start = int(i * 0.12 * RATE)
        tone(samples, start, int(0.4 * RATE), notes[i], 0.45, 6)
        tone(samples, start, int(0.4 * RATE), notes[i] * 2, 0.15, 9)
    return samples


def save_wav(path, samples):
    # scale to fit, turn the numbers into 16 bit whole numbers and write the file
    peak = 0.001
    for value in samples:
        if abs(value) > peak:
            peak = abs(value)

    data = array.array("h")
    for value in samples:
        data.append(int(value / peak * 0.8 * 32767))

    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(data.tobytes())


class Sound:
    def __init__(self):
        self.on = True
        self.folder = tempfile.mkdtemp()   # the sounds live here until you quit
        self.names = []
        self.paths = []
        self.procs = []      # players that are still running (Mac and Linux)
        self.player = None   # None means no way to play sound was found

        self.make("chips", make_chips())
        self.make("shuffle", make_shuffle())
        self.make("win", make_win())
        self.find_player()

    def make(self, name, samples):
        path = self.folder + "/" + name + ".wav"
        save_wav(path, samples)
        self.names.append(name)
        self.paths.append(path)

    def find_player(self):
        if sys.platform == "win32":
            self.player = "winsound"
        elif sys.platform == "darwin":
            self.player = "afplay"
        else:
            for command in ["paplay", "aplay", "play"]:
                if shutil.which(command) is not None:
                    self.player = command
                    break

    def play(self, name):
        if not self.on or self.player is None:
            return
        path = self.paths[self.names.index(name)]

        if self.player == "winsound":
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return

        # forget players that have finished, so they don't pile up
        running = []
        for proc in self.procs:
            if proc.poll() is None:
                running.append(proc)
        self.procs = running

        self.procs.append(subprocess.Popen([self.player, path],
                                           stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL))

    def cleanup(self):
        shutil.rmtree(self.folder, ignore_errors=True)


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

    def points(self):
        if self.rank == "A":
            return 11
        if self.rank == "J" or self.rank == "Q" or self.rank == "K":
            return 10
        return int(self.rank)

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


class Hand:
    # one hand of cards with its own bet. After a split you have two of these.
    def __init__(self):
        self.cards = []
        self.bet = 0
        self.shown = 0       # the total drawn on screen
        self.label = ""      # result text for a split hand, like "WIN +50"
        self.label_color = "white"


class Player:
    def __init__(self, name, chips):
        self.name = name
        self.chips = chips
        self.hands = [Hand()]
        self.say = ""
        self.say_until = 0

    def pay(self, amount):
        amount = min(amount, self.chips)
        self.chips -= amount
        return amount


# ---------- helpers ----------

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


def make_deck():
    deck = []
    for suit in SUITS:
        for rank in RANKS:
            deck.append(Card(rank, suit))
    random.shuffle(deck)
    return deck


def hand_total(cards):
    total = 0
    aces = 0
    for card in cards:
        total += card.points()
        if card.rank == "A":
            aces += 1
    # an ace counts as 1 instead of 11 if we would bust otherwise
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def is_blackjack(cards):
    return len(cards) == 2 and hand_total(cards) == 21


# ---------- the game ----------

class Game:
    def __init__(self, root):
        self.root = root
        root.title("Blackjack")
        root.configure(bg="#120d0a")

        self.canvas = tk.Canvas(root, width=W, height=H, highlightthickness=0, bg="#120d0a")
        self.canvas.pack()

        self.sound = Sound()
        root.protocol("WM_DELETE_WINDOW", self.quit_game)

        self.you = Player("you", 0)
        self.dealer = Player("dealer", 0)
        self.deck = []
        self.chips_flying = []
        self.start = 1000
        self.bought = 0
        self.min_bet = 20
        self.phase = "wait"    # idle, insure, you or wait: what the game is waiting for
        self.message = "starting..."
        self.game_over = False
        self.active = 0        # which of your hands is being played
        self.did_split = False # a 21 after a split is not a blackjack
        self.reveal = False    # True once the dealer's hidden card is turned over
        self.show_bet = False
        self.bet_show = 0
        self.banner = ""
        self.banner_color = "white"
        self.you_gets = 0      # chips that go back to you at the end of the hand
        self.dealer_change = 0 # how the dealer's stack changes
        self.insurance = 0     # chips staked on insurance this hand

        self.draw_table()
        self.build_controls()
        root.bind("<Key>", self.on_key)

        self.update_controls()
        self.frame()
        root.after(300, self.new_game)

    def quit_game(self):
        self.sound.cleanup()
        self.root.destroy()

    def sound_chips(self):
        self.sound.play("chips")

    def build_controls(self):
        bar = tk.Frame(self.root, bg="#120d0a")
        bar.pack(fill="x", pady=8)

        font = "Helvetica 12"
        self.btn_deal = tk.Button(bar, text="Deal", width=10, font=font, command=self.deal)
        self.btn_deal.pack(side="left", padx=(14, 3))

        self.amount = tk.IntVar(value=0)
        self.scale = tk.Scale(bar, from_=0, to=1, orient="horizontal", variable=self.amount,
                              length=170, showvalue=0, bg="#120d0a", highlightthickness=0)
        self.scale.pack(side="left", padx=6)

        self.btn_allin = tk.Button(bar, text="All in", width=6, font=font, command=self.do_allin)
        self.btn_allin.pack(side="left", padx=3)
        self.btn_add = tk.Button(bar, text="Add chips", width=9, font=font, command=self.add_more)
        self.btn_add.pack(side="left", padx=3)

        # during the insurance offer, Hit and Stand become "Insure" and "No thanks"
        self.btn_hit = tk.Button(bar, text="Hit", width=9, font=font, command=self.do_hit)
        self.btn_hit.pack(side="left", padx=(20, 3))
        self.btn_stand = tk.Button(bar, text="Stand", width=9, font=font, command=self.do_stand)
        self.btn_stand.pack(side="left", padx=3)
        self.btn_double = tk.Button(bar, text="Double", width=7, font=font, command=self.do_double)
        self.btn_double.pack(side="left", padx=3)
        self.btn_split = tk.Button(bar, text="Split", width=6, font=font, command=self.do_split)
        self.btn_split.pack(side="left", padx=3)

        self.scale.config(command=self.on_scale)

    def on_key(self, event):
        key = event.keysym.lower()
        if key == "space":
            self.deal()
        elif key == "h":
            self.do_hit()
        elif key == "s":
            self.do_stand()
        elif key == "d":
            self.do_double()
        elif key == "p":
            self.do_split()
        elif key == "i":
            self.do_insure()
        elif key == "n":
            self.do_decline()
        elif key == "m":
            self.sound.on = not self.sound.on

    def on_scale(self, value=None):
        self.btn_deal.config(text="Deal " + str(self.amount.get()))

    def hand_y(self, player):
        if player is self.you:
            return YOU_CARD_Y
        return DEALER_CARD_Y

    def hand_x(self, player, k):
        # one hand sits in the middle, two hands sit left and right
        if len(player.hands) == 1:
            return 450
        return 270 + k * 340

    def all_cards(self):
        cards = []
        for player in [self.you, self.dealer]:
            for hand in player.hands:
                cards = cards + hand.cards
        return cards

    def total_bet(self):
        total = 0
        for hand in self.you.hands:
            total += hand.bet
        return total

    # ---------- setting up games and hands ----------

    def new_game(self):
        start = simpledialog.askinteger("Blackjack", "starting chips (100-" + str(MAX_CHIPS) + ")",
                                        parent=self.root, minvalue=100, maxvalue=MAX_CHIPS)
        if start is None:
            start = 1000

        self.start = start
        self.bought = start
        self.min_bet = max(1, start // 50)
        self.you = Player("you", start)
        self.dealer = Player("dealer", start)
        self.active = 0
        self.insurance = 0
        self.game_over = False
        self.banner = ""
        self.show_bet = False
        self.phase = "idle"
        self.message = "choose your bet and press deal"
        self.update_controls()

    def layout(self, player):
        # spread the cards of each hand evenly around that hand's center
        for k in range(len(player.hands)):
            hand = player.hands[k]
            n = len(hand.cards)
            gap = 76
            if len(player.hands) > 1:
                gap = 36   # split hands sit closer so both fit on the table
            for i in range(n):
                card = hand.cards[i]
                card.tx = self.hand_x(player, k) - (n - 1) * gap / 2 + i * gap
                card.ty = self.hand_y(player)

    def add_card(self, player, hand, delay, face_up):
        card = self.deck.pop()
        card.delay = delay
        card.want_open = face_up
        hand.cards.append(card)
        self.layout(player)

    def send_bet_chips(self, now, count, lag=0):
        # lag is how many milliseconds to wait before the clack plays
        for i in range(count):
            self.chips_flying.append(Chip(PILE_X, YOU_PANEL_Y + 15 - i * 5,
                                          BET_X + random.randint(-8, 8),
                                          BET_Y + random.randint(-5, 5),
                                          now + i * 0.06,
                                          CHIP_COLORS[i % len(CHIP_COLORS)]))
        self.root.after(lag, self.sound_chips)
        self.root.after(1200, self.land_chips)

    def land_chips(self):
        self.chips_flying = []

    def deal(self, event=None):
        if self.phase != "idle":
            return
        if self.game_over:
            self.new_game()
            return

        bet = self.amount.get()
        bet = min(bet, self.you.chips)
        bet = max(bet, min(self.min_bet, self.you.chips))

        now = time.time()
        self.deck = make_deck()
        self.sound.play("shuffle")
        self.chips_flying = []
        self.you.hands = [Hand()]
        self.dealer.hands = [Hand()]
        self.you.say = ""
        self.dealer.say = ""
        self.active = 0
        self.did_split = False
        self.insurance = 0
        self.reveal = False
        self.banner = ""

        self.you.hands[0].bet = self.you.pay(bet)
        self.send_bet_chips(now, 3, 700)   # wait for the shuffle to finish
        self.show_bet = True
        self.bet_show = now + 1.0

        # you, dealer, you, dealer; the dealer's second card stays face down
        self.add_card(self.you, self.you.hands[0], now + 0.3, 1.0)
        self.add_card(self.dealer, self.dealer.hands[0], now + 0.55, 1.0)
        self.add_card(self.you, self.you.hands[0], now + 0.8, 1.0)
        self.add_card(self.dealer, self.dealer.hands[0], now + 1.05, 0.0)

        self.phase = "wait"
        self.message = "dealing..."
        self.update_controls()
        self.root.after(2000, self.check_naturals)

    def add_chips(self, amount):
        # the dealer always gets the same amount, so the stacks stay even
        self.you.chips += amount
        self.dealer.chips += amount
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
            self.message = "added " + str(amount) + " for you and the dealer"
            self.update_controls()

    def do_allin(self):
        if self.phase != "idle" or self.game_over:
            return
        self.amount.set(self.you.chips)
        self.deal()

    # ---------- the hand ----------

    def say(self, player, text):
        player.say = text
        player.say_until = time.time() + 2.4

    def turn_message(self):
        if len(self.you.hands) > 1:
            return "hand " + str(self.active + 1) + " of " + str(len(self.you.hands))
        return "your turn"

    def refresh_totals(self):
        for hand in self.you.hands:
            hand.shown = hand_total(hand.cards)

        dealer_hand = self.dealer.hands[0]
        if len(dealer_hand.cards) == 0:
            dealer_hand.shown = 0
        elif self.reveal:
            dealer_hand.shown = hand_total(dealer_hand.cards)
        else:
            dealer_hand.shown = hand_total([dealer_hand.cards[0]])

    def reveal_dealer(self):
        self.reveal = True
        self.dealer.hands[0].cards[1].want_open = 1.0
        self.root.after(400, self.refresh_totals)

    # ---------- insurance and naturals ----------

    def insurance_cost(self):
        return self.you.hands[0].bet // 2

    def can_insure(self):
        cost = self.insurance_cost()
        return cost >= 1 and self.you.chips >= cost

    def check_naturals(self):
        self.refresh_totals()
        up_card = self.dealer.hands[0].cards[0]

        # an ace showing means the dealer might have blackjack, so offer insurance
        if up_card.rank == "A" and self.can_insure():
            self.phase = "insure"
            self.message = "dealer shows an ace: insurance?"
            self.update_controls()
            return
        self.peek()

    def do_insure(self):
        if self.phase != "insure":
            return
        self.phase = "wait"
        self.insurance = self.you.pay(self.insurance_cost())
        self.send_bet_chips(time.time(), 2)
        self.say(self.you, "insurance")
        self.update_controls()
        self.root.after(1300, self.peek)

    def do_decline(self):
        if self.phase != "insure":
            return
        self.phase = "wait"
        self.say(self.you, "no thanks")
        self.update_controls()
        self.root.after(700, self.peek)

    def peek(self):
        # the dealer checks the hidden card for blackjack
        you_bj = is_blackjack(self.you.hands[0].cards)
        dealer_bj = is_blackjack(self.dealer.hands[0].cards)

        if self.insurance > 0 and not dealer_bj:
            self.say(self.dealer, "no blackjack")

        if you_bj or dealer_bj:
            if you_bj:
                self.say(self.you, "blackjack!")
            if dealer_bj:
                self.say(self.dealer, "blackjack!")
            self.phase = "wait"
            self.reveal_dealer()
            self.update_controls()
            self.root.after(1300, self.settle)
            return

        self.phase = "you"
        self.message = self.turn_message()
        self.update_controls()

    # ---------- your moves ----------

    def do_hit(self):
        if self.phase == "insure":
            self.do_insure()
            return
        if self.phase != "you":
            return
        self.phase = "wait"
        self.say(self.you, "hit")
        self.add_card(self.you, self.you.hands[self.active], time.time(), 1.0)
        self.update_controls()
        self.root.after(900, self.after_player_card)

    def do_stand(self):
        if self.phase == "insure":
            self.do_decline()
            return
        if self.phase != "you":
            return
        self.phase = "wait"
        self.say(self.you, "stand")
        self.update_controls()
        self.root.after(600, self.finish_hand)

    def do_double(self):
        if self.phase != "you":
            return
        hand = self.you.hands[self.active]
        if len(hand.cards) != 2 or self.you.chips < hand.bet:
            return
        self.phase = "wait"
        hand.bet += self.you.pay(hand.bet)
        self.send_bet_chips(time.time(), 3)
        self.say(self.you, "double")
        self.add_card(self.you, hand, time.time() + 0.3, 1.0)
        self.update_controls()
        self.root.after(1300, self.after_double)

    def can_split(self):
        if len(self.you.hands) != 1:
            return False   # only one split per round
        hand = self.you.hands[0]
        if len(hand.cards) != 2:
            return False
        if hand.cards[0].rank != hand.cards[1].rank:
            return False
        return self.you.chips >= hand.bet

    def do_split(self):
        if self.phase != "you" or not self.can_split():
            return
        self.phase = "wait"
        first = self.you.hands[0]

        # the second card moves to a new hand with its own bet
        second = Hand()
        second.cards.append(first.cards.pop())
        second.bet = self.you.pay(first.bet)
        self.you.hands.append(second)
        self.did_split = True

        self.send_bet_chips(time.time(), 3)
        self.say(self.you, "split")
        self.layout(self.you)
        self.add_card(self.you, first, time.time() + 0.3, 1.0)
        self.message = self.turn_message()
        self.update_controls()
        self.root.after(1300, self.after_player_card)

    def after_player_card(self):
        # called after a card lands on the hand you are playing
        self.refresh_totals()
        total = hand_total(self.you.hands[self.active].cards)
        if total > 21:
            self.say(self.you, "bust")
            self.root.after(900, self.finish_hand)
        elif total == 21:
            self.root.after(600, self.finish_hand)
        else:
            self.phase = "you"
            self.message = self.turn_message()
            self.update_controls()

    def after_double(self):
        self.refresh_totals()
        if hand_total(self.you.hands[self.active].cards) > 21:
            self.say(self.you, "bust")
        self.root.after(700, self.finish_hand)

    def finish_hand(self):
        # the hand you were playing is done: go to your next hand, or the dealer
        if self.active + 1 < len(self.you.hands):
            self.active += 1
            hand = self.you.hands[self.active]
            self.message = self.turn_message()
            if len(hand.cards) == 1:   # the split hand still needs its second card
                self.add_card(self.you, hand, time.time(), 1.0)
            self.update_controls()
            self.root.after(900, self.after_player_card)
            return

        # if every hand busted, the dealer doesn't need to play
        alive = False
        for hand in self.you.hands:
            if hand_total(hand.cards) <= 21:
                alive = True

        if alive:
            self.dealer_turn()
        else:
            self.reveal_dealer()
            self.root.after(1200, self.settle)

    def dealer_turn(self):
        self.phase = "wait"
        self.message = "dealer's turn"
        self.update_controls()
        self.reveal_dealer()
        self.root.after(1000, self.dealer_step)

    def dealer_step(self):
        dealer_hand = self.dealer.hands[0]
        total = hand_total(dealer_hand.cards)
        if total < DEALER_STAND:
            self.say(self.dealer, "hit")
            self.add_card(self.dealer, dealer_hand, time.time(), 1.0)
            self.root.after(900, self.refresh_totals)
            self.root.after(1300, self.dealer_step)
        else:
            self.refresh_totals()
            if total > 21:
                self.say(self.dealer, "bust")
            else:
                self.say(self.dealer, "stand")
            self.root.after(1100, self.settle)

    # ---------- ending a hand ----------

    def settle(self):
        self.phase = "wait"
        dealer_cards = self.dealer.hands[0].cards
        theirs = hand_total(dealer_cards)
        dealer_bj = is_blackjack(dealer_cards)

        avail = self.dealer.chips   # the dealer can only pay what it has
        self.you_gets = 0
        self.dealer_change = 0
        message = ""

        # insurance is settled first, and counts as money you put in
        total_bet = self.insurance
        ins_text = ""
        if self.insurance > 0:
            if dealer_bj:
                pay = min(self.insurance * 2, avail)   # the dealer can only pay what it has
                avail -= pay
                self.you_gets += self.insurance + pay
                self.dealer_change -= pay
                ins_text = "insurance +" + str(pay)
            else:
                self.dealer_change += self.insurance
                avail += self.insurance
                ins_text = "insurance -" + str(self.insurance)

        for k in range(len(self.you.hands)):
            hand = self.you.hands[k]
            bet = hand.bet
            mine = hand_total(hand.cards)
            # a 21 on two cards after a split is just 21
            you_bj = (not self.did_split) and is_blackjack(hand.cards)

            win = 0
            result = "lose"
            if you_bj and not dealer_bj:
                win = int(bet * 1.5)
                result = "win"
                text = "blackjack! you win "
            elif mine > 21:
                text = "bust, you lose "
            elif dealer_bj and not you_bj:
                text = "dealer blackjack, you lose "
            elif you_bj and dealer_bj:
                result = "push"
                text = "both blackjack, push"
            elif theirs > 21:
                win = bet
                result = "win"
                text = "dealer busts, you win "
            elif mine > theirs:
                win = bet
                result = "win"
                text = "you win "
            elif mine < theirs:
                text = "dealer wins, you lose "
            else:
                result = "push"
                text = "push, bet returned"

            win = min(win, avail)

            if result == "win":
                avail -= win
                self.you_gets += bet + win
                self.dealer_change -= win
                hand.label = "WIN +" + str(win)
                hand.label_color = "#ffd966"
                text += str(win)
                for card in hand.cards:
                    card.glow = True
            elif result == "push":
                self.you_gets += bet
                hand.label = "PUSH"
                hand.label_color = "white"
            else:
                self.dealer_change += bet
                avail += bet
                hand.label = "LOSE -" + str(bet)
                hand.label_color = "#ff8a80"
                text += str(bet)

            if len(self.you.hands) == 1:
                message = text
            else:
                message += "hand " + str(k + 1) + ": " + hand.label + "     "
            total_bet += bet

        net = self.you_gets - total_bet
        if net > 0:
            self.banner = "WIN +" + str(net)
            self.banner_color = "#ffd966"
            self.sound.play("win")
        elif net < 0:
            self.banner = "LOSE -" + str(0 - net)
            self.banner_color = "#ff8a80"
        else:
            self.banner = "PUSH"
            if len(self.you.hands) > 1 or self.insurance > 0:
                self.banner = "EVEN"
            self.banner_color = "white"

        if ins_text != "":
            message += "   " + ins_text
        self.message = message
        self.update_controls()
        self.root.after(1300, self.start_payout)

    def start_payout(self):
        now = time.time()
        self.show_bet = False
        self.chips_flying = []

        # the bet pile goes to whoever gets it
        ty = DEALER_PANEL_Y + 15
        if self.you_gets > 0:
            ty = YOU_PANEL_Y + 15
        for i in range(6):
            self.chips_flying.append(Chip(BET_X + random.randint(-8, 8),
                                          BET_Y + random.randint(-5, 5),
                                          PILE_X, ty, now + i * 0.08,
                                          CHIP_COLORS[i % len(CHIP_COLORS)]))

        # a win is paid by the dealer, so chips also fly from its stack to yours
        if self.you_gets > self.total_bet() + self.insurance:
            for i in range(4):
                self.chips_flying.append(Chip(PILE_X, DEALER_PANEL_Y + 15 - i * 5,
                                              PILE_X + 14, YOU_PANEL_Y + 15,
                                              now + 0.3 + i * 0.08,
                                              CHIP_COLORS[i % len(CHIP_COLORS)]))
        self.root.after(450, self.sound_chips)
        self.root.after(1500, self.finish_payout)

    def finish_payout(self):
        self.you.chips += self.you_gets
        self.dealer.chips += self.dealer_change
        for hand in self.you.hands:
            hand.bet = 0
        self.insurance = 0
        self.chips_flying = []
        self.phase = "idle"
        self.message = "choose your bet and press deal"

        if self.dealer.chips < self.min_bet:
            self.dealer.chips += self.start
            self.message = "dealer rebought " + str(self.start)

        self.check_game()
        self.update_controls()

    def check_game(self):
        if self.you.chips >= self.min_bet:
            return

        self.message = "you're out of chips"
        if messagebox.askyesno("Out of chips", "rebuy?", parent=self.root):
            room = MAX_CHIPS - self.you.chips
            amount = simpledialog.askinteger("Rebuy",
                                             "chips to add (" + str(self.min_bet) + "-" + str(room) + ")",
                                             parent=self.root, minvalue=self.min_bet, maxvalue=room)
            if amount is not None:
                self.add_chips(amount)
                self.message = "rebought " + str(amount)
                return
        self.game_over = True
        self.message = "game over"

    # ---------- buttons on and off ----------

    def update_controls(self):
        off = "disabled"
        self.btn_hit.config(state=off, text="Hit")
        self.btn_stand.config(state=off, text="Stand")
        self.btn_double.config(state=off)
        self.btn_split.config(state=off)
        self.btn_deal.config(state=off, text="Deal")
        self.btn_allin.config(state=off)
        self.btn_add.config(state=off)
        self.scale.config(state=off)

        if self.phase == "insure":
            self.btn_hit.config(state="normal", text="Insure " + str(self.insurance_cost()))
            self.btn_stand.config(state="normal", text="No thanks")

        if self.phase == "you":
            hand = self.you.hands[self.active]
            self.btn_hit.config(state="normal")
            self.btn_stand.config(state="normal")
            if len(hand.cards) == 2 and self.you.chips >= hand.bet:
                self.btn_double.config(state="normal")
            if self.can_split():
                self.btn_split.config(state="normal")

        if self.phase == "idle":
            self.btn_deal.config(state="normal")
            if self.game_over:
                self.btn_deal.config(text="New game")
            else:
                high = self.you.chips
                low = min(self.min_bet, high)
                self.scale.config(from_=low, to=high, state="normal")
                value = self.amount.get()
                value = max(low, min(value, high))   # keep your last bet if it still fits
                self.amount.set(value)
                self.btn_allin.config(state="normal")
                self.btn_add.config(state="normal")
                self.on_scale()

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

    def draw_panel(self, player, y):
        c = self.canvas
        c.create_text(450, y - 14, text=player.name.upper(), fill="white",
                      font="Helvetica 15 bold", tags="fg")
        c.create_text(450, y + 10, text=str(player.chips) + " chips", fill="#ffd966",
                      font="Helvetica 13", tags="fg")
        self.pile(PILE_X, y + 15, player.chips, max(1, self.start // 4))

    def draw_total(self, total, x, y):
        if total <= 0:
            return
        color = "#d9f2e3"
        text = str(total)
        if total > 21:
            color = "#ff8a80"
            text = str(total) + " bust"
        self.canvas.create_text(x, y, text=text, fill=color,
                                font="Helvetica 15 bold", tags="fg")

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
        self.rounded(780 - w / 2, y - 15, 780 + w / 2, y + 15, 10, fill, edge)
        self.canvas.create_text(780, y, text=player.say, fill=ink,
                                font="Helvetica 12 bold", tags="fg")

    def draw_hand_marks(self):
        # totals above each of your hands, and the split extras
        c = self.canvas
        self.draw_total(self.dealer.hands[0].shown, 450, DEALER_CARD_Y + 62)

        count = len(self.you.hands)
        for k in range(count):
            hand = self.you.hands[k]
            x = self.hand_x(self.you, k)
            self.draw_total(hand.shown, x, YOU_CARD_Y - 62)

            if count > 1:
                # a gold bar shows which hand you are playing right now
                if self.phase == "you" and k == self.active:
                    c.create_line(x - 70, YOU_CARD_Y + 56, x + 70, YOU_CARD_Y + 56,
                                  fill="#f1c40f", width=4, tags="fg")
                if hand.label != "":
                    c.create_text(x, YOU_CARD_Y + 68, text=hand.label, fill=hand.label_color,
                                  font="Helvetica 13 bold", tags="fg")

    def draw(self, now):
        c = self.canvas
        c.delete("fg")

        for i in range(3):
            self.draw_back(DECK_X - i * 2, DECK_Y - i * 2, CARD_W)

        self.draw_panel(self.dealer, DEALER_PANEL_Y)
        self.draw_panel(self.you, YOU_PANEL_Y)

        total_bet = self.total_bet()
        if self.show_bet and total_bet > 0 and now >= self.bet_show:
            self.pile(BET_X, BET_Y, total_bet, max(1, self.start // 20))
            c.create_text(BET_X, BET_Y + 24, text="bet " + str(total_bet), fill="white",
                          font="Helvetica 13 bold", tags="fg")

        if self.show_bet and self.insurance > 0 and now >= self.bet_show:
            c.create_text(BET_X, BET_Y + 42, text="insurance " + str(self.insurance),
                          fill="#ffd966", font="Helvetica 12 bold", tags="fg")

        for card in self.all_cards():
            self.draw_card(card)

        for chip in self.chips_flying:
            self.draw_chip(chip.x, chip.y + hop(chip, now), chip.color)

        self.draw_hand_marks()

        if self.banner != "":
            c.create_text(452, 262, text=self.banner, fill="#0c3a24",
                          font="Helvetica 26 bold", tags="fg")
            c.create_text(450, 260, text=self.banner, fill=self.banner_color,
                          font="Helvetica 26 bold", tags="fg")

        self.draw_bubble(self.dealer, DEALER_CARD_Y, now)
        self.draw_bubble(self.you, YOU_CARD_Y, now)

        c.create_text(450, 20, text=self.message, fill="#f5f5f5",
                      font="Helvetica 15 bold", tags="fg")

        net = self.you.chips + total_bet + self.insurance - self.bought
        net_text = str(net)
        if net >= 0:
            net_text = "+" + str(net)
        c.create_text(880, 20, anchor="e", fill="#9a8f84", font="Helvetica 11", tags="fg",
                      text="bought in " + str(self.bought) + "   net " + net_text)

        label = "sound on (m)"
        if not self.sound.on:
            label = "sound off (m)"
        c.create_text(20, 20, anchor="w", fill="#9a8f84", font="Helvetica 11",
                      text=label, tags="fg")

    def frame(self):
        now = time.time()

        for card in self.all_cards():
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