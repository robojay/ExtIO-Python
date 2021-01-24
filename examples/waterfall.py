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

iqStream = IqStream(extIO = extIO, typesSupported = hwTypesSupported, queueEntries = 256)

extIO.SetCallback(extIoCallback)
extIO.OpenHW()

# Set the stream format and sample rate
# note: some radios allow these to change while streaming
# the handler would be notified
#extIO.ExtIoSetSrate(6)
iqStream.type = extIO.hwtype
iqStream.sampleRate = extIO.ExtIoGetSrates(extIO.ExtIoGetActualSrateIdx())

sample_rate = int(iqStream.sampleRate)
center_freq = int(frequency)
fft_size = 512 # 1024

extIO.StartHW(frequency)

num_samps = round(1e6 / extIO.iqPairs) * extIO.iqPairs
sampleBuffer = np.empty(2 * num_samps, np.int16)
sampleIndex = 0

iqStream.enabled = True

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

iqStream.enabled = False

extIO.StopHW()
extIO.CloseHW()

print('Callback Data Hits = ' + str(iqStream.callbackData))
print('Overruns = ' + str(iqStream.overruns))

# view it as signed 16 bit integers
iqSigned = sampleBuffer.view(np.int16)

# reformat as an I,Q array
iqArray = np.reshape(iqSigned, (int(iqSigned.size / 2), 2))

# convert to complex
# dot product give us complex float I Q values
# scaled by 32767
complexArray = np.array([1.0 / 32767.0 + 0.0j, 0.0 + 1.0j / 32767.0], dtype = np.complex128)
#complexArray = np.array([1.0 + 0.0j, 0.0 + 1.0j], dtype = np.complex128)
iqComplex = iqArray.dot(complexArray)

# Create Waterfall matrix
num_slices = int(np.floor(num_samps/fft_size))  # 1M/1024 = 976
waterfall = np.zeros((num_slices, fft_size))

# Waterfall parameters
time_per_row = 1.0/sample_rate * fft_size
fmin = (center_freq - sample_rate/2.0)/1e6 # MHz
fmax = (center_freq + sample_rate/2.0)/1e6 # MHz
f = np.arange(fmin,fmax,(fmax - fmin)/fft_size)

np.seterr(all='raise')

fig = 1

for i in range(num_slices):

	data = iqComplex[i*fft_size:(i+1)*fft_size]

	if False:
		data = data * np.hamming(fft_size)
		offset = 0.0
		threshold = -10
	else:
		offset = 1e-20
		threshold = -20

	S = np.fft.fftshift(np.fft.fft(data))
	waterfall[i,:] = np.log10(np.fft.fftshift(np.abs(np.fft.fft(data))**2) + offset)

	if True:
		""" debug code """
		# if (i == 0) or (len(np.where(waterfall <= threshold)[0]) != 0):
		if (len(np.where(waterfall[i] <= threshold)[0]) != 0):
			"""
			print(f'*** {i} ***')

			print('[', end = '')
			for z in iqArray[i*fft_size:(i+1)*fft_size-1]:
				print(f'[{z[0]},{z[1]}],', end = '')
			print(f'[{iqArray[(i+1)*fft_size-1][0]},{iqArray[(i+1)*fft_size-1][1]}]]')
			print()

			print('[', end = '')
			for z in iqComplex[i*fft_size:(i+1)*fft_size-1]:
				print(f'{z},', end = '')
			print(f'{iqComplex[(i+1)*fft_size-1]}]')

			print()

			print('[', end = '')
			for z in waterfall[i][:-1]:
				print(f'{z},', end = '')
			print(f'{waterfall[i][-1]}]')

			print()
			"""

			figure, ax = plt.subplots(2)

			D_Real = np.real(data)
			D_Imag = np.imag(data)

			ax[0].set_title('Figure ' + str(fig) + ': I')
			fig += 1
			ax[0].plot(D_Real,'.')

			ax[1].set_title('Figure ' + str(fig) + ': Q')
			fig += 1
			ax[1].plot(D_Imag,'.')


			"""
			S_mag = np.abs(S)
			S_phase = np.angle(S)

			ax[2].set_title('Figure ' + str(fig) + ': FFT Magnitude')
			fig += 1
			ax[2].plot(f, S_mag,'.')

			ax[3].set_title('Figure ' + str(fig) + ': FFT Phase')
			fig += 1
			ax[3].plot(f, S_phase,'.')

			ax[4].set_title('Figure ' + str(fig) + ': FFT Power')
			fig += 1
			ax[4].plot(f,waterfall[i],'.')

			"""

			if (len(np.where(waterfall[i] <= threshold)[0]) != 0):
				print(f'Anomaly at slice {i}')
				if (i > 0):
					plt.figure('Figure ' + str(fig) + ': Waterfall')
					fig += 1
					plt.imshow(waterfall[:i], extent=[fmin, fmax, time_per_row*i, 0], aspect='auto', cmap=plt.get_cmap('jet'))
					plt.xlabel('Frequency [MHz]')
					plt.ylabel('Time [seconds]')

				plt.show()
				exit()

# Plot waterfall
plt.figure('Figure ' + str(fig) + ': Waterfall')
fig += 1
plt.imshow(waterfall, extent=[fmin, fmax, time_per_row*num_slices, 0], aspect='auto', cmap=plt.get_cmap('jet'))
plt.xlabel('Frequency [MHz]')
plt.ylabel('Time [seconds]')
plt.show()
