# import things
from flask import Flask, request
from flask_table import Table, Col
import sqlite3
import time
import Adafruit_DHT
import RPi.GPIO as GPIO
import os
import glob

#######################
# This code desperately needs refactoring, but is a functional homebrew solution
#######################

app = Flask(__name__)

database = 'Kombucha_data.sqlite'
#conn = sqlite3.connect(database)
#c = conn.cursor()

#######################
# MISC INFO
#######################
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


batch = 1;

#######################
# Database Functions
#######################

def write_to_db(batch_num,pH,db=database):
	"""Writes batch, time, temperature, ambient temperature, and humidity to database"""
	conn = sqlite3.connect(db)
	c = conn.cursor()
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
	# System-specific stuff for DS1820 temp probe. 
	##################################################
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)
	GPIO.setup(heat_pin, GPIO.OUT)

	os.system('modprobe w1-gpio')
	os.system('modprobe w1-therm')

	base_dir = '/sys/bus/w1/devices/'

	device_folder = glob.glob(base_dir + ds1820_prefix + '*')[0]
	device_file = device_folder + '/w1_slave'

	#######################
	# Sensor Functions
	#######################

	def read_temp_raw():
		with open(device_file, 'r') as deviceFile:
			lines = deviceFile.readlines()
		return lines

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

	def check_heater_state():
		return GPIO.input(heat_pin)
		

		cur_time = time.time()
		heater_state = check_heater_state()
		temp = read_temp()
		amb_hum, amb_temp = read_ambient(amb_heat_pin,2)

		c.execute('''INSERT INTO Kombucha_data('Batch Number', 'pH', 'Time', 'Heater State', 'Temperature', 'Ambient Temperature', 'Ambient Humidity')
					  VALUES(?,?,?,?,?,?,?)''', (batch_num, pH, cur_time, heater_state, temp, amb_temp, amb_hum))
		conn.commit()
		conn.close()
		return

def read_from_db(db=database):
	"""Writes batch, time, temperature, ambient temperature, and humidity to database"""
	conn = sqlite3.connect(db)
	c = conn.cursor()
	c.execute('''SELECT * FROM (
		SELECT * FROM Kombucha_data ORDER BY Time DESC LIMIT 20)
		ORDER BY Time ASC;''')

	rows = c.fetchall()
	conn.close()
	return rows

#######################
# Table Formatting
#######################

class ItemTable(Table):
	batch_num = Col('Batch Number')
	pH = Col('pH')
	cur_time = Col('Time')
	heater_state = Col('Heater State')
	temp = Col('Kombucha Temperature')
	amb_temp = Col('Ambient Temperature')
	amb_hum = Col('Ambient Humidity')


class Item(object):
	def __init__(self, info):
		(batch_num,cur_time,heater_state,temp,amb_temp,amb_hum,pH) = info
		self.batch_num = batch_num
		self.pH = pH
		self.cur_time = cur_time
		self.heater_state = heater_state
		self.temp = temp
		self.amb_temp = amb_temp
		self.amb_hum = amb_hum


def read_from_db(db=database):
	"""Writes batch, time, temperature, ambient temperature, and humidity to database"""
	conn = sqlite3.connect(db)
	c = conn.cursor()
	c.execute('''SELECT * FROM (
		SELECT * FROM Kombucha_data ORDER BY Time DESC LIMIT 20)
		ORDER BY Time ASC;''')

	rows = c.fetchall()
	conn.close()
	return rows

"""
#Convert to Items
items = []
rows = read_from_db()
print rows
for row in rows:
	items.append(Item(row))

# Populate the table
table = ItemTable(items)
"""

@app.route('/')
def homepage():
	#Creates a page with the table
	#Convert to Items
	items = []
	rows = read_from_db()
	print rows
	for row in rows:
		items.append(Item(row))

	# Populate the table
	table = ItemTable(items)

	return "<style> table, th, td {border: 1px solid black;} </style>" + table.__html__()

@app.route('/pH')
def pH_webpage():
	return '<head> <title>Input current pH</title> </head> <h2>Input current pH</h2><form method="POST"> <input name="pH_value"> <input type="submit"> </form> '

@app.route('/pH',methods=['POST'])
def pH_entry():
	pH_val = request.form.get('pH_value')
	print pH_val
	write_to_db(batch,float(pH_val))
	return 

if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0')