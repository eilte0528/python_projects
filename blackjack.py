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
DEALER_Y = 150
YOU_Y = 380
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
# Every sound is built from numbers: a sine wave for a ping or a note,
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


def make_flick():
    # a short papery snap: a tiny burst of noise and a faint high tick
    samples = silence(0.08)
    noise(samples, 0, int(0.014 * RATE), 0.7, 300, 0.1)
    tone(samples, 0, int(0.05 * RATE), 1800, 0.3, 90)
    return samples


def make_lose():
    # two falling notes, a low "wah wah"
    samples = silence(0.7)
    notes = [330, 247]
    for i in range(len(notes)):
        start = int(i * 0.25 * RATE)
        tone(samples, start, int(0.4 * RATE), notes[i], 0.5, 5)
        tone(samples, start, int(0.4 * RATE), notes[i] * 1.5, 0.15, 7)
    return samples


def save_wav(path, samples, level):
    # scale to fit, turn the numbers into 16 bit whole numbers and write the file
    peak = 0.001
    for value in samples:
        if abs(value) > peak:
            peak = abs(value)

    data = array.array("h")
    for value in samples:
        data.append(int(value / peak * level * 32767))

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
        self.lengths = []    # how long each sound lasts, in seconds
        self.busy_until = 0  # a quiet sound waits until this time
        self.procs = []      # players that are still running (Mac and Linux)
        self.player = None   # None means no way to play sound was found

        self.make("chips", make_chips(), 0.8)
        self.make("shuffle", make_shuffle(), 0.8)
        self.make("win", make_win(), 0.8)
        self.make("flick", make_flick(), 0.35)   # quiet, it plays a lot
        self.make("lose", make_lose(), 0.7)
        self.find_player()

    def make(self, name, samples, level):
        path = self.folder + "/" + name + ".wav"
        save_wav(path, samples, level)
        self.names.append(name)
        self.paths.append(path)
        self.lengths.append(len(samples) / RATE)

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

    def play(self, name, soft=False):
        # a soft sound (the card flick) never interrupts another sound
        if not self.on or self.player is None:
            return
        now = time.time()
        if soft and now < self.busy_until:
            return

        i = self.names.index(name)
        path = self.paths[i]
        if not soft:
            self.busy_until = now + self.lengths[i]

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
        self.landed = False    # True once the flick sound has played

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


class Hand:
    # one hand of cards with its own bet. After a split you have two of these.
    def __init__(self):
        self.cards = []
        self.bet = 0
        self.label = ""          # result text for a hand, like "WIN +50"
        self.label_color = "white"


def glide(card, now):
    # slide a little closer to the target every frame
    if now < card.delay:
        return
    card.x += (card.tx - card.x) * 0.2
    card.y += (card.ty - card.y) * 0.2
    if abs(card.tx - card.x) < 0.5:
        card.x = card.tx
    if abs(card.ty - card.y) < 0.5:
        card.y = card.ty


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


def hand_x(count, k):
    # one hand sits in the middle, two hands sit left and right
    if count == 1:
        return 450
    return 270 + k * 340


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

        self.hands = [Hand()]    # your hands; two after a split
        self.dealer = Hand()
        self.active = 0          # which of your hands is being played
        self.did_split = False   # a 21 after a split is not a blackjack
        self.insurance = 0       # chips staked on insurance this hand
        self.deck = []
        self.chips = 0
        self.start = 1000
        self.bought = 0
        self.min_bet = 20
        self.phase = "wait"      # idle, insure, you or wait: what the game is waiting for
        self.message = "starting..."
        self.banner = ""
        self.banner_color = "white"
        self.reveal = False      # True once the dealer's hidden card is turned over
        self.game_over = False

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

    def sound_win(self):
        self.sound.play("win")

    def sound_lose(self):
        self.sound.play("lose")

    def build_controls(self):
        bar = tk.Frame(self.root, bg="#120d0a")
        bar.pack(fill="x", pady=8)
        font = "Helvetica 12"

        self.btn_deal = tk.Button(bar, text="Deal", width=10, font=font, command=self.deal)
        self.btn_deal.pack(side="left", padx=(14, 3))

        self.amount = tk.IntVar(value=0)
        self.scale = tk.Scale(bar, from_=0, to=1, orient="horizontal", variable=self.amount,
                              length=160, showvalue=0, bg="#120d0a", highlightthickness=0,
                              command=self.on_scale)
        self.scale.pack(side="left", padx=6)

        self.btn_allin = tk.Button(bar, text="All in", width=6, font=font, command=self.all_in)
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

    def all_cards(self):
        cards = self.dealer.cards[:]
        for hand in self.hands:
            cards = cards + hand.cards
        return cards

    def total_bet(self):
        total = 0
        for hand in self.hands:
            total += hand.bet
        return total

    # ---------- starting a game and a hand ----------

    def new_game(self):
        start = simpledialog.askinteger("Blackjack", "starting chips (100-" + str(MAX_CHIPS) + ")",
                                        parent=self.root, minvalue=100, maxvalue=MAX_CHIPS)
        if start is None:
            start = 1000
        self.start = start
        self.bought = start
        self.chips = start
        self.min_bet = max(1, start // 50)
        self.game_over = False
        self.insurance = 0
        self.hands = [Hand()]
        self.dealer = Hand()
        self.banner = ""
        self.phase = "idle"
        self.message = "choose your bet and press deal"
        self.update_controls()

    def layout(self, hands, y):
        # spread the cards of each hand evenly around that hand's center
        count = len(hands)
        gap = 76
        if count > 1:
            gap = 36   # split hands sit closer so both fit on the table
        for k in range(count):
            n = len(hands[k].cards)
            for i in range(n):
                card = hands[k].cards[i]
                card.tx = hand_x(count, k) - (n - 1) * gap / 2 + i * gap
                card.ty = y

    def add_card(self, hand, delay, face_up):
        # the dealer's hand is laid out by itself, yours with all your hands
        card = self.deck.pop()
        card.delay = delay
        card.want_open = face_up
        hand.cards.append(card)
        if hand is self.dealer:
            self.layout([self.dealer], DEALER_Y)
        else:
            self.layout(self.hands, YOU_Y)

    def deal(self, event=None):
        if self.phase != "idle":
            return
        if self.game_over:
            self.new_game()
            return

        bet = self.amount.get()
        bet = min(bet, self.chips)
        bet = max(bet, min(self.min_bet, self.chips))

        now = time.time()
        self.deck = make_deck()
        self.sound.play("shuffle")
        self.root.after(700, self.sound_chips)   # your bet lands after the shuffle
        self.hands = [Hand()]
        self.dealer = Hand()
        self.active = 0
        self.did_split = False
        self.insurance = 0
        self.reveal = False
        self.banner = ""
        self.hands[0].bet = bet
        self.chips -= bet

        # you, dealer, you, dealer; the dealer's second card stays face down
        self.add_card(self.hands[0], now + 0.3, 1.0)
        self.add_card(self.dealer, now + 0.55, 1.0)
        self.add_card(self.hands[0], now + 0.8, 1.0)
        self.add_card(self.dealer, now + 1.05, 0.0)

        self.phase = "wait"
        self.message = "dealing..."
        self.update_controls()
        self.root.after(1900, self.check_naturals)

    def add_more(self):
        if self.phase != "idle" or self.game_over:
            return
        room = MAX_CHIPS - self.chips
        if room < 1:
            return
        amount = simpledialog.askinteger("Add chips", "how many? (1-" + str(room) + ")",
                                         parent=self.root, minvalue=1, maxvalue=room)
        if amount is not None:
            self.chips += amount
            self.bought += amount
            self.update_controls()

    def all_in(self):
        if self.phase != "idle" or self.game_over:
            return
        self.amount.set(self.chips)
        self.deal()

    # ---------- insurance and naturals ----------

    def turn_message(self):
        if len(self.hands) > 1:
            return "hand " + str(self.active + 1) + " of " + str(len(self.hands))
        return "your turn"

    def insurance_cost(self):
        return self.hands[0].bet // 2

    def can_insure(self):
        cost = self.insurance_cost()
        return cost >= 1 and self.chips >= cost

    def check_naturals(self):
        # an ace showing means the dealer might have blackjack, so offer insurance
        if self.dealer.cards[0].rank == "A" and self.can_insure():
            self.phase = "insure"
            self.message = "dealer shows an ace: insurance?"
            self.update_controls()
            return
        self.peek()

    def do_insure(self):
        if self.phase != "insure":
            return
        self.phase = "wait"
        self.insurance = self.insurance_cost()
        self.chips -= self.insurance
        self.sound.play("chips")
        self.message = "insurance taken"
        self.update_controls()
        self.root.after(900, self.peek)

    def do_decline(self):
        if self.phase != "insure":
            return
        self.phase = "wait"
        self.update_controls()
        self.root.after(400, self.peek)

    def peek(self):
        # the dealer checks the hidden card; a blackjack on either side ends the hand
        if is_blackjack(self.hands[0].cards) or is_blackjack(self.dealer.cards):
            self.phase = "wait"
            self.flip_dealer()
            self.update_controls()
            self.root.after(1200, self.settle)
            return

        self.phase = "you"
        self.message = self.turn_message()
        if self.insurance > 0:
            self.message = "no dealer blackjack, insurance lost"
        self.update_controls()

    def flip_dealer(self):
        self.reveal = True
        self.dealer.cards[1].want_open = 1.0

    # ---------- playing the hand ----------

    def do_hit(self):
        if self.phase == "insure":
            self.do_insure()
            return
        if self.phase != "you":
            return
        self.phase = "wait"
        self.add_card(self.hands[self.active], time.time(), 1.0)
        self.update_controls()
        self.root.after(900, self.after_card)

    def after_card(self):
        # called after a card lands on the hand you are playing
        total = hand_total(self.hands[self.active].cards)
        if total >= 21:
            self.root.after(500, self.finish_hand)
        else:
            self.phase = "you"
            self.message = self.turn_message()
            self.update_controls()

    def do_stand(self):
        if self.phase == "insure":
            self.do_decline()
            return
        if self.phase != "you":
            return
        self.phase = "wait"
        self.update_controls()
        self.finish_hand()

    def do_double(self):
        # double the bet, take exactly one card, then stand
        if self.phase != "you":
            return
        hand = self.hands[self.active]
        if len(hand.cards) != 2 or self.chips < hand.bet:
            return
        self.phase = "wait"
        self.chips -= hand.bet
        self.sound.play("chips")
        hand.bet = hand.bet * 2
        self.add_card(hand, time.time(), 1.0)
        self.update_controls()
        self.root.after(1300, self.finish_hand)

    def can_split(self):
        if len(self.hands) != 1:
            return False   # only one split per round
        hand = self.hands[0]
        if len(hand.cards) != 2:
            return False
        if hand.cards[0].rank != hand.cards[1].rank:
            return False
        return self.chips >= hand.bet

    def do_split(self):
        if self.phase != "you" or not self.can_split():
            return
        self.phase = "wait"
        first = self.hands[0]

        # the second card moves to a new hand with its own bet
        second = Hand()
        second.cards.append(first.cards.pop())
        second.bet = first.bet
        self.chips -= first.bet
        self.sound.play("chips")
        self.hands.append(second)
        self.did_split = True

        self.layout(self.hands, YOU_Y)
        self.add_card(first, time.time() + 0.3, 1.0)
        self.message = self.turn_message()
        self.update_controls()
        self.root.after(1300, self.after_card)

    def finish_hand(self):
        # the hand you were playing is done: go to your next hand, or the dealer
        if self.active + 1 < len(self.hands):
            self.active += 1
            hand = self.hands[self.active]
            self.message = self.turn_message()
            if len(hand.cards) == 1:   # the split hand still needs its second card
                self.add_card(hand, time.time(), 1.0)
            self.update_controls()
            self.root.after(900, self.after_card)
            return

        # if every hand busted, the dealer doesn't need to draw
        alive = False
        for hand in self.hands:
            if hand_total(hand.cards) <= 21:
                alive = True

        if alive:
            self.dealer_turn()
        else:
            self.flip_dealer()
            self.root.after(1000, self.settle)

    def dealer_turn(self):
        self.phase = "wait"
        self.message = "dealer's turn"
        self.update_controls()
        self.flip_dealer()
        self.root.after(1000, self.dealer_step)

    def dealer_step(self):
        # the dealer draws until reaching 17, one card at a time
        if hand_total(self.dealer.cards) < DEALER_STAND:
            self.add_card(self.dealer, time.time(), 1.0)
            self.root.after(1100, self.dealer_step)
        else:
            self.root.after(500, self.settle)

    # ---------- ending a hand ----------

    def settle(self):
        theirs = hand_total(self.dealer.cards)
        dealer_bj = is_blackjack(self.dealer.cards)

        total_bet = self.insurance   # insurance counts as money you put in
        total_back = 0               # chips that come back to you, bets included
        message = ""

        ins_text = ""
        if self.insurance > 0:
            if dealer_bj:
                total_back += self.insurance * 3   # the stake plus 2 to 1
                ins_text = "insurance +" + str(self.insurance * 2)
            else:
                ins_text = "insurance -" + str(self.insurance)

        for k in range(len(self.hands)):
            hand = self.hands[k]
            bet = hand.bet
            mine = hand_total(hand.cards)
            # a 21 on two cards after a split is just 21
            you_bj = (not self.did_split) and is_blackjack(hand.cards)

            # win is how much you gain; the bet comes back on a win or a push
            win = 0
            result = "lose"
            if you_bj and dealer_bj:
                result = "push"
                text = "both blackjack, push"
            elif you_bj:
                win = int(bet * 1.5)
                result = "win"
                text = "blackjack! you win " + str(win)
            elif mine > 21:
                text = "bust, you lose " + str(bet)
            elif dealer_bj:
                text = "dealer blackjack, you lose " + str(bet)
            elif theirs > 21:
                win = bet
                result = "win"
                text = "dealer busts, you win " + str(win)
            elif mine > theirs:
                win = bet
                result = "win"
                text = "you win " + str(win)
            elif mine < theirs:
                text = "dealer wins, you lose " + str(bet)
            else:
                result = "push"
                text = "push, bet returned"

            if result == "win":
                total_back += bet + win
                hand.label = "WIN +" + str(win)
                hand.label_color = "#ffd966"
                for card in hand.cards:
                    card.glow = True
            elif result == "push":
                total_back += bet
                hand.label = "PUSH"
                hand.label_color = "white"
            else:
                hand.label = "LOSE -" + str(bet)
                hand.label_color = "#ff8a80"

            if len(self.hands) == 1:
                message = text
            else:
                message += "hand " + str(k + 1) + ": " + hand.label + "     "
            total_bet += bet

        if ins_text != "":
            message += "   " + ins_text

        # sounds: chips come back to you, then a jingle if you won or a wah if you lost
        if total_back > 0:
            self.sound.play("chips")
        if total_back > total_bet:
            self.root.after(500, self.sound_win)
        elif total_back < total_bet:
            self.root.after(500, self.sound_lose)

        self.chips += total_back
        net = total_back - total_bet
        if net > 0:
            self.banner = "WIN +" + str(net)
            self.banner_color = "#ffd966"
        elif net < 0:
            self.banner = "LOSE -" + str(0 - net)
            self.banner_color = "#ff8a80"
        else:
            self.banner = "PUSH"
            if len(self.hands) > 1 or self.insurance > 0:
                self.banner = "EVEN"
            self.banner_color = "white"

        self.message = message
        for hand in self.hands:
            hand.bet = 0
        self.insurance = 0
        self.phase = "wait"
        self.update_controls()
        self.root.after(1800, self.finish)

    def finish(self):
        self.phase = "idle"
        self.message = "choose your bet and press deal"
        if self.chips < self.min_bet:
            self.out_of_chips()
        self.update_controls()

    def out_of_chips(self):
        self.message = "you're out of chips"
        if messagebox.askyesno("Out of chips", "rebuy?", parent=self.root):
            room = MAX_CHIPS - self.chips
            amount = simpledialog.askinteger(
                "Rebuy", "chips to add (" + str(self.min_bet) + "-" + str(room) + ")",
                parent=self.root, minvalue=self.min_bet, maxvalue=room)
            if amount is not None:
                self.chips += amount
                self.bought += amount
                self.message = "rebought " + str(amount)
                return
        self.game_over = True
        self.message = "game over"

    def update_controls(self):
        # buttons are only on when the game is waiting for them
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
            hand = self.hands[self.active]
            self.btn_hit.config(state="normal")
            self.btn_stand.config(state="normal")
            if len(hand.cards) == 2 and self.chips >= hand.bet:
                self.btn_double.config(state="normal")
            if self.can_split():
                self.btn_split.config(state="normal")

        if self.phase == "idle":
            self.btn_deal.config(state="normal")
            if self.game_over:
                self.btn_deal.config(text="New game")
            else:
                high = self.chips
                low = min(self.min_bet, high)
                self.scale.config(from_=low, to=high, state="normal")
                value = max(low, min(self.amount.get(), high))   # keep your last bet if it fits
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

    def draw_total(self, cards, x, y, show_all):
        if len(cards) == 0:
            return
        if show_all:
            total = hand_total(cards)
        else:
            total = hand_total([cards[0]])   # the dealer shows only the open card
        color = "#d9f2e3"
        text = str(total)
        if total > 21:
            color = "#ff8a80"
            text = str(total) + " bust"
        self.canvas.create_text(x, y, text=text, fill=color,
                                font="Helvetica 15 bold", tags="fg")

    def draw_hand_marks(self):
        c = self.canvas
        self.draw_total(self.dealer.cards, 450, DEALER_Y + 62, self.reveal)

        count = len(self.hands)
        for k in range(count):
            hand = self.hands[k]
            x = hand_x(count, k)
            self.draw_total(hand.cards, x, YOU_Y - 62, True)

            if count > 1:
                # a gold bar shows which hand you are playing right now
                if self.phase == "you" and k == self.active:
                    c.create_line(x - 70, YOU_Y + 56, x + 70, YOU_Y + 56,
                                  fill="#f1c40f", width=4, tags="fg")
                if hand.label != "":
                    c.create_text(x, YOU_Y + 70, text=hand.label, fill=hand.label_color,
                                  font="Helvetica 13 bold", tags="fg")

    def draw(self, now):
        c = self.canvas
        c.delete("fg")

        for i in range(3):
            self.draw_back(DECK_X - i * 2, DECK_Y - i * 2, CARD_W)

        # names and chip stacks
        c.create_text(450, 70, text="DEALER", fill="white", font="Helvetica 15 bold", tags="fg")
        c.create_text(450, 468, text="YOU   " + str(self.chips) + " chips", fill="#ffd966",
                      font="Helvetica 14 bold", tags="fg")
        self.pile(300, 480, self.chips, max(1, self.start // 4))

        # your bet sits on the right
        total_bet = self.total_bet()
        if total_bet > 0:
            self.pile(760, 290, total_bet, max(1, self.start // 20))
            c.create_text(760, 314, text="bet " + str(total_bet), fill="white",
                          font="Helvetica 13 bold", tags="fg")

        if self.insurance > 0:
            c.create_text(760, 334, text="insurance " + str(self.insurance), fill="#ffd966",
                          font="Helvetica 12 bold", tags="fg")

        for card in self.all_cards():
            self.draw_card(card)

        self.draw_hand_marks()

        if self.banner != "":
            c.create_text(452, 262, text=self.banner, fill="#0c3a24",
                          font="Helvetica 26 bold", tags="fg")
            c.create_text(450, 260, text=self.banner, fill=self.banner_color,
                          font="Helvetica 26 bold", tags="fg")

        c.create_text(450, 20, text=self.message, fill="#f5f5f5",
                      font="Helvetica 15 bold", tags="fg")

        net = self.chips + total_bet + self.insurance - self.bought
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
                # the first time a card reaches its spot, it makes a flick
                if not card.landed:
                    card.landed = True
                    self.sound.play("flick", True)
                if card.open < card.want_open:
                    card.open = min(card.want_open, card.open + 0.08)
                elif card.open > card.want_open:
                    card.open = max(card.want_open, card.open - 0.08)

        self.draw(now)
        self.root.after(FRAME_MS, self.frame)


def main():
    root = tk.Tk()
    root.resizable(False, False)
    Game(root)
    root.mainloop()


if __name__ == "__main__":
    main()
