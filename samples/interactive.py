#!/usr/bin/env python

import sys
import os
import curses
import code
import readline
import rlcompleter

sys.path.append('../src')

from Bybop_Discovery import *
import Bybop_Device

def input_processing(drone, key, stdscr):
    
    if key == 65 or key == curses.KEY_UP:
        stdscr.addstr(5, 10, str(key) + ' pressed')
        stdscr.refresh()
    elif key == 66 or key == curses.KEY_DOWN:
        stdscr.addstr(5, 10, str(key) + ' pressed')
        stdscr.refresh()
    elif key == 68 or key == curses.KEY_LEFT:
        stdscr.addstr(5, 10, str(key) + ' pressed')
        stdscr.refresh()
    elif key == 67 or key == curses.KEY_RIGHT:
        stdscr.addstr(5, 10, str(key) + ' pressed')
        stdscr.refresh()
    elif key == 101 or key == 'e':
        stdscr.addstr(5, 10, str(key) + ' pressed')
        stdscr.refresh()
    elif key == 116 or key == 't':
        stdscr.addstr(5, 10, str(key) + ' pressed')
        stdscr.refresh()
    elif key == 32 or key == '  ':
        stdscr.addstr(5, 10, str(key) + ' pressed')
        stdscr.refresh()
    elif key == 114 or key == 'r':
        stdscr.addstr(5, 10, str(key) + ' pressed')
        stdscr.refresh()
    elif key == 102 or key == 'f':
        stdscr.addstr(5, 10, str(key) + ' pressed')
        stdscr.refresh()
    elif key == 100 or key == 'd':
        stdscr.addstr(5, 10, str(key) + ' pressed')
        stdscr.refresh()
    elif key == 103 or key == 'g':
        stdscr.addstr(5, 10, str(key) + ' pressed')
        stdscr.refresh()
    else:
        stdscr.addstr(5, 10,'None : ' + str(key) + ' pressed')
        stdscr.refresh()

print 'Searching for devices'

discovery = Discovery(DeviceID.ALL)

discovery.wait_for_change()

devices = discovery.get_devices()

discovery.stop()

if not devices:
    print 'Oops ...'
    sys.exit(1)

device = devices.itervalues().next()

print 'Will connect to ' + get_name(device)

d2c_port = 54321
controller_type = "PC"
controller_name = "bybop shell"

drone = Bybop_Device.create_and_connect(device, d2c_port, controller_type, controller_name)

if drone is None:
    print 'Unable to connect to a product'
    sys.exit(1)

drone.dump_state()

vars = globals().copy()
vars.update(locals())
readline.set_completer(rlcompleter.Completer(vars).complete)
readline.parse_and_bind("tab: complete")
shell = code.InteractiveConsole(vars)

#shell.interact()
drone.get_cali()
drone.get_mav_availability()

stdscr = curses.initscr()
curses.cbreak()
stdscr.keypad(1)

stdscr.addstr(5,5,'welcome')
stdscr.refresh()

key = ''

try:
    while key != ord('q'):
        key = stdscr.getch()
        input_processing(drone, key, stdscr)

except (KeyboardInterrupt, SystemExit):
    print 'Root Exception'
    drone.stop()
    curses.endwin()
    raise

drone.stop()
