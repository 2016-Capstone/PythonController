#!/usr/bin/env python

import sys
import os
import curses
import code
import readline
import rlcompleter
import time
import thread
import multiprocessing
import socket

sys.path.append('../src')

from Bybop_Discovery import *
import Bybop_Device
import Constants
import Bybop_LTE


IS_BACK_HOME_IN_PROCESS = True
PATH = './fifo_cmd'
CMD = ['65','66','68','67','114','102','100','103','113']

def log(stdscr, str):
    stdscr.addstr(10, 20, '[DEBUG] : ' + str)

'''
def get_fifo(PATH):
    if not os.path.exists(PATH):
        os.mkfifo(PATH)

    fifo = os.open(PATH, os.O_RDWR)
    return fifo
'''

def get_pipe():
    fd_read, fd_write = os.pipe()
    fd_read = os.fdopen(fd_read, 'r')
    fd_write = os.fdopen(fd_write, 'w')
    return fd_read, fd_write

def get_socket():
    while True:
        try:
            c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c_socket.connect(Constants.ADDR)
            # c_socket.setblocking(0)
        except Exception as e:
            print("Wrong connection to %s:%d (%s)" % (Constants.HOST, Constants.PORT, e))
            c_socket.close()
            time.sleep(2)
            continue

        try:
            c_socket.send('DVTYPE=1%%MSGTYPE=3\n')
        except Exception as e:
            continue

        return c_socket

def input_processing(drone, key, stdscr):
    hometype = 2
    if key == 65 or key == curses.KEY_UP: #UP
        #stdscr.refresh()
        drone.up()
    elif key == 66 or key == curses.KEY_DOWN: #DOWN
        #stdscr.refresh()
        drone.down()
    elif key == 68 or key == curses.KEY_LEFT: #SIDE LEFT
        #stdscr.refresh()
        drone.side_left()
    elif key == 67 or key == curses.KEY_RIGHT: #SIDE RIGHT
        #stdscr.refresh()
        drone.side_right()
    elif key == 101 or key == 'e': #EMERGENCY
        #stdscr.refresh()
        drone.emergency()
        time.sleep(3)
    elif key == 116 or key == 't': #TAKEOFF
        #stdscr.refresh()
        drone.take_off()
    elif key == 32 or key == '  ': #LAND
        #stdscr.refresh()
        drone.land()
    elif key == 114 or key == 'r': #FORWARD
        #stdscr.refresh()
        drone.forward()
    elif key == 102 or key == 'f': #REAR
        #stdscr.refresh()
        drone.rear()
    elif key == 100 or key == 'd': #ROLL LEFT
        #stdscr.refresh()
        drone.roll_left()
    elif key == 103 or key == 'g': #ROLL RIGHT
        #stdscr.refresh()
        drone.roll_right()
    elif key == 109 or key == 'm': #Mav Mode
        cnt = 1
        while drone.get_mav_state(stdscr) is not True:
            if cnt == 3:
                stdscr.clear()
                stdscr.addstr(Constants.MAV_PRINT_Y, Constants.MAV_PRINT_X, 'MAV Doesnt work :(')
                stdscr.refresh()
                time.sleep(2)
                break
            cnt = cnt +1
            stdscr.clear()
        if(cnt < 3):
            stdscr.clear()
            stdscr.addstr(Constants.MAV_PRINT_Y, Constants.MAV_PRINT_X, 'MAV WORKS GOOD!!!')
            stdscr.refresh()
            time.sleep(2)
    elif key == 104 or key == 'h': #home
        drone.send_contoller_gps()
        #drone.reset_node()
        hometype = drone.get_test_hometype(stdscr)
        stdscr.refresh()
        time.sleep(1)
    elif key == 97 or key == 'a':
        drone.go_node()
        rtn = 'Processing...'
        global IS_BACK_HOME_IN_PROCESS
        while IS_BACK_HOME_IN_PROCESS:
            stdscr.clear()
            stdscr.addstr(Constants.KEY_PRINT_Y, Constants.KEY_PRINT_X, rtn)
            stdscr.refresh()
            time.sleep(1)
        IS_BACK_HOME_IN_PROCESS = True

    else:
        stdscr.refresh()
        #drone.trim()
        drone.hover()

def print_battery(drone, stdscr):
    bat = drone.get_battery()
    stdscr.addstr(Constants.BAT_PRINT_Y, Constants.BAT_PRINT_X, 'battery : ' + str(bat))

def print_gps(drone, stdscr):
    at, lat, lon = drone.get_gps();
    rtn = '>>current_gps'
    rtn += '\n\taltitude\t: ' + str(at)
    rtn += '\n\tlatitude\t: ' + str(lat)
    rtn += '\n\tlongitude\t: ' + str(lon)
    stdscr.addstr(Constants.GPS_PRINT_Y, Constants.GPS_PRINT_X, rtn)
    #stdscr.refresh()

def print_altitude(drone, stdscr):
    alt = drone.get_altitude()
    rtn = '>>'
    rtn += 'realtime_altitde\t: ' + str(alt)
    stdscr.addstr(Constants.ALT_PRINT_Y, Constants.ALT_PRINT_X, rtn)
    #stdscr.refresh()

def print_attitude(drone, stdscr):
    pitch, roll, yaw = drone.get_attitude()
    rtn = '>>realtime_attitude'
    rtn += '\n\tpitch\t: ' + str(pitch)
    rtn += '\n\troll\t: ' + str(roll)
    rtn += '\n\tyaw\t: ' + str(yaw)
    stdscr.addstr(Constants.ATT_PRINT_Y, Constants.ATT_PRINT_X, rtn)
    #stdscr.refresh()

def print_home_position(drone, stdscr):
    at, lat, lon = drone.get_home_position()
    rtn = '>>realtime_home_position'
    rtn += '\n\taltitude\t: ' + str(at)
    rtn += '\n\tlatitude\t: ' + str(lat)
    rtn += '\n\tlongitude\t: ' + str(lon)
    stdscr.addstr(Constants.HOME_PRINT_Y, Constants.HOME_PRINT_X, rtn)
"""
def print_reset_home_position(drone, stdscr):
    at, lat, lon = drone.get_reset_home_position()
    rtn = '>>realtime_reset_home_position'
    rtn += '\n\taltitude\t: ' + str(at)
    rtn += '\n\tlatitude\t: ' + str(lat)
    rtn += '\n\tlongitude\t: ' + str(lon)
    stdscr.addstr(RST_HOME_PRINT_Y, RST_HOME_PRINT_X, rtn)
"""

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
        global IS_BACK_HOME_IN_PROCESS
        IS_BACK_HOME_IN_PROCESS = False
    elif reason is 4:
        rtn += 'stopped'
    elif reason is 5:
        rtn += 'disabled'
    elif reason is 6:
        rtn += 'enabled'
    else :
        rtn += 'Not Yet'

    stdscr.addstr(Constants.HOME_STATE_PRINT_Y, Constants.HOME_STATE_PRINT_X, rtn)


def print_state(drone, stdscr):
    print_battery(drone, stdscr)
    print_gps(drone, stdscr)
    print_altitude(drone, stdscr)
    print_attitude(drone, stdscr)
    print_home_position(drone, stdscr)
    # print_reset_home_position(drone, stdscr)
    print_return_home_state(drone, stdscr)


if __name__ == "__main__":

    print 'Searching for devices'

    '''DISCOVERY'''
    discovery = Discovery(DeviceID.ALL)
    discovery.wait_for_change()
    devices = discovery.get_devices()
    discovery.stop()

    if not devices:
        print 'Oops ...'
        sys.exit(1)

    device = devices.itervalues().next()

    '''CONNECT'''
    print 'Will connect to ' + get_name(device)
    d2c_port = 54321
    controller_type = "PC"
    controller_name = "bybop shell"
    drone = Bybop_Device.create_and_connect(device, d2c_port, controller_type, controller_name)

    if drone is None:
        print 'Unable to connect to a product'
        sys.exit(1)

    drone.dump_state()

    '''SHELL SET'''
    vars = globals().copy()
    vars.update(locals())
    readline.set_completer(rlcompleter.Completer(vars).complete)
    readline.parse_and_bind("tab: complete")
    shell = code.InteractiveConsole(vars)

    #shell.interact()

    '''NEW WINDOW'''
    stdscr = curses.initscr()
    curses.cbreak()
    stdscr.nodelay(1)
    stdscr.keypad(1)

    '''FIFO INIT'''
    pipe = multiprocessing.Queue()

    '''SOCKET INIT'''
    c_socket = get_socket()

    try:
        locker = thread.allocate_lock()
        thread.start_new_thread(Bybop_LTE.get_from_LTE, (c_socket, locker, pipe,))

        drone.set_cali()
        drone.get_cali(stdscr)
        #drone.get_mav_availability(stdscr)
        drone.set_max_altitude(5)
        drone.set_home_type()
        drone.trim()

        '''MAIN ROUTINE'''
        key = -1
        #while key != ord('q') or key != '113':
        while key != 113:
            stdscr.clear()

            '''CMD PROCESSING'''
            try:
                key = pipe.get(False)
            except Exception:
                if key not in CMD:
                    key = -1
                'DONOTHING'
            stdscr.addstr(Constants.KEY_PRINT_Y, Constants.KEY_PRINT_X, str(key))
            input_processing(drone, key, stdscr)

            '''PRINTING MODULE'''
            print_state(drone, stdscr)

            stdscr.refresh()
            time.sleep(0.025) #40MHz / 25ms

    except (KeyboardInterrupt, SystemExit, Exception) as e:
        print '[EXCEPTION] ' + str(e)
        drone.stop()
        curses.endwin()
        raise

    drone.stop()
