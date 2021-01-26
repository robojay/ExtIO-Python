"""
ExtIO-Python performance testing

Requires numpy https://numpy.org/
"""

import sys
import os
import time
from ctypes import *
import threading
import queue
from datetime import datetime
import struct

import numpy as np
import matplotlib.pyplot as plt

from extio import *
import iqStream

class consumerThread (threading.Thread):
	""" Record IQ data from the queue into a file """
	""" TODO: Mechanism to handle sample rate/format changes mid stream """
	global iqStream

	def __init__(self):
		threading.Thread.__init__(self)
		self.stop = False

	def run(self):

		while not(self.stop):
			while (iqStream.tail != iqStream.head):
				tempBuffer = np.copy(iqStream.buffer[iqStream.tail])
				newTail = iqStream.tail + 1
				if (newTail >= iqStream.queueEntries):
					newTail = 0
				iqStream.tail = newTail
			time.sleep(0.05)


def extIoCallback(cnt, status, IQoffs, IQdata):
	""" main function wrapper for the IQ Stream callback method """
	global iqStream
	global timeStamp
	global stampCount
	global stampMark
	global callbackTime
	global deltaTimeMisses

	t1 = time.perf_counter()
	iqStream.iqStreamCallback(cnt, status, IQoffs, IQdata)
	if iqStream.enabled:
		if (cnt > 0):
			t2 = time.perf_counter()
			timeStamp.append(t2)
			dT = t2 - t1
			callbackTime.append(dT)
			# miss counts are recorded in iqStream

def perfCallback(cnt, status, IQoffs, IQdata):
	""" main function wrapper for the IQ Stream callback method """
	global iqStream
	global timeStamp
	global stampCount
	global stampMark
	global callbackTime
	global deltaTimeMisses

	t1 = time.perf_counter()
	if iqStream.enabled:
		if (cnt > 0):
			t2 = time.perf_counter()
			timeStamp.append(t2)
			dT = t2 - t1
			callbackTime.append(dT)
			if dT > deltaTimeExpected:
				deltaTimeMisses += 1

"""
	Globals
"""

extIO = None
timeStamp = []
hwTypesSupported = [ExtIO.ExtHWtype.USBdata16]
useConsumer = False
callbackTime = []
deltaTimeMisses = 0


"""
	Main
"""

if (len(sys.argv) == 6):
	extIO = ExtIO(sys.argv[1])
	frequency = int(sys.argv[2])
	duration = float(sys.argv[3])	
	if sys.argv[4] == 'c':
		useConsumer = True
	else:
		useConsumer = False
	sampleRateIndex = int(sys.argv[5])

else:
	print('usage: python perfTest.py <ExtIO DLL> <Frequency in Hertz> <Duration in Seconds> <p or c> <sample rate index>')
	exit()

# TODO: Support non-default sample rates

extIO.InitHW()

print('name: ' + extIO.name)
print('model: ' + extIO.model)
print('hwtype: ' + str(extIO.hwtype))

# Verify supported hardware type
if extIO.hwtype not in hwTypesSupported:
	print('[main] Unsupported Hardware Type') 
	exit()

iqStream.init(_extIO = extIO, _typesSupported = hwTypesSupported, _queueEntries = 2048)

if useConsumer:
	extIO.SetCallback(extIoCallback)
else:
	extIO.SetCallback(perfCallback)

extIO.OpenHW()

# Set the stream format and sample rate
# note: some radios allow these to change while streaming
# the handler would be notified
iqStream.type = extIO.hwtype
extIO.ExtIoSetSrate(sampleRateIndex)
iqStream.sampleRate = extIO.ExtIoGetSrates(extIO.ExtIoGetActualSrateIdx())

print('Sample Rate: ' + str(iqStream.sampleRate))

if useConsumer:
	print('Using consumer callback')
	consumer = consumerThread()
	consumer.start()
else:
	print('Using performance callback')

extIO.StartHW(frequency)

iqStream.initBuffers()

deltaTimeExpected = (extIO.iqPairs)/ iqStream.sampleRate  
deltaTimeExpectedUs = (extIO.iqPairs * 1e6)/ iqStream.sampleRate  
print('Delta Time Expected (us) = ' + str(deltaTimeExpectedUs))

iqStream.enabled = True

print('Testing...')
time.sleep(duration)
print('done.')

iqStream.enabled = False

extIO.StopHW()

if useConsumer:
	consumer.stop = True
	consumer.join()
	print('Callback Hits = ' + str(iqStream.callbackHits))
	print('Callback Info = ' + str(iqStream.callbackInfo))
	print('Callback Data = ' + str(iqStream.callbackData))
	print('IQ Pairs per Callback = ' + str(extIO.iqPairs))
	print('Total IQ Pairs = ' + str(extIO.iqPairs * iqStream.callbackData))
	print('Samples for second = ' + str((extIO.iqPairs * iqStream.callbackData) / duration))
	print('Overruns = ' + str(iqStream.overruns))
	print('Delta Time Misses = ' + str(iqStream.callbackMisses))
else:
	print('Delta Time Misses = ' + str(deltaTimeMisses))

extIO.CloseHW()

deltaTime = []
for i in range(1, len(timeStamp)):
	deltaTime.append(timeStamp[i] - timeStamp[i-1])

"""
print('deltaTime = [', end='')
for t in deltaTime[:len(deltaTime)-1]:
	print(f'{t},', end = '')
print(f'{deltaTime[-1]}]')

print()
"""

fig = 0

figure, ax = plt.subplots(3)
ax[0].set_title('Figure ' + str(fig) + ': Time Stamps (s)')
fig += 1
ax[0].plot(timeStamp,'.-')

dT = np.array(deltaTime) * 1.0e6 # microseconds
ax[1].set_title('Figure ' + str(fig) + ': Delta Times (us)')
fig += 1
ax[1].plot(dT,'.-')

cT = np.array(callbackTime) * 1.0e6  # change to microsecond display
ax[2].set_title('Figure ' + str(fig) + ': Callback Execution Times (us)')
fig += 1
ax[2].plot(cT,'.-')
ax[2].plot(np.full((len(cT),),deltaTimeExpectedUs), 'k-', lw=1,dashes=[2, 2])
ax[2].set_ylim(top = 2 * deltaTimeExpectedUs, bottom = 0)
plt.show()
