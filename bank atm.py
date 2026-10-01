print('BANK OF EILTE')

pin = int(input('Enter your PIN: '))

while pin != 5428:
  pin = int(input('Incorrect PIN. Enter your PIN again: '))

if pin == 5428:
  print('PIN accepted!')
