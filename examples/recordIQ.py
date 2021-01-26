"""
Example use of ExtIO-Python to record IQ data as a WAV file

Uses mandatory ExtIO DLL calls, and requires support of the optional
ExtIoSetSrate, ExtIoGetSrates, and ExtIoGetActualSrateIdx calls

Works with a limited set of harware types

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
from extio import *
import iqStream

class waveHeader():
	def __init__(self):
		self.ckID = b'RIFF'
		self.ckSize = 0
		self.formType = b'WAVE'
		self.fmtHeader = b'fmt '
		self.fmtChunkSize = 16
		self.fmtFormatType = 1
		self.fmtChannels = 2
		self.fmtSampleRate = 0
		self.fmtBytesPerSecond = 0
		self.fmtBlockAlignment = 0
		self.fmtBitsPerSample = 0
		self.dataHeader = b'data'
		self.dataSize = 0

	def to_bytes(self):
		format = '<4sI4s4sIHHIIHH4sI'
		buf = struct.pack(format,
		self.ckID,
		self.ckSize,
		self.formType,
		self.fmtHeader,
		self.fmtChunkSize,
		self.fmtFormatType,
		self.fmtChannels,
		self.fmtSampleRate,
		self.fmtBytesPerSecond,
		self.fmtBlockAlignment,
		self.fmtBitsPerSample,
		self.dataHeader,
		self.dataSize)
		return buf


class recorderThread (threading.Thread):
	""" Record IQ data from the queue into a file """
	""" TODO: Mechanism to handle sample rate/format changes mid stream """
	global iqStream

	def __init__(self, fileHandle):
		threading.Thread.__init__(self)
		self.stop = False
		self.fileHandle = fileHandle

	def run(self):

		while not(self.stop):
			while (iqStream.tail != iqStream.head):
				tempBuffer = np.copy(iqStream.buffer[iqStream.tail])
				newTail = iqStream.tail + 1
				if (newTail >= iqStream.queueEntries):
					newTail = 0
				iqStream.tail = newTail
				self.fileHandle.write(tempBuffer.tobytes())
			time.sleep(0.05)

"""
	Globals
"""

hwTypesSupported = [ExtIO.ExtHWtype.USBdata16]
extIO = None

"""
	Main
"""

if (len(sys.argv) == 6):
	extIO = ExtIO(sys.argv[1])
	sampleRateIndex = int(sys.argv[2])
	frequency = int(sys.argv[3])
	duration = float(sys.argv[4])	
	filePath = sys.argv[5]
	fileName = filePath + os.path.sep + 'IQ_'
	fileName += datetime.utcnow().strftime('%Y%m%d_%H%M%SZ')
	fileName += '_' + str(frequency) + 'Hz.wav'

else:
	print('usage: python recordIQ.py <ExtIO DLL> <Sample Rate Index> <Frequency in Hertz> <Duration in Seconds> <Path for Record File>')
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

extIO.SetCallback(iqStream.iqStreamCallback)
extIO.OpenHW()

# Set the stream format and sample rate
# note: some radios allow these to change while streaming
# the handler would be notified
iqStream.type = extIO.hwtype
extIO.ExtIoSetSrate(sampleRateIndex)
iqStream.sampleRate = extIO.ExtIoGetSrates(extIO.ExtIoGetActualSrateIdx())

# create a default header
# will fill in details after capture
fileHeader = waveHeader()
wavFile = open(fileName, 'wb')
wavFile.write(fileHeader.to_bytes())

recorder = recorderThread(wavFile)
recorder.start()

extIO.StartHW(frequency)

iqStream.initBuffers()

iqStream.enabled = True

print('Recording...')
time.sleep(duration)
print('done.')

iqStream.enabled = False

extIO.StopHW()

recorder.stop = True
recorder.join()

extIO.CloseHW()

# close file
wavFile.close()

print('Callback Hits = ' + str(iqStream.callbackHits))
print('Callback Info = ' + str(iqStream.callbackInfo))
print('Callback Data = ' + str(iqStream.callbackData))
print('IQ Pairs per Callback = ' + str(extIO.iqPairs))
print('Total IQ Pairs = ' + str(extIO.iqPairs * iqStream.callbackData))
print('Samples for second = ' + str((extIO.iqPairs * iqStream.callbackData) / duration))
print('Overruns = ' + str(iqStream.overruns))
print('Delta Time Misses = ' + str(iqStream.callbackMisses))

# update file header information
	
# TODO: handle multiple IQ formats...

# fill in the values we need
fileSize = os.stat(fileName).st_size
fileHeader.ckSize = fileSize - 8
fileHeader.fmtSampleRate = int(iqStream.sampleRate)
fileHeader.dataSize = fileSize - len(fileHeader.to_bytes())

if iqStream.type == ExtIO.ExtHWtype.USBdataU8:
	fileHeader.fmtBlockAlignment = 2
	fileHeader.fmtBitsPerSample = 8

elif iqStream.type == ExtIO.ExtHWtype.USBdata16:
	fileHeader.fmtBlockAlignment = 4
	fileHeader.fmtBitsPerSample = 16

elif iqStream.type == ExtIO.ExtHWtype.USBdata24:
	# TODO - check for WAV support	
	pass

elif iqStream.type == ExtIO.ExtHWtype.USBdata32:
	fileHeader.fmtBlockAlignment = 8
	fileHeader.fmtBitsPerSample = 32

elif iqStream.type == ExtIO.ExtHWtype.USBfloat32:
	# TODO - check for WAV support
	pass

fileHeader.fmtBytesPerSecond = int(iqStream.sampleRate) * fileHeader.fmtBitsPerSample

# rewrite the header
wavFile = open(fileName, 'rb+')
wavFile.write(fileHeader.to_bytes())
wavFile.close()
