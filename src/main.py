import time
import ubinascii
from network import LoRa
import machine
import socket
import struct
import pycom
from machine import I2C

from network import WLAN

wl = WLAN()
wl.deinit()


print('Main start')

i2c = I2C(0, I2C.MASTER, baudrate=115200, pins=('P9', 'P10'))
addr = i2c.scan()
print(addr)
if addr:
    print('Sensor detected on address: ', addr, '\n')
    addr = addr[0]
else:
    print('No sensor detected!\n')
    addr = 0x0D  # Use default address for the sensor
    pycom.heartbeat(False)
    pycom.rgbled(0xFF0000)  # Red light to indicate error connecting to sensor

X_start_val = 0
Y_start_val = 0
Z_start_val = 0

#LoRa setup
lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.EU868)

app_eui = ubinascii.unhexlify("70B3D57ED003E884")
app_key = ubinascii.unhexlify("32F83B1858BD503C6D1C724FD1D4F8CA")

lora.join(activation=LoRa.OTAA, auth=(app_eui, app_key), timeout=0)

while not lora.has_joined():
    print("LoRa not yet joined...")
    time.sleep(3)

print('Successfully joined LoRa network!')

#Create LoRa socket
lora_socket = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
lora_socket.setsockopt(socket.SOL_LORA, socket.SO_DR, 0) #Data Rate set to 0 in order to achieve higher range

#Sensor class
class Sensor():

    def __init__(self, i2c, addr): #Initialize values
        self.i2c = i2c
        self.addr = addr
        self.val = 0

    def setup(self): #Configure the sensor

        #SET PERIOD

        setup1 = bytearray(2)
        setup1[0] = 0x0B
        setup1[1] = 0x01

        self.i2c.writeto(addr, setup1)
        time.sleep_ms(10)
        period_val = self.i2c.readfrom(self.addr, 2) # read 2 bytes

        #Set continous mode

        setup2 = bytearray(2)
        setup2[0] = 0x09
        setup2[1] = 0x1D

        self.i2c.writeto(addr, setup2)
        time.sleep_ms(10)
        contmode_val = self.i2c.readfrom(self.addr, 2) # read 2 bytes


        #Check status if ready

        self.i2c.writeto(addr, 0x06)
        time.sleep_ms(10)
        ready_val = self.i2c.readfrom(self.addr, 2) # read 2 bytes



    def read(self):

        #Read data from X-axis LSB

        self.i2c.writeto(addr, 0x00)
        time.sleep_ms(50)
        X_LSB = self.i2c.readfrom(self.addr, 1) # read 2 bytes
        X_LSB_val = X_LSB[0]

        #Read data from X-axis MSB

        self.i2c.writeto(addr, 0x01)
        time.sleep_ms(50)
        X_MSB = self.i2c.readfrom(self.addr, 1) # read 2 bytes
        if(X_MSB[0] >= 128): # Convert to negative value using two's complement
            X_MSB_val = -1*(X_MSB[0] - 128)
        else:
            X_MSB_val = X_MSB[0]

        #Read data from Y-axis LSB

        self.i2c.writeto(addr, 0x02)
        time.sleep_ms(50)
        Y_LSB = self.i2c.readfrom(self.addr, 1) # read 2 bytes
        Y_LSB_val = Y_LSB[0]

        #Read data from Y-axis MSB

        self.i2c.writeto(addr, 0x03)
        time.sleep_ms(50)
        Y_MSB = self.i2c.readfrom(self.addr, 1) # read 2 bytes
        if(Y_MSB[0] >= 128): # Convert to negative value using two's complement
            Y_MSB_val = -1*(Y_MSB[0] - 128)
        else:
            Y_MSB_val = Y_MSB[0]

        #Read data from Z-axis LSB

        self.i2c.writeto(addr, 0x04)
        time.sleep_ms(50)
        Z_LSB = self.i2c.readfrom(self.addr, 1) # read 2 bytes
        Z_LSB_val = Z_LSB[0]

        #Read data from Z-axis MSB

        self.i2c.writeto(addr, 0x05)
        time.sleep_ms(50)
        Z_MSB = self.i2c.readfrom(self.addr, 1) # read 2 bytes
        if(Z_MSB[0] >= 128): # Convert to negative value using two's complement
            Z_MSB_val = -1*(Z_MSB[0] - 128)
        else:
            Z_MSB_val = Z_MSB[0]

        #Convert LSB to negative if MSB is negative
        if(X_MSB_val < 0):
            X_LSB_val = -1*X_LSB_val

        if(Y_MSB_val < 0):
            Y_LSB_val = -1*Y_LSB_val

        if(Z_MSB_val < 0):
            Z_LSB_val = -1*Z_LSB_val

        #Bitshift MSB 8 places to the left
        X_val = X_MSB_val * 2**8 + X_LSB_val
        Y_val = Y_MSB_val * 2**8 + Y_LSB_val
        Z_val = Z_MSB_val * 2**8 + Z_LSB_val

        values = [X_val, Y_val, Z_val]
        self.val = values

        return self.val


sensor = Sensor(i2c, addr) #Initialize sensor

sensor.setup() #Setup continous mode etc for sensor

#Calculate start values
for x in range(10):
    start_values = sensor.read()
    print('Start values = ', start_values)
    if x != 0: #Skip 1st set of values for better accuracy
        print('not skipping nr ', x)
        X_start_val = X_start_val + start_values[0]
        Y_start_val = Y_start_val + start_values[1]
        Z_start_val = Z_start_val + start_values[2]

    print('X = ', X_start_val)
    print('Y = ', Y_start_val)
    print('Z = ', Z_start_val)

#Find the average start values
X_start_val = X_start_val/9
Y_start_val = Y_start_val/9
Z_start_val = Z_start_val/9

print('Calculating average...')

print('X = ', X_start_val)
print('Y = ', Y_start_val)
print('Z = ', Z_start_val)

current_parking_value = 0 # 0 = empty, 1 = car

while True:
    time.sleep_ms(50)  #Sleep to give the sensor some time to get a good reading
    other_val = sensor.read()
    print('The values are: ', other_val)

    if abs(X_start_val - other_val[0]) > 200:
        print('Car detected!')
        if current_parking_value == 0: #If the spot was empty, send data
            lora_socket.send(bytes([0x01]))
            current_parking_value = 1
    elif abs(Y_start_val - other_val[1]) > 200:
        print('Car detected!')
        if current_parking_value == 0: #If the spot was empty, send data
            lora_socket.send(bytes([0x01]))
            current_parking_value = 1
    elif abs(Z_start_val - other_val[2]) > 200:
        print('Car detected!')
        if current_parking_value == 0: #If the spot was empty, send data
            lora_socket.send(bytes([0x01]))
            current_parking_value = 1
    else:
        print('Empty spot!')
        if current_parking_value == 1: #If there was a car parked previously, send data
            lora_socket.send(bytes([0x00]))
            current_parking_value = 0
