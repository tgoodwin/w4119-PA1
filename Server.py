"""
server.py
Tim Goodwin
tlg2132
CSEE 4119
"""
import socket
import select
import string
import sys
import signal
import errno
import time

client_list = [] # anyone from anywhere who requests connection
dictionary = {}  # valid username-login pairs from txt file
block_event = {}  # blocked IP addresses map to the time of blocking
block_user = {}  # all blocked username - IP address pairs
active = {}      # dictionary that maps usernames to socket objects
usr_hist = {}    # maps username string to login time
offline = {}     # dictionary of offline usernames to message lists

RECV_BUFFER = 4096  #bytes
BLOCK_TIME = 60     #seconds
LAST_HOUR = 3600    #seconds (1 hour)
TIME_OUT = 1800     #seconds (30 min)
MAX_FAILURES = 3
MAX_BACKLOG = 25

ServSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

class User:
    def __init__(self, name, socket, addr):
        self.name = name
        self.socket = socket
        self.addr = addr
        self.t_zero = int(time.time())

def main():
    if(len(sys.argv) < 2):
        print "usage: python server.py <server_port_no>"
        sys.exit()

    with open('user_pass.txt', 'r') as user_pass:
        for line in user_pass:
            username, userpass = line.split()
            dictionary[username] = userpass
            offline[username] = [] #initialize empty list
    port = int(sys.argv[1])
    ServSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ServSock.bind(('', port)) # accept all interfaces
    ServSock.listen(MAX_BACKLOG)
    signal.signal(signal.SIGINT, close_handler)
    # Add server socket to the list of readable connections
    client_list.append(ServSock)
    print "chat server started on port " + str(port)

    while 1:
        # socket multiplexing via select() method
        try:
            read_sockets, write_sockets, error_sockets = select.select(client_list,[],[], TIME_OUT)
        except select.error, e:
            break
        except socket.error, e:
            break

        # read_sockets from select() is list of sockets with activity to be read
        for sock in read_sockets:
            if sock == ServSock:
                connection, ClntAddr = ServSock.accept()
                connection.settimeout(TIME_OUT)
                client_list.append(connection)
                print "login attempt from (%s, %s)" % ClntAddr
                ip_addr, process = ClntAddr
                # check if this IP address should be blocked
                #if check_status(BLOCK_TIME, ip_addr, block_times):
                name = authenticate_user(connection, dictionary, ip_addr)
                #else:
                #    name = None

                # successful authentication according to user_pass.txt
                if(name != None):
                    person = User(name, connection, ip_addr)
                    active[name] = person
                    usr_hist[name] = int(time.time())
                    print "logged in client: [" + person.name + "]"

                    # if there are messages saved for the user
                    if len(offline[name]) > 0:
                        offline_message(connection, offline[name])
                        offline[name][:] = []

                    broadcast_message(connection, '[' + person.name + ']' + " is online", active)

                # either the case of failed login or still-blocked IP
                else:
                    connection.close()
                    client_list.remove(connection)

            # incoming data from logged-in client socket
            else:
                try:
                    clientname = get_name(sock, active)
                    data = sock.recv(RECV_BUFFER)

                    if data:
                        handle_request(sock, clientname, data)
                    elif not data:
                        try:
                            logout(sock, active)
                        except:
                            sys.exit() #horrible error

                except:
                    broadcast_message(sock, "client " + str(clientname) +" is offline\n", active)
                    print "client (%s) is offline" % clientname
                    logout(sock, active)

    ServSock.close()
    client_list.remove(ServSock)

#------------------------- END OF MAIN ----------------------------------------
def prompt(sock):
    try:
        sock.send("command: ")
    except:
        return

def authenticate_user(sock, user_dict, ip_addr):
    n = 0
    unverified = True
    try:
        while(unverified):
            sock.send("Username: ")
            username = sock.recv(RECV_BUFFER).strip()
            if block_user.has_key(username):
                if check_status(BLOCK_TIME, ip_addr, block_event) == False:
                    return None
                else:
                    del block_user[username]

            if active.has_key(username): #WORKS NOW
                sock.send("this account is already logged in.\n")
                continue
            elif(user_dict.has_key(username)): #valid logins from txt file
                correct_value = user_dict.get(username)
                while(n < MAX_FAILURES):
                    sock.send("Password: ")
                    password = sock.recv(RECV_BUFFER).strip()
                    if password == correct_value:
                        sock.send("welcome to the room, %s.\n" % username)
                        unverified = False
                        return username
                        break
                    elif correct_value != password:
                        n += 1
                        sock.send("incorrect password - " + str(n) + " of " + str(MAX_FAILURES) + " attempts.\n")
                sock.send("You are blocked for messing up.\n")
                block_user[username] = ip_addr
                block(ip_addr, block_event)

                return None
                break
            else:
                sock.send("Username not recognized.\n")
                continue
            #------ end of authentication loop -------
    except:
        return None

def handle_request(sock, clnt_name, message):
    words = message.split()
    n = len(words)
    if(words[0] == "whoelse"):
        whoelse(sock, active)

    elif(words[0] == "wholast" and n > 1):
        t_elapsed = int(words[1])
        t_elapsed *= 60 # convert to seconds
        wholast(sock, t_elapsed, usr_hist, clnt_name)
        return

    elif(words[0] == "broadcast" and words[1] == "message"):
        substring = words[2:n]
        content = " ".join( substring )
        msg = clnt_name + ": " + content
        broadcast_message(sock, msg, active)

    elif(words[0] == "broadcast" and words[1] == "user"):
        userlist = [] #list of names
        i = 2
        while (words[i] != "message" and i < n):
            userlist.append(words[i])
            i += 1
        i += 1 #move index beyond the word 'message'
        msg_sub = words[i:n]
        space = " "
        ur_content = space.join(msg_sub)
        final_msg = clnt_name + ": " + ur_content
        broadcast_user(sock, userlist, final_msg, active)

    elif(words[0] == "message"):
        target_user = words[1]
        sub = words[2:n]
        s = " "
        your_content = s.join(sub)
        msg = clnt_name + ": " + your_content
        message_user(sock, target_user, msg, active)

    elif(words[0] == "logout" and len(words) == 1):
        goodbye_msg = "[%s] is offline" % clnt_name
        broadcast_message(sock, goodbye_msg, active)
        logout(sock, active)

    else:
        prompt(sock)

# displays all other users currently logged in
def whoelse(sock, usr_dict):
    try:
        for obj in usr_dict.values():
            if obj.socket != ServSock and obj.socket != sock:
                sock.send(obj.name + '\n')
        sock.send("command: ")
    except:
        return

# keeps record of users up to 1 hour in the past.
def wholast(sock, dt, login_hist, clnt_name):
    t_current = int(time.time())
    try:
        for hist_name in login_hist.keys():
            t_elapsed = t_current - login_hist[hist_name]
            if (t_elapsed > LAST_HOUR):
                del login_hist[hist_name]
            elif (t_elapsed < dt and hist_name != clnt_name):
                sock.send(hist_name + '\n')
        sock.send("command: ")
    except:
        return

# sends message to all other users currently logged in
def broadcast_message(sock, message, usr_dict):
    try:
        for obj in usr_dict.values():
            if obj.socket != ServSock and obj.socket != sock:
                obj.socket.send('\n' + message + "\ncommand: ")
        sock.send("command: ")
    except:
        return

# sends message to a client-specified set of users
def broadcast_user(sock, usr_list, message, usr_dict):
    try:
        for usr in usr_list:
            for obj in usr_dict.values():
                if(obj.name == usr):
                    obj.socket.send('\n' + message + "\ncommand: ")
        sock.send("command: ")
    except:
        print "broadcast_user() failed."

# sends a private message to a client-specified user
def message_user(sock, name, message, usr_dict): #WORKIN BITCH
    received = False
    try:
        for obj in usr_dict.values():
            if (obj.name == name):
                obj.socket.send('\n' + message + "\ncommand: ")
                received = True
        if received == False and offline.has_key(name):
            offline[name].append(message)
        sock.send("command: ")
    except:
        print "message_user() failed."

def offline_message(sock, msg_list):
    try:
        sock.send("\nPrivate messages while you were away:\n")
        for old_msg in msg_list:
            sock.send(old_msg + '\n')
        #sock.send("command: ")
    except:
        print "offline_message() failed."

# logs a user out from the chat room and closes their connection
def logout(sock, usr_dict):
    for obj in usr_dict.values():
        if (obj.socket == sock):
            usr_name = obj.name
            del usr_dict[usr_name]
            sock.close()
            client_list.remove(sock)

# block the user's IP address
def block(ip, blacklist):
    t_blocking = int(time.time())
    blacklist[ip] = t_blocking
    print "Blocked IP " + ip + " at time " + str(t_blocking)

# checks if a user should still be blocked from connecting
def check_status(T_BLOCK, ip, blacklist):
    right_now = int(time.time())
    if blacklist.has_key(ip):
        block_elapsed = right_now - blacklist[ip]
        if block_elapsed > T_BLOCK:
            del blacklist[ip]
            return True
        else:
            return False
    else:
        return True

def get_name(sock, usr_dict):
    for obj in usr_dict.values():
        if (obj.socket == sock):
            usr_name = obj.name
            return usr_name


def get_sock(name, usr_dict):
    if usr_dict.has_key(name):
        return usr_dict[name].socket
    else:
        print "get_sock() failed."

def close_handler(signum, frame):
    print "signal " + str(signum) + " called, closing down."
    sys.exit()

if __name__ == "__main__":
    main()
