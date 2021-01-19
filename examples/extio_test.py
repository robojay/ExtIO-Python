import sys
from extio import *
import time

"""
Simple example to test the function of the ExtIO driver

Some drivers may require additional DLLs, which can make
debugging DLL paths difficult.
"""

def exampleCallback(cnt, status, IQoffs, IQdata):
	""" (int cnt, int status, float IQoffs, void *IQdata)
	Example callback function
	Increments a counter when called with data (cnt > 0)
	Prints information when called with driver info (cnt = -1)
	"""
	global callbackInfo
	global callbackData

	if cnt > 0:
		# we have data
		callbackData += 1

	elif cnt == -1:
		#we have driver info
		callbackInfo += 1
		print('[Callback] ', end = '')
		print(cnt, end = '')
		print(' ', end = '')
		print(status, end = '')
		print(' ', end = '')
		print(IQoffs, end = '')
		print(' ', end = '')
		print(IQdata)

"""
Main
"""

if (len(sys.argv) != 3):
	print('usage: python extio_test.py <ExtIO DLL> <Frequency in Hertz>')
	exit()

callbackInfo = 0
callbackData = 0

extIO = ExtIO(sys.argv[1])
frequency = int(sys.argv[2])

# this call will return name, model, hwtype
# or they can be accessed via the object
extIO.InitHW()

print('name: ' + extIO.name)
print('model: ' + extIO.model)
print('hwtype: ' + str(extIO.hwtype))

extIO.SetCallback(exampleCallback)

print('Open: ' + str(extIO.OpenHW()))
print('Start: ' + str(extIO.StartHW(frequency)))

time.sleep(5)

extIO.StopHW()
extIO.CloseHW()

print('callbackInfo = ' + str(callbackInfo))
print('callbackData = ' + str(callbackData))
