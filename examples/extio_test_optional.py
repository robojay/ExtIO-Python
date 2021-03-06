import sys
from extio import *
import time

"""
Simple example to test the function of the ExtIO driver

This code includes tests for optional functions that may not
be available on all radios

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

time.sleep(2)

extIO.SetHWLO(frequency + 1)

""" this is one way to tell if a DLL supports a function """
try:
	extIO.foo()
except AttributeError:
	print('foo() not supported ;-)')

print(extIO.ExtIoGetSrates())

print(extIO.ExtIoGetSrates(idx = 0))

sRateIndex = extIO.ExtIoGetActualSrateIdx()
print(sRateIndex)

print(extIO.ExtIoSetSrate(sRateIndex))

settingsArray = extIO.ExtIoGetSetting()
""" this is one way to go through the indices, there are better Pythonic ways if you know the setting you want """
for index in range(0, len(settingsArray)):
	print('Index [' + str(index) + '] ' + settingsArray[index]['description'] + ' = ' + settingsArray[index]['value'])

print(extIO.ExtIoGetSetting(0))

time.sleep(2)

extIO.StopHW()
extIO.CloseHW()

print('callbackInfo = ' + str(callbackInfo))
print('callbackData = ' + str(callbackData))
