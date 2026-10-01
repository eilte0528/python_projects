print("=" * 58)
print("STARFALL: THE GALAXY THAT REMEMBERED")
print("=" * 58)
print("A story about a crew, a strange signal, and one very bad galaxy")
print()

commander = input("What is your commander's name? ").strip()
if commander == "":
	commander = "Rook Vale"

print()
print("You are Commander " + commander + ", captain of the starship Wayfarer.")
print("Your crew calls you the Last Light. You once flew through a collapsing")
print("wormhole to save them. Jax still says the landing was your fault.")
print()
print("Imani Voss studies strange life and talks to plants when nobody is looking.")
print("Jax Arlen is your pilot, your oldest friend, and a terrible card player.")
print("Sable is the ship's android. Quiet, thoughtful, and part of the crew.")
print()
print("Now an unknown galaxy glows beyond the viewport. A distress signal")
print("is repeating your ship's name, though nobody here has sent it.")
print()

crew_trust = 0
signal_clues = 0
fuel_left = 3

print("IMANI: The nebula has a pulse. No, I don't like that either.")
print("JAX: We could ignore the breathing space cloud. Just an idea.")
print("SABLE: The signal uses the commander's voice.")
print("JAX: Your voice? That's not creepy at all.")
print("YOU: Whatever it is, it knows us. Let's find out why.")
print()
print("1. Follow the distress signal into the dark.")
print("2. Scan the living nebula before we get closer.")
choice = input("Choose 1 or 2: ").strip()
while choice != "1" and choice != "2":
	choice = input("Enter 1 or 2: ").strip()

if choice == "1":
	print()
	print("You steer straight toward the signal. The Wayfarer shudders as")
	print("something vast moves behind the stars.")
	print("JAX: You know, most captains wait until after breakfast to risk the ship.")
	print("YOU: You can eat when we know who's calling.")
	crew_trust = crew_trust + 1
	fuel_left = fuel_left - 1
else:
	print()
	print("You order a scan. The nebula ripples, then draws a perfect map")
	print("of the galaxy across the cockpit glass.")
	print("IMANI: It's not breathing. It's thinking. I wish I hadn't said that.")
	print("SABLE: The map shows a planet that is not there yet.")
	signal_clues = signal_clues + 1

print()
print("The signal grows louder. Its message is clear now:")
print("'WAYFARER, DO NOT LET SABLE OPEN THE DOOR.'")
print()
print("Sable's hands tighten around the console. Blue light flickers under")
print("its silver skin. It looks scared, though it insists it cannot be.")
print("SABLE: I don't remember sending that message.")
print("IMANI: We believe you. Right, Jax?")
print("JAX: I believe you. I just don't trust the creepy signal.")
print()
print("1. Trust Sable and ask it to decode the signal.")
print("2. Let Imani inspect the signal without connecting to Sable.")
choice = input("Choose 1 or 2: ").strip()
while choice != "1" and choice != "2":
	choice = input("Enter 1 or 2: ").strip()

if choice == "1":
	print()
	print("You nod to Sable. It looks relieved before connecting to the signal.")
	print("SABLE: The message is 27 years old.")
	print("JAX: We got here ten minutes ago.")
	print("SABLE: I know. That is why I am worried.")
	crew_trust = crew_trust + 1
	signal_clues = signal_clues + 1
else:
	print()
	print("Imani wires the signal through a med scanner and Jax's old radio.")
	print("IMANI: Got it. But something in there just looked back at me.")
	print("JAX: I liked the radio better when it only played bad music.")
	signal_clues = signal_clues + 1

print()
print("A black planet appears ahead, surrounded by the wreckage of ships.")
print("One wreck bears the Wayfarer's name. Its hull is scarred and ancient.")
print("JAX: That's our ship. Tell me that's not our ship.")
print("SABLE: It is ours. The captain's chair is empty.")
print("IMANI: Then where are we?")
print()
print("The signal changes. Your own voice speaks from the wreck:")
print("'Commander, the galaxy is alive. It learned our fears from our minds.'")
print("'It will offer you a perfect future. Do not believe it.'")
print()
print("IMANI: The galaxy is reading us. We have to choose what to do next.")
print("1. Fly through the wreck field and reach the black planet quickly.")
print("2. Take the long route through the nebula and protect the ship.")
choice = input("Choose 1 or 2: ").strip()
while choice != "1" and choice != "2":
	choice = input("Enter 1 or 2: ").strip()

if choice == "1":
	print()
	print("You thread the Wayfarer through the wreckage, flying by instinct.")
	print("JAX: That was the worst flying I have ever seen.")
	print("YOU: But we're alive.")
	print("JAX: Fine. I'll put it on the genius list.")
	fuel_left = fuel_left - 1
	crew_trust = crew_trust + 1
else:
	print()
	print("You guide the crew through the nebula. It parts around the ship")
	print("like a curtain, revealing a safe path to the black planet.")
	print("IMANI: It's making room for us. I think it wants us to see something.")
	signal_clues = signal_clues + 1

print()
print("On the black planet, a doorway opens in the rock. Beyond it waits")
print("a room filled with stars and one impossible sight: a second Wayfarer.")
print("An older version of Sable steps out, cracked and flickering.")
print()
print("OLD SABLE: I sent the signal. In my time, we trusted the galaxy.")
print("OLD SABLE: It gave us everything we wanted. Then it would not let us go.")
print("SABLE: Is that what happens to me?")
print("OLD SABLE: You keep the door open. You always have.")
print("IMANI: No. We are not leaving you here.")
print("JAX: Commander, please tell me you've got a plan.")
print()
print("The stars in the room blink like enormous eyes. The galaxy speaks")
print("through every speaker at once, using your voice:")
print("GALAXY: Stay. I can bring back everyone you lost. I can make you safe.")
print("For a moment, you see your crew at home, laughing around the old table.")
print("It feels real. That's the frightening part.")
print("Then Jax reaches for you, and his hand passes straight through.")
print()
print("YOU: A perfect world with no choices is just a beautiful cage.")
print("YOU: Crew, we're going home. Together.")
print()
print("1. Let Sable overload the doorway while you hold off the galaxy.")
print("2. Use the Wayfarer's engine to break the doorway from outside.")
choice = input("Choose 1 or 2: ").strip()
while choice != "1" and choice != "2":
	choice = input("Enter 1 or 2: ").strip()

print()
if choice == "1":
	print("SABLE: You trusted me when the signal told you not to.")
	print("SABLE: Thank you for seeing me as crew.")
	print("Sable overloads the doorway. You hold on as the stars pull at you.")
	print("IMANI: I've got you!")
	print("Together, the crew pulls you back through the closing door.")
else:
	print("JAX: You want me to fly into the door?")
	print("YOU: Through it. There's a difference.")
	print("JAX: There really isn't, but I trust you.")
	print("Jax brings the Wayfarer around. You cut the door's power.")
	print("The galaxy roars. Imani and Sable pull you out of the way.")

print()
print("The doorway shatters. The stars go dark, then return, one by one.")
print("The galaxy does not die. It lets go, like it is waking from a dream.")
print("The old Wayfarer fades away. Your crew is here. Your real crew.")
print()
print("IMANI: Do you think it understood why we left?")
print("YOU: I hope so. Nobody should have to be alone, even a galaxy.")
print("SABLE: I am glad I stayed with this crew.")
print("JAX: And I am glad my ship is in one piece.")
print("YOU: Most of it.")
print("JAX: I'm choosing to remember it in one piece.")
print()

if signal_clues > 1 and crew_trust > 0:
	print("With the clues you gathered and the trust you built, the Wayfarer")
	print("charts a safe passage out. Your crew names the route " + commander + "'s Run.")
elif fuel_left > 1:
	print("With fuel to spare, the Wayfarer gets home before the shockwave.")
	print("Your crew celebrates the fastest victory in fleet history.")
else:
	print("The Wayfarer limps out on emergency power, but every crew member")
	print("makes it home. The fleet calls your rescue a legendary victory.")

print()
print("YOU WIN, COMMANDER " + commander.upper() + ".")
print("The unknown galaxy has a new story to remember: the crew that said no.")
print("=" * 58)
