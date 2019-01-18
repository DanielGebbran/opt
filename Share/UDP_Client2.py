#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 16 10:55:18 2019
Socket guide:
    https://realpython.com/python-sockets/
Reference videos:
    https://www.youtube.com/watch?v=YqFwMGzP-44
    https://www.youtube.com/watch?v=ZwxTGGEx-1w
    https://www.youtube.com/watch?v=zpl4Rm5I008
Some UDP theory:
    https://stackoverflow.com/questions/28346352/multi-client-udp-server-python
    https://medium.com/swlh/lets-write-a-chat-app-in-python-f6783a9ac170
    https://stackoverflow.com/questions/5815675/what-is-sock-dgram-and-sock-stream
    
@author: daniel
"""
import socket
import random
import time
import datetime

def Main():
    host = '127.0.0.1'
    port = 5000
    
    try:
        with open('ipaddress.txt', 'r') as f:
            host = f.readline().rstrip()
    except:
        host = '172.16.13.73'
        
    server = (host, port)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((host, 5002))
    
    print ("UDP Client RNG. Using server: ", host, port)
        
    while True:
        # Send Client to Server
        message = 'RNG Testing: %s' % (random.randint(1, 5000))
        current_time = datetime.datetime.now().time()
        print (current_time, "Sending data to server: ", str(message))
        s.sendto(str.encode(message), server)
        
        # Listen to Server
        data, addr = s.recvfrom(1024)
        current_time = datetime.datetime.now().time()
        print (current_time, "<- Received: ", data.decode('utf-8'))
        time.sleep( random.randint(1, 5))
    s.close()
        
if __name__ == "__main__":
    Main()
    
    