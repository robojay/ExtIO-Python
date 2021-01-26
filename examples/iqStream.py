from ctypes import *
import threading
import queue
import time

import numpy as np

callbackHits = 0
callbackInfo = 0
callbackData = 0
callbackMisses = 0
overruns = 0
queueFailures = 0
type = None
sampleRate = None
typesSupported = None
extIO = None
enabled = False
queueEntries = None
head = 0
tail = 0
buffer = []
entrySize = None
bytesPerCallback = None
deltaTimeExpected = None

debugCallbackData = False
debugCallbackInfo = False


def init(_typesSupported, _extIO, _queueEntries = 64):
	global callbackHits
	global callbackInfo
	global callbackData
	global callbackMisses
	global overruns
	global queueFailures
	global type
	global sampleRate
	global typesSupported
	global extIO
	global enabled
	global queueEntries
	global head
	global tail
	global buffer
	global entrySize
	global bytesPerCallback
	global deltaTimeExpected

	callbackHits = 0
	callbackInfo = 0
	callbackData = 0
	callbackMisses = 0
	overruns = 0
	queueFailures = 0
	type = _extIO.hwtype
	sampleRate = None
	typesSupported = _typesSupported
	extIO = _extIO
	enabled = False
	queueEntries = _queueEntries
	head = 0
	tail = 0
	buffer = []

def initBuffers():
	global callbackHits
	global callbackInfo
	global callbackData
	global callbackMisses
	global overruns
	global queueFailures
	global type
	global sampleRate
	global typesSupported
	global extIO
	global enabled
	global queueEntries
	global head
	global tail
	global buffer
	global entrySize
	global bytesPerCallback
	global deltaTimeExpected

	entrySize = extIO.iqPairs
	bytesPerCallback = entrySize * 4

	for i in range(0, queueEntries):
		buffer.append(create_string_buffer(bytesPerCallback))

	deltaTimeExpected = (extIO.iqPairs)/ sampleRate  


def iqStreamCallback(cnt, status, IQoffs, IQdata):
	""" callback function """
	#  (int cnt, int status, float IQoffs, void *IQdata);
	global callbackHits
	global callbackInfo
	global callbackData
	global callbackMisses
	global overruns
	global queueFailures
	global type
	global sampleRate
	global typesSupported
	global extIO
	global enabled
	global queueEntries
	global head
	global tail
	global buffer
	global entrySize
	global bytesPerCallback
	global deltaTimeExpected

	t1 = time.perf_counter()

	callbackHits += 1

	if cnt > 0:
		# we have data
		if enabled:
			callbackData += 1

			if type == extIO.ExtHWtype.USBdata16:
				# INT16
				tempBuf = cast(IQdata, POINTER(c_char * bytesPerCallback))			
				memmove(buffer[head], tempBuf, bytesPerCallback)
				newHead = head  + 1
				if (newHead >= queueEntries):
					newHead = 0
				if newHead == tail:
					overruns += 1
				else:
					head = newHead
			
			#do this later...elif type == ...:
				# INT24, etc.

			else:
				print('[iqStreamCallback] No valid type set (' + str(type) + ')')
				# should handle this better... but for now
				exit()

			t2 = time.perf_counter()
			dT = t2 - t1
			if dT > deltaTimeExpected:
				callbackMisses += 1

	elif cnt == -1:
		# we have driver info
		callbackInfo += 1

		# TODO: changing sample rate and/or format mid recording should cause some 
		# kind of event to stop the recorder, save the file, and reopen a new file for
		# new data
		# one possibility is to insert this type of state change into the queue

		if status == extIO.ExtHWstatus.Changed_SampleRate:
			sampleRate = extIO.ExtIoGetSrates(extIO.ExtIoGetActualSrateIdx())
			deltaTimeExpected = (extIO.iqPairs)/ sampleRate  
		
		elif status == extIO.ExtHWstatus.SampleFmt_IQ_INT16:
			type = extIO.ExtHWtype.USBdata16 

		elif status == extIO.ExtHWstatus.SampleFmt_IQ_UINT8:
			type = extIO.ExtHWtype.USBdataU8

		elif status == extIO.ExtHWstatus.SampleFmt_IQ_INT24:
			type = extIO.ExtHWtype.USBdata24 

		elif status == extIO.ExtHWstatus.SampleFmt_IQ_INT32:
			type = extIO.ExtHWtype.USBdata32 

		elif status == extIO.ExtHWstatus.SampleFmt_IQ_FLT32:
			type = extIO.ExtHWtype.USBfloat32 

		if type not in typesSupported:
			# should handle this better... but for now				
			print('[iqStreamCallback] Unsupported Hardware Type') 
			print(type)
			print(typesSupported)
			exit()

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


""" Saved for later

			if enabled:
				callbackData += 1
				if type == extIO.ExtHWtype.USBdata16:
					# INT16
					tempBuf = cast(IQdata, POINTER(c_int))			
					tempArray = np.ctypeslib.as_array(tempBuf, shape=(2 * int(cnt/sizeof(c_int)),))
					try:
						queue.put_nowait(tempArray)
					except queue.Full:
						overruns += 1

"""