#!/usr/bin/env python

import sys
import os
import curses
import code
import readline
import rlcompleter
import time

sys.path.append('../src')

from Bybop_Discovery import *
import Bybop_Device

BAT_PRINT_X = 5
BAT_PRINT_Y = 2

KEY_PRINT_X = 5
KEY_PRINT_Y = 3

MAV_PRINT_X = 5
MAV_PRINT_Y = 5

GPS_PRINT_X = 5
GPS_PRINT_Y = 7

ALT_PRINT_X = 5
ALT_PRINT_Y = 12

ATT_PRINT_X = 5
ATT_PRINT_Y = 14

HOME_PRINT_X = 5
HOME_PRINT_Y = 19

RST_HOME_PRINT_X = 5
RST_HOME_PRINT_Y = 24

HOME_STATE_PRINT_X = 5
HOME_STATE_PRINT_Y = 29

def log(stdscr, str):
    stdscr.addstr(10, 20, '[DEBUG] : ' + str)

def input_processing(drone, key, stdscr):
    hometype = 2
    if key == 65 or key == curses.KEY_UP: #UP
        stdscr.addstr(KEY_PRINT_Y, KEY_PRINT_X, 'UP')
        #stdscr.refresh()
        drone.up()
    elif key == 66 or key == curses.KEY_DOWN: #DOWN
        stdscr.addstr(KEY_PRINT_Y, KEY_PRINT_X, 'DOWN')
        #stdscr.refresh()
        drone.down()
    elif key == 68 or key == curses.KEY_LEFT: #SIDE LEFT
        stdscr.addstr(KEY_PRINT_Y, KEY_PRINT_X, 'SIDE LEFT')
        #stdscr.refresh()
        drone.side_left()
    elif key == 67 or key == curses.KEY_RIGHT: #SIDE RIGHT
        stdscr.addstr(KEY_PRINT_Y, KEY_PRINT_X, 'SIDE RIGHT')
        #stdscr.refresh()
        drone.side_right()
    elif key == 101 or key == 'e': #EMERGENCY
        stdscr.addstr(KEY_PRINT_Y, KEY_PRINT_X, 'EMERGENCY')
        #stdscr.refresh()
        drone.emergency()
        time.sleep(3)
    elif key == 116 or key == 't': #TAKEOFF
        stdscr.addstr(KEY_PRINT_Y, KEY_PRINT_X, 'TAKE OFF')
        #stdscr.refresh()
        drone.take_off()
    elif key == 32 or key == '  ': #LAND
        stdscr.addstr(KEY_PRINT_Y, KEY_PRINT_X, 'LAND')
        #stdscr.refresh()
        drone.land()
    elif key == 114 or key == 'r': #FORWARD
        stdscr.addstr(KEY_PRINT_Y, KEY_PRINT_X, 'FORWARD')
        #stdscr.refresh()
        drone.forward()
    elif key == 102 or key == 'f': #REAR
        stdscr.addstr(KEY_PRINT_Y, KEY_PRINT_X, 'REAR')
        #stdscr.refresh()
        drone.rear()
    elif key == 100 or key == 'd': #ROLL LEFT
        stdscr.addstr(KEY_PRINT_Y, KEY_PRINT_X, 'ROLL LEFT')
        #stdscr.refresh()
        drone.roll_left()
    elif key == 103 or key == 'g': #ROLL RIGHT
        stdscr.addstr(KEY_PRINT_Y, KEY_PRINT_X, 'ROLL RIGHT')
        #stdscr.refresh()
        drone.roll_right()
    elif key == 109 or key == 'm': #Mav Mode
        cnt = 1
        while drone.get_mav_state(stdscr) is not True:
            if cnt == 3:
                stdscr.clear()
                stdscr.addstr(MAV_PRINT_Y, MAV_PRINT_X, 'MAV Doesnt work :(')
                stdscr.refresh()
                time.sleep(2)
                break
            cnt = cnt +1
            stdscr.clear()
        if(cnt < 3):
            stdscr.clear()
            stdscr.addstr(MAV_PRINT_Y, MAV_PRINT_X, 'MAV WORKS GOOD!!!')
            stdscr.refresh()
            time.sleep(2)
    elif key == 104 or key == 'h': #home
        drone.send_contoller_gps()
        hometype = drone.get_test_hometype(stdscr)
    elif key == 97 or key == 'a':
        if hometype is not 2:
            drone.go_node()
    else:
        stdscr.addstr(KEY_PRINT_Y, KEY_PRINT_X,'None : ' + str(key) + ' pressed')
        stdscr.refresh()
        #drone.trim()
        drone.hover()

def print_battery(drone, stdscr):
    bat = drone.get_battery()
    stdscr.addstr(BAT_PRINT_Y, BAT_PRINT_X, 'battery : ' + str(bat))

def print_gps(drone, stdscr):
    at, lat, lon = drone.get_gps();
    rtn = '>>current_gps'
    rtn += '\n\taltitude\t: ' + str(at)
    rtn += '\n\tlatitude\t: ' + str(lat)
    rtn += '\n\tlongitude\t: ' + str(lon)
    stdscr.addstr(GPS_PRINT_Y, GPS_PRINT_X, rtn)
    #stdscr.refresh()

def print_altitude(drone, stdscr):
    alt = drone.get_altitude()
    rtn = '>>'
    rtn += 'realtime_altitde\t: ' + str(alt)
    stdscr.addstr(ALT_PRINT_Y, ALT_PRINT_X, rtn)
    #stdscr.refresh()

def print_attitude(drone, stdscr):
    pitch, roll, yaw = drone.get_attitude()
    rtn = '>>realtime_attitude'
    rtn += '\n\tpitch\t: ' + str(pitch)
    rtn += '\n\troll\t: ' + str(roll)
    rtn += '\n\tyaw\t: ' + str(yaw)
    stdscr.addstr(ATT_PRINT_Y, ATT_PRINT_X, rtn)
    #stdscr.refresh()

def print_home_position(drone, stdscr):
    at, lat, lon = drone.get_home_position()
    rtn = '>>realtime_home_position'
    rtn += '\n\taltitude\t: ' + str(at)
    rtn += '\n\tlatitude\t: ' + str(lat)
    rtn += '\n\tlongitude\t: ' + str(lon)
    stdscr.addstr(HOME_PRINT_Y, HOME_PRINT_X, rtn)

def print_reset_home_position(drone, stdscr):
    at, lat, lon = drone.get_reset_home_position()
    rtn = '>>realtime_reset_home_position'
    rtn += '\n\taltitude\t: ' + str(at)
    rtn += '\n\tlatitude\t: ' + str(lat)
    rtn += '\n\tlongitude\t: ' + str(lon)
    stdscr.addstr(RST_HOME_PRINT_Y, RST_HOME_PRINT_X, rtn)

def print_return_home_state(drone, stdscr):
    state, reason = drone.get_return_home_state()
    rtn = '>>realtime_return_home_state'
    rtn += '\n\tstate\t: '
    if state is 0:
        rtn += 'available'
    elif state is 1:
        rtn += 'inProgress'
    elif state is 2:
        rtn += 'unavailable'
    elif state is 3:
        rtn += 'pending (Navigate home has been received, but its process is pending)'
    else:
        rtn += 'Not Yet'

    rtn += '\n\treason\t: '
    if reason is 0:
        rtn += 'userRequest'
    elif reason is 1:
        rtn += 'connectionLost'
    elif reason is 2:
        rtn += 'lowBattery'
    elif reason is 3:
        rtn += 'finished'
    elif reason is 4:
        rtn += 'stopped'
    elif reason is 5:
        rtn += 'disabled'
    elif reason is 6:
        rtn += 'enabled'
    else :
        rtn += 'Not Yet'

    stdscr.addstr(HOME_STATE_PRINT_Y, HOME_STATE_PRINT_X, rtn)

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


stdscr = curses.initscr()
curses.cbreak()
stdscr.nodelay(1)
stdscr.keypad(1)

stdscr.addstr(2,2,'welcome')
stdscr.refresh()


try:
    drone.get_cali(stdscr)
    drone.get_mav_availability(stdscr)
    drone.set_max_altitude(5)
    drone.set_home_type()
    drone.trim()
    key = ''


    while key != ord('q'):
        stdscr.clear()

        key = stdscr.getch()
        input_processing(drone, key, stdscr)

        print_battery(drone, stdscr)
        print_gps(drone, stdscr)
        print_altitude(drone, stdscr)
        print_attitude(drone, stdscr)
        print_home_position(drone, stdscr)
        print_reset_home_position(drone, stdscr)
        print_return_home_state(drone, stdscr)

        stdscr.refresh()
        time.sleep(0.025) #40MHz / 25ms

except (KeyboardInterrupt, SystemExit, Exception) as e:
    print '[EXCEPTION] ' + str(e)
    drone.stop()
    curses.endwin()
    raise

drone.stop()
