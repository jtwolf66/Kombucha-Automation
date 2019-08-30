#!/usr/bin/python
import sqlite3
import RPi.GPIO as GPIO
import time
import glob
import os
import Adafruit_DHT

##################################################
#
# This code is run by a cron-job every 5 minutes.
#
##################################################



##################################################
# Useful parameters
##################################################

#Working Directory
PWD=os.getcwd()

#Batch Number
batch = 1

# GPIO pin number to control heating pad
heat_pin = 19
amb_heat_pin = 22

# Define minimum and maximum temperatures (deg. C)
min_temp = 24.0
max_temp = 27.0

# Serial prefix for DS1820 probe.
ds1820_prefix = '28'


##################################################
# Database Setup
##################################################

database = 'Kombucha_data.sqlite'
#conn = sqlite3.connect(database)
#c = conn.cursor()



ktable = 'Kombucha_data'

cbatch = 'Batch Number'
t1 = 'INTEGER'
cpH = 'pH'
t2 = 'REAL'
ctime = 'Time'
t3 = 'INTEGER'
ctemp = 'Temperature'
t4 = 'REAL'
catemp = 'Ambient Temperature'
t5 = 'REAL'
cahum = 'Ambient Humidity'
t6 = 'REAL'


##################################################
# System-specific stuff for DS1820 temp probe. 
##################################################

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

base_dir = '/sys/bus/w1/devices/'

device_folder = glob.glob(base_dir + ds1820_prefix + '*')[0]
device_file = device_folder + '/w1_slave'

##################################################


##################################################
# Set up GPIO pins
##################################################

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(heat_pin, GPIO.OUT)

##################################################


##################################################
# Useful Functions
##################################################

def read_temp_raw():
	with open(device_file, 'r') as deviceFile:
		lines = deviceFile.readlines()
	return lines

def degCtoF(tempC):
	"""Converts from degrees Celcius to Fahrenheit"""
	return tempC * 9.0 / 5.0 + 32.0

def read_temp():
	"""Reads device file and returns temperature in deg. Celcius"""
	lines = read_temp_raw()
	while lines[0].strip()[-3:] != 'YES':
		time.sleep(0.2)
		lines = read_temp_raw()
	equals_pos = lines[1].find('t=')
	if equals_pos != -1:
		temp_string = lines[1][equals_pos+2:]
		return float(temp_string) / 1000.0

def read_ambient(sensor_id,pin):
	sensor_args = { '11': Adafruit_DHT.DHT11,
                '22': Adafruit_DHT.DHT22,
                '2302': Adafruit_DHT.AM2302 }
    if sensor_id in sensor_args:
    	sensor = sensor_args[sensor_id]
	    amb_hum, amb_temp = Adafruit_DHT.read_retry(sensor, pin)
	    return amb_hum, amb_temp
	else:
		print('Failed to get reading. Invalid sensor_id')
		return

def write_to_db(db=database,batch_num,cur_time,heater_state,temp,amb_temp,amb_hum):
	"""Writes batch, time, temperature, ambient temperature, and humidity to database"""
	conn = sqlite3.connect(db)
	c = conn.cursor()
	c.execute('''INSERT INTO Kombucha_data('Batch Number', 'pH', 'Time', 'Heater State', 'Temperature', 'Ambient Temperature', 'Ambient Humidity')
                  VALUES(?,NULL,?,?,?,?,?)''', (batch_num, cur_time, heater_state, temp, amb_temp, amb_hum))
	conn.commit()
	conn.close()
	return


##################################################

##################################################
# Define switching state
##################################################

def check_heater_state():
	return GPIO.input(heat_pin)

def switch_state(state):
	"""This takes in the state we want the switch to
	be in ("ON" or "OFF") and tries to do so. It
	outputs this new state to the state file defined
	at the top."""
	if state == "ON":
		gpio_state = GPIO.HIGH
	elif state == "OFF":
		gpio_state = GPIO.LOW
	try:
		GPIO.output(heat_pin, gpio_state)

	except KeyboardInterrupt:
		print "Aborted by user"
		# Reset GPIO settings
		GPIO.cleanup()

##################################################


##################################################
# Perform control actions
##################################################
curr_time = time.time()
curr_temp = read_temp()
cur_ambh, cur_ambt = read_ambient(amb_heat_pin,2)

if curr_temp <= min_temp:
	switch_state("ON")
	write_to_db(batch,curr_time,1,curr_temp,cur_ambt.cur_ambh)
elif curr_temp >= max_temp:
	switch_state("OFF")
	write_to_db(batch,curr_time,0,curr_temp,cur_ambt.cur_ambh)
elif (curr_temp > min_temp) and (curr_temp < max_temp):
	cur_hstate = check_heater_state()
	write_to_db(batch,curr_time,cur_hstate,curr_temp,cur_ambt.cur_ambh)
else:
	print("An error seems to have occured")
	switch_state("OFF")

##################################################
