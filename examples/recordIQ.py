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

class IqStream():
	""" Class to handle the IQ streaming data """
	def __init__(self, queueEntries = 64):
		self.callbackHits = 0
		self.callbackInfo = 0
		self.callbackData = 0
		self.overruns = 0
		self.queue = queue.Queue(queueEntries)
		self.type = None
		self.sampleRate = None

def extIoCallback(cnt, status, IQoffs, IQdata):
	#  (int cnt, int status, float IQoffs, void *IQdata);
	global iqStream
	global extIO

	iqStream.callbackHits += 1

	if cnt > 0:
		# we have data
		iqStream.callbackData += 1
		if iqStream.type == ExtIO.ExtHWtype.USBdata16:
			# INT16
			tempBuf = cast(IQdata, POINTER(c_int))			
			tempArray = np.ctypeslib.as_array(tempBuf, shape=(2 * int(cnt/sizeof(c_int)),))
			try:
				iqStream.queue.put_nowait(tempArray)
			except queue.Full:
				iqStream.overruns += 1

		#do this later...elif iqStream.type == ...:
			# INT24, etc.

		else:
			print('[Callback] No valid iqFormat set (' + str(iqFormat) + ')')
			# should handle this better... but for now
			exit()

	elif cnt == -1:
		# we have driver info
		iqStream.callbackInfo += 1

		# TODO: changing sample rate and/or format mid recording should cause some 
		# kind of event to stop the recorder, save the file, and reopen a new file for
		# new data
		# one possibility is to insert this type of state change into the queue

		if status == ExtIO.ExtHWstatus.Changed_SampleRate:
			iqStream.sampleRate = extIO.ExtIoGetSrates(extIO.ExtIoGetActualSrateIdx())		

		elif status == ExtIO.ExtHWstatus.SampleFmt_IQ_UINT8:
			iqStream.type = ExtIO.ExtHWtype.USBdataU8

		elif status == ExtIO.ExtHWstatus.SampleFmt_IQ_INT16:
			iqStream.type = ExtIO.ExtHWtype.USBdata16 

		elif status == ExtIO.ExtHWstatus.SampleFmt_IQ_INT24:
			iqStream.type = ExtIO.ExtHWtype.USBdata24 

		elif status == ExtIO.ExtHWstatus.SampleFmt_IQ_INT32:
			iqStream.type = ExtIO.ExtHWtype.USBdata32 

		elif status == ExtIO.ExtHWstatus.SampleFmt_IQ_FLT32:
			iqStream.type = ExtIO.ExtHWtype.USBfloat32 

		if iqStream.type not in hwTypesSupported:
			# should handle this better... but for now
			print('[Callback] Unsupported Hardware Type') 
			exit()

	debugCallbackData = False
	debugCallbackInfo = False

	# this is really slow, and if enabled (especially for data)
	# may cause data loss
	if (debugCallbackData) or (debugCallbackInfo and cnt < 0):	
		print('[Callback] ', end = '')
		print(cnt, end = '')
		print(' ', end = '')
		print(status, end = '')
		print(' ', end = '')
		print(IQoffs, end = '')
		print(' ', end = '')
		print(IQdata)


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

	def __init__(self, iqStream, fileHandle):
		threading.Thread.__init__(self)
		self.stop = False
		self.iqStream = iqStream
		self.fileHandle = fileHandle

	def run(self):

		while not(self.stop):
			gotData = False
			try:
				tempBuffer = self.iqStream.queue.get(block = True, timeout = 1)
				gotData = True
			except queue.Empty:
				pass

			if gotData:
				self.fileHandle.write(tempBuffer.tobytes())

"""
	Globals
"""

iqStream = IqStream()
extIO = None
hwTypesSupported = [ExtIO.ExtHWtype.USBdata16]

"""
	Main
"""

if (len(sys.argv) == 5):
	extIO = ExtIO(sys.argv[1])
	frequency = int(sys.argv[2])
	duration = float(sys.argv[3])	
	filePath = sys.argv[4]
	fileName = filePath + os.path.sep + 'IQ_'
	fileName += datetime.utcnow().strftime('%Y%m%d_%H%M%SZ')
	fileName += '_' + str(frequency) + 'Hz.wav'

else:
	print('usage: python recordIQ.py <ExtIO DLL> <Frequency in Hertz> <Duration in Seconds> <Path for Record File>')
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

extIO.SetCallback(extIoCallback)
extIO.OpenHW()

# Set the stream format and sample rate
# note: some radios allow these to change while streaming
# the handler would be notified
iqStream.type = extIO.hwtype
iqStream.sampleRate = extIO.ExtIoGetSrates(extIO.ExtIoGetActualSrateIdx())

# create a default header
# will fill in details after capture
fileHeader = waveHeader()
wavFile = open(fileName, 'wb')
wavFile.write(fileHeader.to_bytes())

recorder = recorderThread(iqStream, wavFile)
recorder.start()

extIO.StartHW(frequency)

# open file

print('Recording...')
time.sleep(duration)
print('done.')

extIO.StopHW()

recorder.stop = True
recorder.join()

extIO.CloseHW()

# close file
wavFile.close()

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
