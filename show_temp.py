#!/usr/bin/python
from __future__ import unicode_literals
import sys
import os
import time
import pigpio
import DHT22
import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv
import pprint
import pandas as pd

from pymongo import Connection
connection = Connection()
db = connection.local
temps = db.temps

def plot_month (now):
    # print (now)
    key = datetime.datetime (now.year, now.month, 1, 0, 0)
    end_days = [0,31,29,31,30,31,30,31,31,30,31,30,31]
    #              1  2  3  4  5  6  7  8  9 10 11 12
    last_day = end_days[now.month]
    if now.month == 2 :
        if now.year % 4 == 0 :
            last_day = 29
    
    # print (last_day)
    key2 = datetime.datetime (now.year, now.month, last_day, 23, 59)
    current = db.temps.find({'_id' : {"$gte" : key, "$lt" : key2 }})
    
    with open ('temps.csv', 'w') as csv_file :
        csv_writer = csv.writer (csv_file)
        csv_writer.writerow (['outside','room','living room'])
        
        for i in current :
            if i["_id"].minute == 0 :
                t = i["_id"]
                o = i["outside"]["temp"]
                r = i["room"]["temp"]
                try :
                    l = i["living_room"]["temp"]
                except :
                    l = 0
                if r < 30 :
                    r = l
                if l < 30 :
                    l = r
                hour = "{:02d}".format(t.hour)
                row = [o, r, l]
                csv_writer.writerow(row)
            
    df = pd.read_csv('temps.csv')       
    title = 'Temperature for ' + key.strftime("%B")
    ax = df.plot(title=title)
    ax.set_xlabel("hours")
    ax.set_ylabel("temperature F")
    plt.savefig ('/home/pi/static/monthly.png')
    


def plot_day (date, hourly="Y"):
    delta = datetime.timedelta(days=1)
    next_day = date + delta
    # print (date)
    key = datetime.datetime (date.year, date.month, date.day, 0, 0)
    key2 = datetime.datetime (next_day.year, next_day.month, next_day.day, 0, 0)
    current = db.temps.find({'_id' : {"$gte" : key, "$lt" : key2 }})

    with open ('temps.csv', 'w') as csv_file :
        csv_writer = csv.writer (csv_file)
        csv_writer.writerow (['outside','room','living room'])

        for i in current :
            if i["_id"].minute == 0 or hourly != "Y":
                t = i["_id"]
                o = i["outside"]["temp"]
                r = i["room"]["temp"]
                l = i["living_room"]["temp"]
                if r < 30 :
                    r = l
                if l < 30 :
                    l = r
                hour = "{:02d}".format(t.hour)
                row = [o, r, l]
                csv_writer.writerow(row)

    df = pd.read_csv('temps.csv')
    title = 'Temperature for ' + key.strftime("%B %d")
    if hourly == 'Y' :
        title += " hourly"
    ax = df.plot(title=title)
    if hourly == 'Y' :
        ax.set_xlabel("hours")
    else :
        ax.set_xlabel("10 minute increments")
    ax.set_ylabel("temperature F")
    if hourly == 'Y' :
        plt.savefig ('/home/pi/static/hourly.png')
    else :
        plt.savefig ('/home/pi/static/daily.png')


def average (values):
  return sum(values, 0.0) / len(values)

def check_last_30_minutes (out_temp, room_temp) :
    delta = datetime.timedelta (minutes=-39)
    now = datetime.datetime.today() 
    start = now + delta
    current = temps.find({'_id' : {"$gte" : start}})
    lower_out = 0
    lower_in = 0
    for i in current :
        # print (i["_id"], " out: ", i["outside"]["temp"], "  room:", i["room"]["temp"])
        if out_temp > i["outside"]["temp"] :
           lower_out += 1
        if room_temp > i["room"]["temp"] :
           lower_in += 1
    if lower_in >= 3 and lower_out >= 3 :
       return "close"
    return "open"


pi = pigpio.pi()

degree = u"\u00b0" 

s = DHT22.sensor(pi, 4)			# near
s2 = DHT22.sensor(pi, 17)		# outside
s3 = DHT22.sensor(pi, 18)		# living room

window_pin = 23
pi.set_mode (window_pin, pigpio.INPUT)
pi.set_pull_up_down (window_pin, pigpio.PUD_UP)

window_status = pi.read(window_pin)

room_temp = []
room_humidity = []
out_temp = []
out_humidity = []
living_room_temp = []
living_room_humidity = []

for i in range(5) :
  time.sleep (1)
  s.trigger()
  time.sleep (2)
  s2.trigger()
  time.sleep (2)
  s3.trigger ()
  time.sleep (2)
  room_temp.append(((s.temperature()*9.0)/5.0)+32)
  out_temp.append(((s2.temperature()*9.0)/5.0)+32)
  living_room_temp.append(((s3.temperature()*9.0)/5.0)+32)
  room_humidity.append(s.humidity())
  out_humidity.append(s2.humidity())
  living_room_humidity.append(s3.humidity())

current = {"_id" : datetime.datetime.now(),
           "room" : {"temp" : average(room_temp),
                     "humidity" : average(room_humidity),
		     "window" : window_status},
           "outside" : {"temp" : average(out_temp),
                        "humidity" : average(out_humidity)},
	   "living_room" : {"temp" : average(living_room_temp),
                            "humidity" : average(living_room_temp)}}

temps.insert(current)

# print (window_status)

"""
   new window shutters - wire not attached

if window_status == 1 :
  print ("Window open")
  if average(out_temp)  >  average(room_temp) :
     os.system ('mplayer police_s.wav')
     os.system ('/usr/bin/espeak -s 155 -a 200 "Close window please"')
  if check_last_30_minutes (average(out_temp), average(room_temp)) == 'close' :
     os.system ('mplayer police_s.wav')
     os.system ('/usr/bin/espeak -s 155 -a 200 "Temperature is rising. Close window please"')
else :
  print ("Window closed")
  if average(room_temp) > 55.0 :
    if average(room_temp) > average(out_temp) :
      if check_last_30_minutes (average(out_temp), average(room_temp)) == 'open' :
        os.system ('mplayer police_s.wav')
        os.system ('/usr/bin/espeak -s 155 -a 200 "Open window please"')
"""

plot_day (datetime.datetime.now())
# plot_day (datetime.datetime.now(), 'N')

plot_month (datetime.datetime.now())

html = open ('/home/pi/templates/index.html', 'w')
   
html.write('<html>')
html.write('\n')
html.write('<body>')
html.write('\n')
html.write('<h1>Current Temperatures</h1>')
html.write('\n') 
now = datetime.datetime.now()
line = '<h2>' + str(now)[0:16] + '</h2>'
html.write(line)
html.write('\n')
html.write('<pre>')
html.write('\n')
line='Computer Room Temp={0:0.1f}{2}F  Humidity={1:0.1f}%'.format((average(room_temp)), average(room_humidity), degree)
html.write(line.encode("UTF-8"))
html.write('\n')
html.write('<p>')
line='    Outside   Temp={0:0.1f}{2}F  Humidity={1:0.1f}%'.format((average(out_temp)), average(out_humidity), degree)
html.write(line.encode("UTF-8"))
html.write('\n')
html.write('<p>')
line='Living Room   Temp={0:0.1f}{2}F  Humidity={1:0.1f}%'.format((average(living_room_temp)), average(living_room_humidity), degree)
html.write(line.encode("UTF-8"))
html.write('\n')
html.write('</pre>')
html.write('\n')
html.write('<img src="{{url_for(\'static\', filename=\'hourly.png\')}}"/>')
html.write('\n')
html.write('<img src="{{url_for(\'static\', filename=\'monthly.png\')}}"/>')
html.write('\n')
# html.write('<img src="{{url_for(\'static\', filename=\'daily.png\')}}"/>')
# html.write('\n')
to_do = check_last_30_minutes (average(out_temp), average(room_temp))
if average(room_temp) <= average(out_temp) :
    to_do = 'close'
html.write('<h2>' + to_do + '<h2>')
html.write('\n')
html.write('</body>')
html.write('\n')
html.write('</html>')
html.write('\n')

html.close()

print current["_id"]
print 'Computer Room Temp={0:0.1f}{1}F  Humidity={2:0.1f}%'.format((average(room_temp)), degree, average(room_humidity))
print '    Outside   Temp={0:0.1f}{1}F  Humidity={2:0.1f}%'.format((average(out_temp)), degree, average(out_humidity))
print 'Living Room   Temp={0:0.1f}{1}F  Humidity={2:0.1f}%'.format((average(living_room_temp)), degree, average(living_room_humidity))
s.cancel()
s2.cancel()
s3.cancel()




