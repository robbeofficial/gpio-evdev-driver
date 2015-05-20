# gpio-evdev-driver
polls GPIO events on the Raspberry Pi and maps them to keyboard events.

The code was intended to be used with RetroPie: http://blog.petrockblock.com/retropie/ and custom input hardware which is directly hooked up to the GPIO pins of the Pi. Similar projects (also based on uinput, listed below) exist, but none of them worked for my particular configuration so I decided to start a new one.

The code polls for low-active signals! It sets the input pins up with the internat pull-up resistors, so the default state is HIGH. After a pin is connected to GND, an input event is triggered, which fires a keyboard event.

When running the code for the first time, it will ask you to define a keyboard event to be sent for each user action in ACTIONS. The same goes for GPIO events (falling edges). Currently, you revert the configuration by simply deleting the corresponding *.p files.

## Requirements
- the uinput kernel module must be installed, which is usually the case
- RPi.GPIO package: https://pypi.python.org/pypi/RPi.GPIO
- evdev python module: https://python-evdev.readthedocs.org/en/latest/

## Related Projects
- pikeyd: https://github.com/mmoller2k/pikeyd
- retrogame: https://github.com/adafruit/Adafruit-Retrogame

## TODOs
- player 2 actions
- make code runable as daemon
- detect specific configurations of multiple pins (combos)
- send key combinations (e.g. ctrl-alt-del)
- don't use pickle, but something human readable (probably JSON)
- maybe some arguments to (re)configure stuff
