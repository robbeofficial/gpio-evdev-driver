import RPi.GPIO as GPIO
from time import sleep
import pickle
from os.path import isfile
from evdev import InputDevice, UInput, categorize, ecodes
from sys import stdout

INPUT_PINS = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30] # pins to be polled (all others are ignored)
NPINS = len(INPUT_PINS)
CONFIG_FILE_KEYS = 'keys.p' # key configuration (action -> key)
CONFIG_FILE_GPIO = 'gpio.p' # gpio configuration (action -> gpio pin)
ACTIONS = ['P1 Left', 'P1 Right', 'P1 Up', 'P1 Down', 'P1 Start', 'P1 Select', 'P1 A', 'P1 B', 'P1 X', 'P1 Y', 'P1 L', 'P1 R'] # list of user actions (should be <= INPUT_PINS)
POLLING_INTERVAL = 0.01 # in seconds

# setup input pins to use pull-up resistors
def setup_pins():
	for pin in INPUT_PINS:
		print("polling pin %d" % pin)
		GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# polling loop
def poll(mapping):
	state = dict(zip(INPUT_PINS,NPINS*[1])) # default pin state (working with low-active signals here)
	uinput = UInput()

	while True:
		for pin in INPUT_PINS:
			pval = state[pin] # previous pin state
			val = GPIO.input(pin) # current pin state
		
			# detect edges
			if not pval and val: # rising edge
				#print("rising edge at pin %d -> %s up" % (pin,ecodes.KEY[mapping[pin]]))
				uinput.write(ecodes.EV_KEY, mapping[pin], 0)  # key up
				uinput.syn()
			elif pval and not val: # falling edge
				#print("falling edge at pin %d -> %s down" % (pin, ecodes.KEY[mapping[pin]]))
				uinput.write(ecodes.EV_KEY, mapping[pin], 1)  # key down
				uinput.syn()

			state[pin] = val # update pin state

		sleep(POLLING_INTERVAL) # wait for next polling cycle

# waits for and returns key down event
def wait_key(dev):
	for event in dev.read_loop():
		if event.type == ecodes.EV_KEY and event.value == 1: # key down
			return event

# waits for falling edge and returns corresponding input pin 
def wait_falling_edge():
	while True:
		for pin in INPUT_PINS:
			if GPIO.input(pin) == 0:
				return pin
        sleep(POLLING_INTERVAL)

# print() without linebreak
def printf(string):
	stdout.write(string)
	stdout.flush()

# prompts for keyboard events to be sent for each user action (action->key mapping)
def configure_keys(dev):
	keys = dict()
	for action in ACTIONS:
		printf("press key for %s ... " % action)
		while True:
			event = wait_key(dev)
			if event.code not in keys.values():
				break
		printf("%s\n" % ecodes.KEY[event.code])
		keys[action] = event.code
	return keys

# prompts for GPIO events that should trigger the user actions (action->pin mapping)
def configure_gpio():
	gpio = dict()
	for action in ACTIONS:
		printf("press button for %s ... " % action)
		while True:
			pin = wait_falling_edge()
			if pin not in gpio.values():
				break
		printf("%d\n" % pin)
		gpio[action] = pin
	return gpio

# reads action->key mapping from config file, starts configuration if file not yet exists
def read_keys():
	if not isfile(CONFIG_FILE_KEYS):
		keyboard = InputDevice('/dev/input/event0')
		keys = configure_keys(keyboard)
		pickle.dump(keys, open(CONFIG_FILE_KEYS,'w'))
	else:
		keys = pickle.load(open(CONFIG_FILE_KEYS, 'r'))
	return keys

# reads action->pin mapping from config file, starts configuration if file not yet exists
def read_gpio():
	if not isfile(CONFIG_FILE_GPIO):
		gpio = configure_gpio()
		pickle.dump(gpio, open(CONFIG_FILE_GPIO,'w'))
	else:
		gpio = pickle.load(open(CONFIG_FILE_GPIO, 'r'))
	return gpio

# creates pin->key mapping for all user actions
def create_mapping(gpio, keys):
	mapping = dict()
	for action in ACTIONS:
		mapping[gpio[action]] = keys[action]
	return mapping


GPIO.setmode(GPIO.BCM)
setup_pins()

keys = read_keys()
gpio = read_gpio()
mapping = create_mapping(gpio, keys)

poll(mapping)
