README.txt

Tim Goodwin
tlg2132
CSEE4119
Programming Assignment 1
October 8th, 2015

All source code written by Timothy Goodwin in 2015.

---------- BRIEF DESCRIPTION OF MY CODE ----------
1. Server.py
This is the chat server written in python. All requests are handled through this server. The server handles multiple TCP connections using the select() method.
In addition to handling connections, the server implements all functionalities specified in this assignment. Connections are authenticated using the user-password pairs provided in the handout.

2. Client.py
The client side program sends requests to the server and prints any data received from the server to the command line. The program also uses the select() method to simultaneously handle activity from the server TCP connection as well as from the user (stdin).

---------- DETAILS ON DEVELOPMENT ENVIRONMENT ----------
All of my source code was written using GitHub's Atom text editor. Programs were tested using Python 2.7.

---------- HOW TO RUN THIS CODE ----------

step 1: run the server program on an available port of your choosing
for example, type the following:
python Server.py 4119

step 2: run the client program on the IP address of the machine running Server.py, also using the same port number.
for example, type the following:
python Client.py 127.0.0.1 4119

---------- ADDITIONAL FUNCTIONALITY ----------

1. Whenever someone enters or leaves room, it is made known to other users.
2. Offline messaging - the server will deliver all messages sent privately to the user while that user was offline. Broadcasted, blasted messages are not personal and important enough to be saved on the server's resources.
