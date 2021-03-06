import sqlite3
import serial
import time
from datetime import datetime
from subprocess import Popen
SERIAL_PORT = 'fa131'
TEMP_THRESH_HI = 90.
TEMP_THRESH_LO = 70.
HUMIDITY_THRESH = 80.

def setupDB():
    conn = sqlite3.connect('worms.db')
    c = conn.cursor()
    c.execute('''create table worms (id int, time text, temp float, 
        humidity float, motion integer, image text)''')
    c.execute('''create table alerts (id int, time text, alerttext text,
        active integer, explain text)''')
    conn.commit()
    conn.close()

def readArduino():
    ser = serial.Serial(port='/dev/tty.usbmodem' + SERIAL_PORT, baudrate=9600)
    print "arduino opened"
    attempts = 0
    while(True):
        try:
            line = ser.readline()
            attempts += 1
            print line
            if len(map(float, line.split(','))) == 2:
                break
        except Exception, e:
            pass
        if attempts >= 20:
            raise Exception("Cannot find Arduino. Is it connected?")
    print "saving last line to DB"
    # first get the current time stamp
    curtime = datetime.now()
    timestamp = curtime.strftime("%Y-%m-%d_%H:%M:%S")

    # so far we only have temp and humidity sensors
    [temp,humidity] = line.split(',')
    temp = float(temp)
    humidity = float(humidity)
    # add other sensors here
    motion = 0
    image = ''

    return [timestamp, temp, humidity, motion, image]

def insertintoDB(data):
    conn = sqlite3.connect('worms.db')
    c = conn.cursor()
    # get the last entry id and increment it
    c.execute("select max(id) from worms")
    try:
        index = c.fetchone()[0] + 1
    except Exception, e:
        index = 1
    # this is the actual data
    [timestamp, temp, humidity, motion, image] = data
    c.execute("insert into worms values (?,?,?,?,?,?)",
        (index, timestamp, temp, humidity, motion, image))
    conn.commit()
    conn.close()

def checkforAlerts(data):
    [timestamp, temp, humidity, motion, image] = data

    conn = sqlite3.connect('worms.db')
    c = conn.cursor()
    c.execute("select max(id) from alerts")
    try:
        index = c.fetchone()[0] + 1
    except Exception, e:
        index = 1

    if temp > TEMP_THRESH_HI or temp < TEMP_THRESH_LO:
        alerttext = "Check temperature"
        color = 1
        if temp > TEMP_THRESH_HI:
            explaintext = "Temperature rose to %dF" % temp
        else:
            explaintext = "Temperature dropped to %dF" % temp
        sendalert(alerttext)
        c.execute("insert into alerts values (?,?,?,?,?)",
            (index, timestamp, alerttext, color, explaintext))
        index += 1
    if humidity < HUMIDITY_THRESH:
        alerttext = "Check humidity"
        color = 2
        #alerttext = ""
        explaintext = "Humidity dropped to %d%%" % humidity
        sendalert(alerttext)
        c.execute("insert into alerts values (?,?,?,?,?)",
            (index, timestamp, alerttext, color, explaintext))

    conn.commit()
    conn.close()          

def sendalert(alerttext):
    Popen(["./send_sms.sh", alerttext])
    Popen(["./send_to_glass.sh", alerttext])
    pass



if __name__ == "__main__":
    while(1):
        data = readArduino()
        insertintoDB(data)
        time.sleep(2)
