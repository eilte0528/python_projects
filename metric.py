from datetime import datetime

# each number is "how many base units in one of these"
# base units: meter, gram, liter
LENGTH = {"mm": 0.001, "cm": 0.01, "m": 1, "km": 1000,
          "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344}
MASS = {"mg": 0.001, "g": 1, "kg": 1000, "oz": 28.3495, "lb": 453.592}
VOLUME = {"ml": 0.001, "l": 1, "cup": 0.236588, "gal": 3.78541}

CATEGORIES = {"length": LENGTH, "mass": MASS, "volume": VOLUME}
TEMP_UNITS = ["c", "f", "k"]
NAMES = list(CATEGORIES) + ["temperature"]


def to_celsius(value, unit):
    if unit == "f":
        return (value - 32) * 5 / 9
    if unit == "k":
        return value - 273.15
    return value


def from_celsius(value, unit):
    if unit == "f":
        return value * 9 / 5 + 32
    if unit == "k":
        return value + 273.15
    return value


def units_for(category):
    if category == "temperature":
        return TEMP_UNITS
    return list(CATEGORIES[category])


class Converter:
    def __init__(self):
        self.history = []

    def convert(self, category, value, src, dst):
        # temperature has offsets so it can't use the simple ratio
        if category == "temperature":
            result = from_celsius(to_celsius(value, src), dst)
        else:
            table = CATEGORIES[category]
            result = value * table[src] / table[dst]

        line = f"{value:g} {src} = {result:.6g} {dst}"
        stamp = datetime.now().strftime("%H:%M")
        self.history.append(f"[{stamp}] {line}")
        return line

    def show_history(self):
        if not self.history:
            print("nothing yet")
        for line in self.history:
            print("  " + line)


def ask_number(prompt):
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("not a number")


def ask_unit(prompt, category):
    options = units_for(category)
    while True:
        unit = input(prompt).strip().lower()
        if unit in options:
            return unit
        print("pick from:", ", ".join(options))


def pick_category():
    for i, name in enumerate(NAMES, 1):
        print(f"  {i}. {name}")
    while True:
        choice = input("category (number, h = history, q = quit): ").strip().lower()
        if choice in ("h", "q"):
            return choice
        if choice.isdigit() and 1 <= int(choice) <= len(NAMES):
            return NAMES[int(choice) - 1]
        print("pick a number from the list")


def main():
    converter = Converter()
    print("📏 metric converter\n")

    while True:
        choice = pick_category()

        if choice == "q":
            break
        if choice == "h":
            converter.show_history()
            continue

        print("units:", ", ".join(units_for(choice)))
        value = ask_number("value: ")
        src = ask_unit("from: ", choice)
        dst = ask_unit("to: ", choice)
        print(converter.convert(choice, value, src, dst))
        print()

    print("bye")


# TODO: speed, area, save history to a file

if __name__ == "__main__":
    main()