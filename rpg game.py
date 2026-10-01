import random

player_hp = 30
max_player_hp = 30
enemy_hp = 24
potions = 2
game_running = True

print("=== My Forest RPG ===")
print("You're walking through the forest when a goblin shows up.")
print("Choose a move: attack, block, heal, or quit")

while game_running and player_hp > 0 and enemy_hp > 0:
	print("\nYour HP:", player_hp, "/", max_player_hp)
	print("Goblin HP:", enemy_hp)
	print("Potions:", potions)
	move = input("Your move: ").lower()

	if move == "attack":
		damage = random.randint(4, 8)
		enemy_hp = enemy_hp - damage
		print("You hit the goblin for", damage, "damage.")
	elif move == "block":
		print("You get ready to block the next attack.")
	elif move == "heal":
		if potions > 0:
			healing = random.randint(6, 10)
			player_hp = player_hp + healing
			if player_hp > max_player_hp:
				player_hp = max_player_hp
			potions = potions - 1
			print("You use a potion and get back", healing, "HP.")
		else:
			print("You're out of potions.")
			continue
	elif move == "quit":
		game_running = False
		print("You head back home.")
	else:
		print("I don't know that move. Try attack, block, heal, or quit.")
		continue

	if game_running and enemy_hp > 0:
		enemy_damage = random.randint(3, 7)
		if move == "block":
			blocked_damage = random.randint(2, 4)
			enemy_damage = enemy_damage - blocked_damage
			if enemy_damage < 0:
				enemy_damage = 0
			print("You block", blocked_damage, "damage.")

		player_hp = player_hp - enemy_damage
		print("The goblin hits you for", enemy_damage, "damage.")

		if player_hp < 0:
			player_hp = 0

if player_hp == 0:
	print("\nThe goblin beat you this time.")
elif enemy_hp <= 0:
	print("\nYou beat the goblin! The path home is clear.")
