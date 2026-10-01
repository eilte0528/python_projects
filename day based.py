print("A DAY IN THE LIFE")
print("-----------------")
print("You are jigar, and today is yours to shape.")

play_again = "yes"

while play_again == "yes":
	time = 7
	energy = 5
	mood = 5
	plans_done = 0

	print("\nIt is 7:00 AM. Your alarm starts ringing.")
	print("1. Get up right away")
	print("2. Snooze for a little longer")
	choice = input("What do you do? Enter 1 or 2: ")

	while choice != "1" and choice != "2":
		choice = input("Please enter 1 or 2: ")

	if choice == "1":
		print("You get up early and have time to prepare.")
		energy = energy + 1
		plans_done = plans_done + 1
	else:
		print("You snooze your alarm. The extra rest feels good, but now you are rushing!")
		time = time + 1
		energy = energy + 1

	print("\nIt is now", time, "AM. Time for breakfast.")
	print("1. Make a healthy breakfast")
	print("2. Grab a quick snack")
	print("3. Skip breakfast")
	choice = input("Choose 1, 2, or 3: ")

	while choice != "1" and choice != "2" and choice != "3":
		choice = input("Please enter 1, 2, or 3: ")

	if choice == "1":
		print("A good breakfast gives you a strong start.")
		energy = energy + 2
		mood = mood + 1
	elif choice == "2":
		print("Your snack is quick, and you are ready to go.")
		energy = energy + 1
	else:
		print("You head out hungry. The morning might feel longer now.")
		energy = energy - 1

	print("\nOn the way to school, you notice a neighbor carrying heavy bags.")
	print("1. Stop and help")
	print("2. Keep going so you are not late")
	choice = input("Choose 1 or 2: ")

	while choice != "1" and choice != "2":
		choice = input("Please enter 1 or 2: ")

	if choice == "1":
		print("Your neighbor thanks you. Helping feels good, even if it takes time.")
		mood = mood + 2
		time = time + 1
	else:
		print("You make good time, but wonder if you should have stopped.")
		plans_done = plans_done + 1

	print("\nIt is around", time + 2, "AM. You arrive at school with", energy, "energy.")
	print("A big assignment is due today. What is your plan?")
	print("1. Work steadily and ask for help if needed")
	print("2. Rush through it alone")
	print("3. Take a short break, then get started")
	choice = input("Choose 1, 2, or 3: ")

	while choice != "1" and choice != "2" and choice != "3":
		choice = input("Please enter 1, 2, or 3: ")

	if choice == "1":
		print("You focus, make progress, and finish the assignment.")
		plans_done = plans_done + 2
		energy = energy - 1
	elif choice == "2":
		print("You finish quickly, but the rushed work is not your best.")
		plans_done = plans_done + 1
		energy = energy - 2
	else:
		print("The break clears your head. You get started and finish most of it.")
		plans_done = plans_done + 1
		mood = mood + 1
		energy = energy - 1

	print("\nAfter school, a friend invites you to play outside.")
	print("1. Join your friend")
	print("2. Go home and relax")
	choice = input("Choose 1 or 2: ")

	while choice != "1" and choice != "2":
		choice = input("Please enter 1 or 2: ")

	if choice == "1":
		print("You have fun together and get some fresh air.")
		mood = mood + 2
		energy = energy - 1
	else:
		print("You enjoy a quiet break and recharge at home.")
		energy = energy + 1
		mood = mood + 1

	print("\nThe day is winding down.")
	if energy >= 5 and mood >= 7:
		print("ENDING: A bright, balanced day! You feel rested, happy, and ready for tomorrow.")
	elif plans_done >= 3:
		print("ENDING: A productive day! You got a lot done, even if you are ready for bed.")
	elif mood >= 6:
		print("ENDING: A kind and cheerful day! The moments you shared made it special.")
	else:
		print("ENDING: A tiring day. Tomorrow is a fresh start, and you can make a new plan.")

	print("\nYour final energy:", energy)
	print("Your final mood:", mood)
	play_again = input("\nPlay through another day? Enter yes or no: ").lower()

	while play_again != "yes" and play_again != "no":
		play_again = input("Please enter yes or no: ").lower()

print("\nThanks for playing A Day in the Life!")
