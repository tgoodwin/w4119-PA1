"""
client.py
Tim Goodwin
CSEE 4119
"""

import socket
import select
import string
import sys
import signal

RECV_BUFFER = 4096

def main():

    if(len(sys.argv) < 3):
        print "usage: python client.py <server_IP_address> <server_port_no>"
        sys.exit()

    host = sys.argv[1]
    port = int(sys.argv[2])

    ServSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ServSock.settimeout(2)
    signal.signal(signal.SIGINT, close_handler)

    try:
        ServSock.connect((host, port))
        sys.stdout.flush()

    # server is offline
    except:
        print 'Unable to contact server.'
        sys.exit()

    while 1: #always-on server
        socket_list = [sys.stdin, ServSock] #Listen to server or stdin
        try:
            read_sockets, write_sockets, error_sockets = select.select(socket_list, [], [])
        except select.error, e:
            break
        except socket.error, e:
            break

        for sock in read_sockets:

            #incoming message from chat server
            if sock == ServSock:
                data = sock.recv(RECV_BUFFER)
                #only case when recv returns 0 bytes is if connection is closed
                if not data:
                    print '\nDisconnected from chat server.'
                    sys.exit()

                # data from server
                else:
                    sys.stdout.write(data)
                    sys.stdout.flush()

            # client typed a message in the command line
            else:
                msg = sys.stdin.readline().strip() #triggers on '\n'
                if msg: ServSock.send(msg)
                sys.stdout.flush()

def close_handler(signum, frame):
    print "signal " + str(signum) + " called, closing down."
    sys.exit()

if __name__ == "__main__":
    main()
