#!/usr/bin/env python

import time
import threading
import pprint
import copy

import Bybop_NetworkAL
from Bybop_Network import *
from Bybop_Commands import *
from Bybop_Discovery import *
from Bybop_Connection import *
import arsdkparser

MOVE_SPEED = 20


TEST_LAT = 35.859294
TEST_LON = 128.488366
TEST_AT = 1.0


class State(object):
    """
    Three level dictionnary to save the internal state of a Device.

    The first level key is the project of the command.
    The second level key is the project of the classs.
    The third level key is the command.

    The content for each command depends on the command type. For normal commands,
    the content is a dictionnary of arguments in the form { 'name':value ... }. If
    the command is a list command, then the content is a list of arguments dictionnaries.
    If the command is a map command, then the content is a dictionnary of arguments
    dictionnaries, indexed by their first argument.

    This class use internal locks to allow proper multithread access.

    This class also implements a wait_for function to do non-busy wait for commands
    reception (i.e. wait for an answer from the device), with an optionnal timeout.
    """

    def __init__(self):
        """
        Create a new, empty, state.

        Creating a new state should only be done from an Device __init__ function.
        """
        self._dict = {}
        self._waitlist = {}
        self._lock = threading.Lock()
        self._waitid = 0

    def _getcldic(self, pr, cl, create=True):
        if not pr in self._dict:
            if create:
                self._dict[pr] = {}
            else:
                return None
        pr_d = self._dict[pr]
        if not cl in pr_d:
            if create:
                pr_d[cl] = {}
            else:
                return None
        return pr_d[cl]

    def wait_for(self, name, timeout=None):
        """
        Wait for a change on the given key.

        Return True if the key changed, False if a timeout occured

        Arguments:
        - name : The command to watch, in 'project.class.command' notation

        Keyword arguments:
        - timeout : Timeout, in floating point seconds, for the wait
        """
        with self._lock:
            event = threading.Event()
            wid = self._waitid
            self._waitid += 1
            if not name in self._waitlist:
                self._waitlist[name] = {}
            self._waitlist[name][wid] = event

        res = event.wait(timeout)

        with self._lock:
            if res:
                event.clear()
            del self._waitlist[name][wid]
            if not self._waitlist[name]:
                del self._waitlist[name]
        return res

    def _signal_waiting(self, pr, cl, cmd):
        waitname = '%s.%s.%s' % (pr, cl, cmd)
        if waitname in self._waitlist:
            for k, v in self._waitlist[waitname].iteritems():
                v.set()

    def put(self, pr, cl, cmd, args):
        """
        Put a new command in the dictionnary.

        This function only handles normal commands. For list or map commands,
        see put_list or put_map functions.

        Arguments:
        - pr : Project name of the command
        - cl : Class name of the command
        - cmd : Name of the commands
        - args : Arguments dictionnary of the command
        """
        with self._lock:
            pr_cl = self._getcldic(pr, cl)
            if cmd in pr_cl:
                del pr_cl[cmd]
            pr_cl[cmd] = copy.deepcopy(args)
            self._signal_waiting(pr, cl, cmd)

    def put_list(self, pr, cl, cmd, args):
        """
        Put a new list-command in the dictionnary.

        This function handles list-commands by appending the arguments dictionnary
        to the command list.

        Arguments:
        - pr : Project name of the command
        - cl : Class name of the command
        - cmd : Name of the commands
        - args : Arguments dictionnary of the command
        """
        with self._lock:
            pr_cl = self._getcldic(pr, cl)
            if not cmd in pr_cl:
                pr_cl[cmd] = []
            pr_cl[cmd].append(copy.deepcopy(args))
            self._signal_waiting(pr, cl, cmd)

    def put_map(self, pr, cl, cmd, args, key):
        """
        Put a new map-command in the dictionnary.

        This function saves the arguments dictionnary, indexed by its first element, in
        the command disctionnary.

        Arguments:
        - pr : Project name of the command
        - cl : Class name of the command
        - cmd : Name of the commands
        - args : Arguments dictionnary of the command
        - key : Value of the first argument of the command
        """
        with self._lock:
            pr_cl = self._getcldic(pr, cl)
            if not cmd in pr_cl:
                pr_cl[cmd] = {}
            pr_cl[cmd][key] = copy.deepcopy(args)
            self._signal_waiting(pr, cl, cmd)

    def get_value(self, name):
        """
        Get the current value of a command.

        For never received commands, None is returned
        For normal commands, an arguments dictionnary in the { 'name':value ... } format is
        returned. For list-commands, a list of such disctionnaries is returned. For map-commands,
        a dictionnary of such dictionnaries is returned.

        Arguments:
        - name : The command to get, in 'project.class.command' notation
        """
        try:
            pr, cl, cmd = name.split('.')
        except ValueError:
            return None
        with self._lock:
            pr_cl = self._getcldic(pr, cl)
            if pr_cl is None:
                #print 'ERROR : State.get_value pr_cl is None'
                ret = None
            elif not cmd in pr_cl:
                #print 'ERROR : State.get_value cmd not in pr_cl'
                ret = None
            else:
                ret = copy.deepcopy(pr_cl[cmd])
        return ret

    def duplicate(self):
        """
        Return a new, non-synchronized (i.e. pure dict) copy of the internal dictionnary.
        """
        with self._lock:
            ret = copy.deepcopy(self._dict)
        return ret

    def dump(self):
        """
        Dump the current state using a pretty printer.

        This is useful for debugging purposes, to see the whole product state.
        """
        with self._lock:
            pprint.pprint(self._dict)


class Device(object):
    """
    Simple wrapper around ARNetwork + ARCommands.

    This class is subclassed for each device to add convenience functions, and proper
    initialization. It should not be used directly.
    """

    def __init__(self, ip, c2d_port, d2c_port, ackBuffer=-1, nackBuffer=-1, urgBuffer=-1, cmdBuffers=[],
                 skipCommonInit=False, verbose=False):
        """
        Create and start a new Device.

        The connection must have been started beforehand by Connection.connect().

        Arguments:
        - ip : The product ip address
        - c2d_port : The remote port (on which we will send data)
        - d2c_port : The local port (on which we will read data)
        - ackBuffer : The buffer for acknowledged data (-1 means no buffer)
        - nackBuffer : The buffer for non acknowledged data (-1 means no buffer)
        - urgBuffer : The buffer for high priority data (-1 means no buffer)
        - cmdBuffers : The buffers from the device which contains ARCommands
        - skipCommonInit : Skip the common init phase (only for SkyController)
        - verbose : Set verbose mode (prints sent/received commands)
        """
        self._verbose = verbose
        inb = [i for i in (ackBuffer, nackBuffer, urgBuffer) if i > 0]
        outb = cmdBuffers
        self._network = Network(ip, c2d_port, d2c_port, inb, outb, self)
        self._ackBuffer = ackBuffer
        self._nackBuffer = nackBuffer
        self._urgBuffer = urgBuffer
        self._cmdBuffers = cmdBuffers
        self._state = State()
        if not skipCommonInit:
            self._common_init_product()
        self._init_product()

    def data_received(self, buf, data):
        """
        Save the recieved data in the state.

        This function is called by the internal Network, and should not be called
        directly by the application.
        """
        if buf in self._cmdBuffers:
            dico, ok = unpack_command(data)
            if not ok:
                return

            pr, cl, cmd = dico['proj'], dico['class'], dico['cmd']

            try:
                args = dico['args']
                key = dico['arg0']
            except:
                args = {}
                key = 'no_arg'

            if self._verbose:
                print 'Received command : ' + str(dico)

            type_ = dico['listtype']
            if type_ == arsdkparser.ArCmdListType.NONE:
                self._state.put(pr, cl, cmd, args)
            elif type_ == arsdkparser.ArCmdListType.LIST:
                self._state.put_list(pr, cl, cmd, args)
            elif type_ == arsdkparser.ArCmdListType.MAP:
                self._state.put_map(pr, cl, cmd, args, key)

    def did_disconnect(self):
        """
        Called when the product is disconnected.

        The application should not call this function directly.
        """
        print 'Product disconnected !'
        self.stop()

    def get_state(self, copy=True):
        """
        Get the product state.

        Arguments:
        - copy : if True, this function will return a pure dictionnary copy of the state
                 if False, this function will return a reference to the internal state
                 (default True)

        When requesting a non-copy state, the application should NEVER try to modify it.

        To get a value from the internal state, use its 'get_value' function.
        """
        if copy:
            return self._state.duplicate()
        else:
            return self._state

    def get_battery(self):
        """
        Get the current battery percentage.
        """
        try:
            return self._state.get_value('common.CommonState.BatteryStateChanged')['percent']
        except:
            return 0

    def set_cali(self):
        try:
            return self.send_data('common.Calibration.MagnetoCalibration', 1)
        except:
            return False

    def get_cali(self, stdscr):
        stdscr.clear()
        stdscr.addstr(9, 13, '[ Do you need Cali? ]')
        stdscr.refresh()
        """
        Get the current cali state.
        """
        rtn = ''
        x = 1
        y = 1
        z = 1
        try:
            cali_required = self._state.get_value('common.CalibrationState.MagnetoCalibrationRequiredState')['required']
            if cali_required == 1:
                self.send_data('common.Calibration.MagnetoCalibration', 1)
                stdscr.addstr(10, 15, '- Cali required')
                stdscr.refresh()
            elif cali_required == 0:
                stdscr.addstr(10, 15, '+ Cali not required')
                stdscr.refresh()
                time.sleep(2)
                return

            self.wait_answer('common.CalibrationState.MagnetoCalibrationStateChanged')

            stdscr.clear()
            stdscr.addstr(10, 13, 'Go calibration...')
            stdscr.refresh()

            while True:
                rtn = 'Follow as zAxis -> yAxis -> xAxis\n'
                values = self._state.get_value('common.CalibrationState.MagnetoCalibrationStateChanged')

                if values['zAxisCalibration'] == 1:
                    rtn += '\n\t\t+ z Axis done(YAW)\t\t'
                    z = 0
                else:
                    rtn += '\n\ts\t- z Axis required(YAW)'
                if values['yAxisCalibration'] == 1:
                    rtn += '\n\t\t+ y Axis done(PITCH)\t\t'
                    y = 0
                else:
                    rtn += '\n\t\t- y Axis required(PITCH)'
                if values['xAxisCalibration'] == 1:
                    rtn += '\n\t\t+ x Axis done(ROLL)\t\t'
                    x = 0
                else:
                    rtn += '\n\t\t- x Axis required(ROLL)'
                stdscr.addstr(12, 15, rtn)
                stdscr.refresh()
                time.sleep(1)
                if x == 0 and z == 0 and y == 0:
                    stdscr.clear()
                    stdscr.addstr(10, 13, 'Cali DONE!!')
                    stdscr.refresh()
                    time.sleep(2)
                    break
        except:
            raise

    def get_mav_availability(self, stdscr):
        stdscr.clear()
        stdscr.addstr(9, 13, '[ Is Mavlink file available? ]')
        stdscr.refresh()
        script = ''

        try:
            rtn = self._state.get_value('common.FlightPlanState.AvailabilityStateChanged')['AvailabilityState']
            if rtn == 1:
                stdscr.addstr(10, 15, '+ FlightPlan is available')
            else:
                stdscr.addstr(10, 15, '- FlightPlan is not available')
            stdscr.refresh()
            time.sleep(2)
            return rtn
        except:
            return 0

#===Is Work?=====
    def get_mav_state(self, stdscr):
        stdscr.clear()
        stdscr.addstr(9,13,'[ Can you run Mavlink? ]')
        stdscr.refresh()
        script = ''

        try:
            self.send_data('common.Common.AllStates')
            self.wait_answer('common.CommonState.AllStatesChanged')
            values = self._state.get_value('common.FlightPlanState.ComponentStateListChanged')
            #gps, cali, mav, takeoff = self._state.get_value('common.FlightPlanState.ComponentStateListChanged')
            gps_state = values[0]['State']
            cali_state = values[1]['State']
            mav_state = values[2]['State']
            takeoff_state = values[3]['State']

            if gps_state == 1:
                script += '+ GPS get ready\n\n'
            elif gps_state == 0:
                script += '- GPS is not ready\n\n'
            if cali_state == 1:
                script += '\t\t+ Cali get ready\n\n'
            elif cali_state == 0:
                script += '\t\t- Cali is not ready\n\n'
            if mav_state == 1:
                script += '\t\t+ Mav get ready\n\n'
            elif mav_state == 0:
                script += '\t\t- Mav is not ready\n\n'
            if takeoff_state == 1:
                script += '\t\t+ Takeoff get ready\n\n'
            elif takeoff_state == 0:
                script += '\t\t- Takeoff is not ready\n\n'


            stdscr.addstr(11, 16, script)
            stdscr.refresh()
            time.sleep(1)

            if (gps_state * cali_state * mav_state * takeoff_state) == 1:
                return True
            else:
                return False
        except Exception as e:
            return False

    def get_gps(self):
        """
        Get the current position.
        """
        try:
            values = self._state.get_value('ardrone3.PilotingState.GpsLocationChanged')
            at = values['altitude']
            lat = values['latitude']
            lon = values['longitude']
            TEST_AT = at
            return at, lat, lon
        except:
            return -1, -1, -1

    def get_altitude(self):
        try:
            return self._state.get_value('ardrone3.PilotingState.AltitudeChanged')['altitude']
        except:
            return -1

    def get_attitude(self):
        try:
            values = self._state.get_value('ardrone3.PilotingState.AttitudeChanged')
            pitch = values['pitch']
            roll = values['roll']
            yaw = values['yaw']
            return pitch, roll, yaw
        except:
            return -1, -1, -1

    def get_home_type(self):
        try:
            values = self._state.get_value('ardrone3.GPSState.HomeTypeChosenChanged')
            typ = values['type']
            return typ
        except:
            return -1

    def get_test_hometype(self, stdscr):
        stdscr.clear()
        stdscr.addstr(9, 13, '[ Can you run Return Home? ]')
        stdscr.refresh()
        script = ''
        try:
            #values = self._state.get_value('ardrone3.GPSState.HomeTypeChosenChanged')
            #typ = values['type']
            typ = self.get_home_type()

            if typ == 0:
                script = 'The drone will try to return to the take off position'
            elif typ == 1:
                script = 'The drone will try to return to the pilot position'
            elif typ == 2:
                script = 'The drone has not enough information, it will try to return to the first GPS fix'

            stdscr.addstr(11, 16, script)
            stdscr.refresh()
            time.sleep(2)
            return typ
        except:
            return -1

    def get_realtime_data(self):
        at, lat, lon = self.get_gps()
        battery = self.get_battery()
        back_home_typ = self.get_home_type()
        altitude = self.get_altitude()

        gps = str(lat) + '/' + str(lon)
        bat = str(battery)
        if back_home_typ == 0:
            bhtyp = 'take-off'
        elif back_home_typ == 1:
            bhtyp = 'pilot'
        else:
            bhtyp = 'GPS err'
        alt = str(altitude)

        return gps, bat, bhtyp, alt

    def send_contoller_gps(self, x, y):
        try:
            return self.send_data('ardrone3.GPSSettings.SendControllerGPS', x, y, 1, 0.5, 0.5)
        except:
            return -1

    def go_node(self):
        try:
            return self.send_data('ardrone3.Piloting.NavigateHome', 1)
        except:
            return -1

    def get_home_position(self):
        try:
            values = self._state.get_value('ardrone3.GPSSettingsState.HomeChanged')
            at = values['altitude']
            lat = values['latitude']
            lon = values['longitude']
            return at, lat, lon
        except:
            return -1, -1, -1

    def get_reset_home_position(self):
        try:
            values = self._state.get_value('ardrone3.GPSSettingsState.ResetHomeChanged')
            at = values['altitude']
            lat = values['latitude']
            lon = values['longitude']
            return at, lat, lon
        except:
            return -1, -1, -1

    def set_max_altitude(self, alt):
        try:
            self.send_data('ardrone3.PilotingSettings.MaxAltitude', alt)
        except:
            return -1

    def set_home_type(self):
        try:
            self.send_data('ardrone3.GPSSettings.HomeType', 1)
        except:
            return -1

    def reset_node(self):
        try:
            return self.send_data('ardrone3.GPSSettings.ResetHome')
        except:
            return -1

    def get_return_home_state(self):
        try:
            values = self._state.get_value('ardrone3.PilotingState.NavigateHomeStateChanged')
            reason = values['reason']
            state = values['state']
            return state, reason
        except:
            return -1, -1

    def send_data(self, name, *args, **kwargs):
        """
        Send some command to the product.

        Return a NetworkStatus value.

        Arguments:
        - name : The command to send, in 'project.class.command' notation
        - *args : arguments to the command

        Keyword arguments:
        - retries : number of retries (default 5)
        - timeout : timeout (seconds) per try for acknowledgment (default 0.15)
        """
        try:
            pr, cl, cm = name.split('.')
            cmd, buf, to = pack_command(pr, cl, cm, *args)
        except CommandError as e:
            print 'Bad command !' + str(e)
            return NetworkStatus.ERROR
        bufno = -1
        if buf == arsdkparser.ArCmdBufferType.NON_ACK:
            bufno = self._nackBuffer
            datatype = Bybop_NetworkAL.DataType.DATA
        elif buf == arsdkparser.ArCmdBufferType.ACK:
            bufno = self._ackBuffer
            datatype = Bybop_NetworkAL.DataType.DATA_WITH_ACK
        elif buf == arsdkparser.ArCmdBufferType.HIGH_PRIO:
            bufno = self._urgBuffer
            datatype = Bybop_NetworkAL.DataType.DATA_LOW_LATENCY

        if bufno == -1:
            print 'No suitable buffer'
            return NetworkStatus.ERROR

        retries = kwargs['retries'] if 'retries' in kwargs else 5
        timeout = kwargs['timeout'] if 'timeout' in kwargs else 0.15

        status = self._network.send_data(bufno, cmd, datatype, timeout=timeout, tries=retries + 1)

        if status == 0 and self._verbose:
            print 'Sent command %s.%s.%s with args %s' % (pr, cl, cm, str(args))

        return status

    def wait_answer(self, name, timeout=5.0):
        """
        Wait for an answer from the product.

        This function will block until the product sends the requested command, or the timeout
        is expired.

        Return True if the command was received, False if a timeout occured.

        Arguments:
        - name : The command to wait, in 'project.class.command' notation

        Keyword arguments:
        - timeout : Maximum time (floating point seconds) to wait (default 5.0)
        """
        status = self._state.wait_for(name, timeout=timeout)
        return status

    def _init_product(self):
        raise NotImplementedError('Do not use Device directly !')

    def _common_init_product(self):
        now = time.gmtime()
        dateStr = time.strftime('%Y-%m-%d', now)
        timeStr = time.strftime('T%H%M%S+0000', now)
        self.send_data('common.Common.CurrentDate', dateStr)
        self.send_data('common.Common.CurrentTime', timeStr)
        self.send_data('common.Settings.AllSettings')
        self.wait_answer('common.SettingsState.AllSettingsChanged')
        self.send_data('common.Common.AllStates')
        self.wait_answer('common.CommonState.AllStatesChanged')

    def dump_state(self):
        print 'Internal state :'
        self._state.dump()

    def stop(self):
        self._network.stop()

    def set_verbose(self, verbose):
        self._verbose = verbose


class BebopDrone(Device):
    def __init__(self, ip, c2d_port, d2c_port):
        """
        Create and start a new BebopDrone device.

        The connection must have been started beforehand by Connection.connect().

        Arguments:
        - ip : The product ip address
        - c2d_port : The remote port (on which we will send data)
        - d2c_port : The local port (on which we will read data)
        """
        super(BebopDrone, self).__init__(ip, c2d_port, d2c_port, ackBuffer=11, nackBuffer=10, urgBuffer=12,
                                         cmdBuffers=[127, 126])

    def _init_product(self):
        # Deactivate video streaming
        self.send_data('ardrone3.MediaStreaming.VideoEnable', 0)

    def trim(self):
        return self.send_data('ardrone3.Piloting.FlatTrim')

    def take_off(self):
        """
        Send a take off request to the Bebop Drone.
        """
        self.send_data('ardrone3.Piloting.TakeOff')

    def land(self):
        """
        Send a landing request to the Bebop Drone.
        """
        self.send_data('ardrone3.Piloting.Landing')

    def emergency(self):
        """
        Send an emergeny request to the Bebop Drone.

        An emergency request shuts down the motors.
        """
        self.send_data('ardrone3.Piloting.Emergency')

    def move(self, flag, roll, pitch, yaw, gaz ):
        self.send_data('ardrone3.Piloting.PCMD', flag, roll, pitch, yaw, gaz, 0.0)

    def hover(self):
        self.move(1, 0, 0, 0, 0)

    def up(self):
        self.move(1, 0, 0, 0, MOVE_SPEED)

    def down(self):
        self.move(1, 0, 0, 0, -MOVE_SPEED)

    def side_left(self):
        self.move(1, -MOVE_SPEED, 0, 0, 0)

    def side_right(self):
        self.move(1, MOVE_SPEED, 0, 0, 0)

    def forward(self):
        self.move(1, 0, MOVE_SPEED, 0, 0)

    def rear(self):
        self.move(1, 0, -MOVE_SPEED, 0, 0)

    def roll_left(self):
        self.move(1, 0, 0, -MOVE_SPEED, 0)

    def roll_right(self):
        self.move(1, 0, 0, MOVE_SPEED, 0)


class JumpingSumo(Device):
    def __init__(self, ip, c2d_port, d2c_port):
        """
        Create and start a new JumpingSumo device.

        The connection must have been started beforehand by Connection.connect().

        Arguments:
        - ip : The product ip address
        - c2d_port : The remote port (on which we will send data)
        - d2c_port : The local port (on which we will read data)
        """
        super(JumpingSumo, self).__init__(ip, c2d_port, d2c_port, ackBuffer=11, nackBuffer=10, cmdBuffers=[127, 126])

    def _init_product(self):
        # Deactivate video streaming
        self.send_data('jpsumo.MediaStreaming.VideoEnable', 0)

    def change_posture(self, posture):
        """
        Change the posture of the JumpingSumo.

        Arguments:
        - posture : integer value corresponding to the posture requested

        Possible values are found in the ARCommands xml file (0 then grows)
        Currently known values:
        - 0 : standing
        - 1 : jumper
        - 2 : kicker
        """
        return self.send_data('jpsumo.Piloting.Posture', posture)

    def change_volume(self, volume):
        """
        Change the volume of the JumpingSumo.

        Arguments:
        - volume : integer value [0; 100] : percentage of maximum volume.
        """
        return self.send_data('jpsumo.AudioSettings.MasterVolume', volume)

    def jump(self, jump_type):
        """
        Make the JumpingSumo jump.

        Arguments:
        - jump_type : integer value corresponding to the type of jump requested

        Possible values are found in the ARCommands xml file (0 then grows)
        Currently known values:
        - 0 : long
        - 1 : high
        """
        return self.send_data('jpsumo.Animations.Jump', jump_type)


class SkyController(Device):
    def __init__(self, ip, c2d_port, d2c_port):
        """
        Create and start a new SkyController device.

        The connection must have been started beforehand by Connection.connect().

        Arguments:
        - ip : The product ip address
        - c2d_port : The remote port (on which we will send data)
        - d2c_port : The local port (on which we will read data)
        """
        super(SkyController, self).__init__(ip, c2d_port, d2c_port, ackBuffer=11, nackBuffer=10, urgBuffer=12,
                                            cmdBuffers=[127, 126], skipCommonInit=True)

    def _init_product(self):
        self.send_data('skyctrl.Settings.AllSettings')
        self.wait_answer('skyctrl.SettingsState.AllSettingsChanged')
        self.send_data('skyctrl.Common.AllStates')
        self.wait_answer('skyctrl.CommonState.AllStatesChanged')


def create_and_connect(device, d2c_port, controller_type, controller_name):
    device_id = get_device_id(device)
    ip = get_ip(device)
    port = get_port(device)
    if device_id not in DeviceID.ALL:
        print 'Unknown product ' + device_id
        return None

    connection = Connection(ip, port)
    answer = connection.connect(d2c_port, controller_type, controller_name)
    if not answer:
        print 'Unable to connect'
        return None
    if answer['status'] != 0:
        print 'Connection refused'
        return None

    c2d_port = answer['c2d_port']

    if device_id == DeviceID.BEBOP_DRONE or device_id == DeviceID.BEBOP_2:
        return BebopDrone(ip, c2d_port, d2c_port)
    elif device_id == DeviceID.JUMPING_SUMO or device_id == DeviceID.JUMPING_NIGHT or device_id == DeviceID.JUMPING_RACE:
        return JumpingSumo(ip, c2d_port, d2c_port)
    elif device_id == DeviceID.SKYCONTROLLER or device_id == DeviceID.SKYCONTROLLER_2:
        return SkyController(ip, c2d_port, d2c_port)
    return None
