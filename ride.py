height = int(input('What is your height (cm)? '))
credits = int(input('How many credits do you have? '))

if height >= 147 and credits >= 10:
  print("Enjoy the ride!")
elif height < 147 and credits >= 10:
  print("You are not tall enough to ride.")
elif credits < 10 and height >= 147:
  print("You don't have enough credits to ride.")
else:
  print("You are not tall enough for this ride, nor do you have enough credits.")