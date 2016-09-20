#!/usr/bin/env python

import argparse
import json
from evdev import InputDevice, UInput, categorize, ecodes
from collections import OrderedDict
import RPi.GPIO as GPIO
from time import sleep, time
from string import Template
import sys
import os
import stat
from os.path import abspath, dirname, isfile
from subprocess import call

PINS = range(27) # BCM pin range
CONFIG_FILE = "config.json"
INIT_SCRIPT = 'gpio-evdev-driver.sh'
POLLING_INTERVAL = 0.01 # in seconds
DEFAULT_ACTIONS = ['P1 Left', 'P1 Right', 'P1 Up', 'P1 Down', 'P1 Start', 'P1 Select', 'P1 A', 'P1 B', 'P1 X', 'P1 Y', 'P1 L', 'P1 R', 'ESC']

# read args
parser = argparse.ArgumentParser(description="polls GPIO events on the Raspberry Pi and maps them to keyboard events (requires root)")
parser.add_argument('-k','--assign-keys', action='store_true', help='goes through all actions defined in config.json and assigns keyboard events to be sent')
parser.add_argument('-p','--assign-pins', action='store_true', help='goes through all actions defined in config.json and assigns GPIO triggers to be monitored')
parser.add_argument('-d','--device', default='/dev/input/event0', help='keyboard input device (default: /dev/input/event0)')
parser.add_argument('-t','--test-pins', action='store_true', help='polls all pin states for testing purposes')
parser.add_argument('-i','--install', action='store_true', help='installs as init script daemon (automatic lauch at boot; always refers to this script location and config.json!)')
parser.add_argument('-u','--uninstall', action='store_true', help='uninstalls init script daemon')

args = parser.parse_args()

def init_gpio():
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(PINS, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# waits for and returns key down event
def wait_key(dev):
	for event in dev.read_loop():
		if event.type == ecodes.EV_KEY and event.value == 1: # key down
			return event

def assign_keys(config):
	keys = set()
	keyboard = InputDevice(args.device)
	for action in config['actions']:
		print "press key for '%s' ..." % action
		while True:
			event = wait_key(keyboard)
			if event.code not in keys:
				break
		keys.add(event.code)
		config['actions'][action]['key'] = event.code
	return config

def wait_pins():
	pressed = set()
	released = set()
	while not pressed or not pressed == released:
		for pin in PINS:
			if GPIO.input(pin) == 0:
				pressed.add(pin)
			else:
				if pin in pressed:
					released.add(pin)
        	sleep(POLLING_INTERVAL) # waiting between pins yields in better perofrmance
	return list(pressed)

def assign_pins(config):
	init_gpio()
	for action in config['actions']:
		print "press button for %s ... " % action
		pins = wait_pins()
		config['actions'][action]['pins'] = pins
	return config

def test_pins():
	init_gpio()
	while True:
		vals = []
		for pin in PINS:
			vals.append(GPIO.input(pin))
		print vals
		sleep(POLLING_INTERVAL)

# writes config to JSON
def write_config(fname, config):
	with open(fname, 'w') as f:
	    json.dump(config, f, indent=4)

# reads / generates config
def read_config(fname):
	if isfile(fname):
		with open(fname, 'r') as f:
		    config = json.load(f, object_pairs_hook=OrderedDict)
	else:
		actions = OrderedDict()
		for action in DEFAULT_ACTIONS:
			actions[action] = {'pins': [], 'key': None}
		config = {'actions': actions}
	return config

# create mapping
def create_mapping(config):
	mapping = {} # pin -> key
	combinations = [] # (pins, key)
	for action,d in config['actions'].items():
		pins = d['pins']
		key = d['key']
		if pins and key is not None:
			print "mapping pin(s) %s to key %d for '%s'" % (str(pins), key, action)
			if len(pins) == 1:
				mapping[pins[0]] = key
			else:
				combinations.append( (pins, key) )
	return mapping, combinations

# main loop
def polling_loop(mapping, combinations):
	init_gpio()
	uinput = UInput()

	pin_state = [1]*len(PINS)
	combination_state = [False]*len(combinations)

	while True:
		#start = time()

		# update pin states and trigger single pin events
		for pin in PINS:
			prev = pin_state[pin] # previous pin state
			curr = GPIO.input(pin) # current pin state

			# detect edges
			if prev and not curr and pin in mapping: # falling edge
				uinput.write(ecodes.EV_KEY, mapping[pin], 1)  # key down
				uinput.syn()
			elif not prev and curr and pin in mapping: # rising edge
				uinput.write(ecodes.EV_KEY, mapping[pin], 0)  # key up
				uinput.syn()

			# update pin state
			pin_state[pin] = curr

		# query pin combinations
		for i, (pins, key) in enumerate(combinations):
			hit = True
			for pin in pins:
				if pin_state[pin] == 1:
					hit = False
					break
			if hit and not combination_state[i]:
				combination_state[i] = True
				uinput.write(ecodes.EV_KEY, key, 1)  # key down
				uinput.syn()
			elif not hit and combination_state[i]:
				combination_state[i] = False
				uinput.write(ecodes.EV_KEY, key, 0)  # key up
				uinput.syn()

		#print time() - start

		# wait for next polling cycle
		sleep(POLLING_INTERVAL)

# read config
config = read_config(CONFIG_FILE)

# pin test
if args.test_pins:
	test_pins()
	exit(0)

# assign keys
if args.assign_keys:
	config = assign_keys(config)
	write_config(CONFIG_FILE, config)
	exit(0)

# assign pins
if args.assign_pins:
	config = assign_pins(config)
	write_config(CONFIG_FILE, config)
	exit(0)

# install
init_script_path = '/etc/init.d/' + INIT_SCRIPT
if args.install:
	# generate init script
	template = Template( open(INIT_SCRIPT + '.template').read() )
	mapping = {'dir': abspath(dirname(sys.argv[0]))}
	init_script = template.substitute(mapping)

	# install init script
	open(init_script_path,'w').write(init_script)
	stats = os.stat(init_script_path)
	os.chmod(init_script_path, stats.st_mode | stat.S_IEXEC)
	call(['update-rc.d', INIT_SCRIPT, 'defaults'])

	exit(0)

# uninstall
if args.uninstall:
	call(['update-rc.d', INIT_SCRIPT, 'remove'])
	os.remove(init_script_path)
	exit(0)

# redirect std streams
sys.stdout = open("stdout.txt", 'w')
sys.stderr = open("stderr.txt", 'w')

# run driver mode
mapping, combinations = create_mapping(config)
polling_loop(mapping, combinations)
