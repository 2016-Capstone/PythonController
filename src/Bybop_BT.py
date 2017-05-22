import bleservice
import socket
import errno
import time
from socket import error as SocketError

################
# PRIVATE DELARE#
################

bl = bleservice.Bluetoothctl()

hostMACAddress = 'B8:27:EB:80:FB:37'
port = 3
backlog = 1
size = 1024

IP = '210.125.31.25'
PORT = 443
SERVER = (IP, PORT)

MSG_HELLO = "DVTYPE=1%%MSGTYPE=3\n"


################

def ble_init():
    bl.make_discoverable()
    print("discovered on!")


def ble_scan():
    return bl.get_paired_devices()


def socket_ble_init():
    s_bt.bind((hostMACAddress, port))
    s_bt.listen(backlog)


def socket_ble_recv():
    buf = ''
    conn, addr = s_bt.accept()

    try:
        while True:
            rcv = conn.recv(512)
            if not rcv:
                print "receive success!"
                break
            buf += rcv
    except SocketError as e:
        if e.errno != errno.ECONNRESET:
            raise
        pass
    conn.close()
    return buf


def socket_lte_init():
    s_lte.connect(SERVER)


def socket_lte_send_hello():
    s_lte.sendall(MSG_HELLO)


def socket_lte_send_img(length, img):
    totalsent = 0
    while totalsent < length:
        result = s_lte.send(img)
        if result == 0:
            print 'socket connection broken'
            return
        totalsent += result


########################
##### MAIN ROUTINE #####
########################

if __name__ == "__main__":

    ble_init()

    try:
        while True:
            s_bt = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            s_lte = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_ble_init()

            try:
                print 'Conn try...'
                socket_lte_init()
            except Exception as e:
                print("Wrong connection to %s:%d (%s)" % (IP, PORT, e))
                s_bt.close()
                s_lte.close()
                time.sleep(2)
                continue

            try:
                socket_lte_send_hello()
                print 'Say HELLO'
            except:
                print 'Faile HELLO'
                s_bt.close()
                s_lte.close()
                continue

            while True:
                try:
                    while True:
                        lists = ble_scan()
                        if not lists:
                            print(lists)
                            break
                    print '(BLE)Rcv try...'
                    rcv = socket_ble_recv()
                    rcv += '\n'
                    print(rcv)
                    socket_lte_send_img(len(rcv), rcv)
                    print '(LTE)Send img'
                except Exception as e:
                    print("Err %s" % (e))
                    s_bt.close()
                    s_lte.close()
                    break
    except (KeyboardInterrupt, SystemExit):
        raise
