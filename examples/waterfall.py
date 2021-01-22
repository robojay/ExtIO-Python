#!/usr/bin/env python

"""
Adapted from pysdr.org and David Cherkus
"""

import sys
import matplotlib.pyplot as plt
import threading
import queue

import numpy as np
from extio import *

def extIoCallback(cnt, status, IQoffs, IQdata):
	""" main function wrapper for the IQ Stream callback method """
	global iqStream
	iqStream.iqStreamCallback(cnt, status, IQoffs, IQdata)


"""
	Globals
"""

hwTypesSupported = [ExtIO.ExtHWtype.USBdata16]
iqStream = None
extIO = None

"""
	Main
"""

if (len(sys.argv) == 3):
	extIO = ExtIO(sys.argv[1])
	frequency = int(sys.argv[2])
else:
	print('usage: python waterfall.py <ExtIO DLL> <Frequency in Hertz>')
	exit()

# TODO: Support non-default sample rates

extIO.InitHW()

# Verify supported hardware type
if extIO.hwtype not in hwTypesSupported:
	print('[main] Unsupported Hardware Type') 
	exit()

iqStream = IqStream(extIO = extIO, typesSupported = hwTypesSupported)

extIO.SetCallback(extIoCallback)
extIO.OpenHW()

# Set the stream format and sample rate
# note: some radios allow these to change while streaming
# the handler would be notified
iqStream.type = extIO.hwtype
iqStream.sampleRate = extIO.ExtIoGetSrates(extIO.ExtIoGetActualSrateIdx())

sample_rate = int(iqStream.sampleRate)
center_freq = int(frequency)
fft_size = 1024

extIO.StartHW(frequency)

num_samps = round(1E6 / extIO.iqPairs) * extIO.iqPairs
sampleBuffer = np.empty(2 * num_samps, np.int16)
sampleIndex = 0

while sampleIndex < len(sampleBuffer):
	gotData = False
	try:
		tempBuffer = iqStream.queue.get(block = True, timeout = 1)
		gotData = True
	except queue.Empty:
		pass

	if gotData:
		sampleBuffer[sampleIndex:sampleIndex + len(tempBuffer)] = tempBuffer
		sampleIndex += len(tempBuffer)

extIO.StopHW()
extIO.CloseHW()

# reformat as an I,Q array
iqArray = np.reshape(sampleBuffer, (int(sampleBuffer.size / 2), 2))

# view it as signed 16 bit integers
iqSigned = iqArray.view(np.int16)

# convert to complex
# dot product give us complex float I Q values
# scaled by 32767
#complexArray = np.array([1.0 / 32767.0 + 0.0j, 0.0 + 1.0j / 32767.0])
complexArray = np.array([1.0 + 0.0j, 0.0 + 1.0j])
iqComplex = iqSigned.dot(complexArray)

# Create Waterfall matrix
num_slices = int(np.floor(num_samps/fft_size))  # 1M/1024 = 976
waterfall = np.zeros((num_slices, fft_size))

np.seterr(all='raise')

for i in range(num_slices):
	try:
		waterfall[i,:] = np.log10(np.fft.fftshift(np.abs(np.fft.fft(iqComplex[i*fft_size:(i+1)*fft_size]))**2))
	except FloatingPointError:
		print('divide by zero error at ' + str(i))
		print(iqComplex[i*fft_size:(i+1)*fft_size])
		print()

# Plot waterfall
time_per_row = 1.0/sample_rate * fft_size
fmin = (center_freq - sample_rate/2.0)/1e6 # MHz
fmax = (center_freq + sample_rate/2.0)/1e6 # MHz
plt.imshow(waterfall, extent=[fmin, fmax, time_per_row*num_slices, 0], aspect='auto', cmap=plt.get_cmap('jet'))
plt.xlabel('Frequency [MHz]')
plt.ylabel('Time [seconds]')
plt.show()
