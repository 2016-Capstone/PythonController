import socket
import os
import sys
import time
import errno
'''
HOST = '210.125.31.25'
PORT = 443
ADDR = (HOST, PORT)
'''

CMD = [65,66,68,67,114,102,100,103,113]

def get_from_LTE(c_socket, locker, fifo):
    while (True):
        '''
        try:
            c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c_socket.connect(ADDR)
            #c_socket.setblocking(0)
        except Exception as e:
            print("Wrong connection to %s:%d (%s)" % (HOST, PORT, e))
            c_socket.close()
            time.sleep(2)
            continue

        try:
            c_socket.send('DVTYPE=1%%MSGTYPE=3\n')
        except Exception as e:
            continue
        '''

        fix = -1
        while (True):
            try:
                locker.acquire()
                data = c_socket.recv(1024)
                locker.release()
                if data == '':
                    break
                if data == 'HELLO\n':
                    continue
                print (repr(data))
                fifo.put(data)
                '''
                cmp = data
                if data in CMD :
                    while cmp is not -1:
                        time.sleep(0.025)
                        c_socket.setblocking(0)
                        try:
                            cmp = c_socket.recv(1024)
                            fifo.put(data)
                        except socket.error, e:
                            fifo.put(data)
                            continue
                    c_socket.setblocking(1)
                '''
            except socket.error, e:
                if e.args[0] == errno.EWOULDBLOCK:
                    fifo.put('none')
                    time.sleep(0.025)  # short delay, no tight loops
                else:
                    print e
                    break
            except (KeyboardInterrupt, SystemExit, Exception):
                c_socket.close()
                #fifo.close()
                print ('\nEND')
                raise Exception

def send_to_LTE(c_socket, locker, gps_q):
        '''
        try:
            c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c_socket.connect(ADDR)
            #c_socket.setblocking(0)
        except Exception as e:
            print("Wrong connection to %s:%d (%s)" % (HOST, PORT, e))
            c_socket.close()
            time.sleep(2)
            continue

        try:
            c_socket.send('DVTYPE=1%%MSGTYPE=3\n')
        except Exception as e:
            continue
        '''
        cnt = 0
        while True:
            try:
                gps = gps_q.get()
                if cnt == 3:
                    locker.acquire()
                    c_socket.send('DVTYPE=1%%MSGTYPE=1%%DATA=' + gps + '\n')
                    c_socket.send("\n")
                    locker.release()
                    cnt = 0
                cnt = cnt + 1

            except (KeyboardInterrupt, SystemExit, Exception):
                c_socket.close()
                # fifo.close()
                print ('\nEND')
                raise Exception
