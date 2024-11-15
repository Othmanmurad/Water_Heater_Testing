from datetime import datetime
from numpy.random import normal
from numpy import zeros, savetxt, loadtxt
import random
import RPi.GPIO as GPIO
from time import time, sleep
from threading import Thread
import os
import csv
#Initialize GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
FMPIN = 6    #flow meter GPIO pin
VPIN = 17    #valve GPIO pin
GPIO.setup(FMPIN, GPIO.IN, GPIO.PUD_UP) #setup flow meter pin as input
GPIO.setup(VPIN, GPIO.OUT, initial=GPIO.LOW)    #setup valve pin as output
GPIO.add_event_detect(FMPIN, GPIO.RISING)   #add rising edge detection

#Define function to draw water
def draw_water(targetVol):
    if targetVol <= 0:
        return (0, 0)  # Return volume and duration as 0 if target is invalid
    
    print('Drawing %.2f gallon(s).' % targetVol)
    volume = 0
    numPulses = 0
    start_time = time()  # Record start time
    
    GPIO.output(VPIN, GPIO.HIGH)    #open valve
    while volume < targetVol:  #keep valve open until desired volume has passed
        if GPIO.event_detected(FMPIN):
            numPulses += 1    #Count pulses from flow meter
            volume = float(numPulses) / 476    #Calculate volume
        
        current_time = time()
        elapsed_time = current_time - start_time
        if elapsed_time > 180:
            print('Timeout Error.')
            break
    
    GPIO.output(VPIN, GPIO.LOW) #close valve
    end_time = time()  # Record end time
    duration = round(end_time - start_time, 2)  # Calculate duration in seconds
    
    print('Volume drawn: %.2f gallon(s).' % volume)
    print('Draw duration: %.2f seconds.' % duration)
    
    return (volume, duration)  # Return both volume and duration

# Create a queue to store the results from the thread
from queue import Queue
result_queue = Queue()

# Modified thread function to store results
def draw_water_with_queue(targetVol, queue):
    result = draw_water(targetVol)
    queue.put(result)

thread_draw = Thread(target=draw_water_with_queue, args=[0, result_queue])

# Read schedule from gen4.csv
times = []
volumes = []
with open('12H-WDP.csv', 'r') as file:
    read = csv.reader(file)
    for row in read:
        times.append(row[0])
        volumes.append(row[1])

#Enter main program loop
while True:
    now = datetime.now()    #Update date/time
    filename = 'WH_Data_' + str(now.month) + '-' + str(now.day) + '-' + str(now.year) + '.csv'
    
    # Create new file with header if it doesn't exist
    if not os.path.isfile(filename):
        with open(filename, 'w') as data:
            data.write('Time,Draw Amount,Draw Duration\n')
    
    #Draw water if there is an event at this minute
    timestr = datetime.strftime(now, "%H:%M:%S")
    drawVolume = 0
    for i in range(0, len(times)):
        if times[i] == timestr:
            drawVolume = float(volumes[i])
            
    if drawVolume != 0:
        if thread_draw.is_alive():
            print('Debugging: Previous draw is still running. Waiting for draw to finish.\n')
            thread_draw.join()
            if not result_queue.empty():
                thread_result = result_queue.get()
        
        # Start new thread with queue
        result_queue = Queue()  # Reset queue for new thread
        thread_draw = Thread(target=draw_water_with_queue, args=[drawVolume, result_queue])
        thread_draw.start()
        
        # Wait for the draw to complete to get accurate duration
        thread_draw.join()
        actual_volume, duration = result_queue.get()
        
        # Log the event with duration - simplified direct write
        try:
            with open(filename, 'a') as data:
                data.write(f"{timestr},{actual_volume:.2f},{duration:.2f}\n")
            print(f"Logged: Time={timestr}, Volume={actual_volume:.2f}, Duration={duration:.2f}")
        except IOError as e:
            print(f"Error logging data: {e}")
    
    sleep(1)

