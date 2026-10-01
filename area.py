print("Area Calculator")

while True:
	print("\nChoose a shape:")
	print("1. Square")
	print("2. Rectangle")
	print("3. Triangle")
	print("4. Circle")
	print("5. Exit")

	choice = input("Enter your choice (1-5): ")

	if choice == "1":
		side = float(input("Enter the side length: "))
		area = side * side
		print("Area of the square:", area)
	elif choice == "2":
		length = float(input("Enter the length: "))
		width = float(input("Enter the width: "))
		area = length * width
		print("Area of the rectangle:", area)
	elif choice == "3":
		base = float(input("Enter the base: "))
		height = float(input("Enter the height: "))
		area = (base * height) / 2
		print("Area of the triangle:", area)
	elif choice == "4":
		radius = float(input("Enter the radius: "))
		area = 3.14 * radius * radius
		print("Area of the circle:", area)
	elif choice == "5":
		print("Thanks for using the Area Calculator!")
		break
	else:
		print("Invalid choice. Please enter a number from 1 to 5.")
