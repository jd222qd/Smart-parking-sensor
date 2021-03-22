import os
import machine


uart = machine.UART(0, 115200)
os.dupterm(uart)

machine.main('main.py')
print('Starting main program!')
