#!/usr/bin/python
from __future__ import unicode_literals
import sys
import os
import time
import pigpio
import DHT22
import datetime
from pymongo import Connection
connection = Connection()
db = connection.local
temps = db.temps

pi = pigpio.pi()

window_pin = 23
pi.set_mode (window_pin, pigpio.INPUT)
pi.set_pull_up_down (window_pin, pigpio.PUD_UP)

window_status = pi.read(window_pin)

if window_status == 1 :
    print ("window open")
else :
    print ("window closed")

x = datetime.datetime.today()
minute = ((x.minute -1) / 10) * 10
key2 = datetime.datetime (x.year, x.month, x.day, x.hour, minute)
print key2

current = db.temps.find({'_id' : {"$gte" : key2}}).limit(1)
for i in current :
    line = " Out: {:3.1f}".format(i["outside"]["temp"])
    os.system('banner ' + '"' + line + '"')
    line = "Room: {:3.1f}".format(i["room"]["temp"])
    os.system('banner ' + '"' + line + '"')
    line = "Livi: {:3.1f}".format(i["living_room"]["temp"])
    os.system('banner ' + '"' + line + '"')
    # print i
