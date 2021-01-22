from ctypes import *
import threading
import queue

import numpy as np

class IqStream():
	"""
	Class to handle the IQ streaming data

	"""
	def __init__(self, typesSupported, extIO, queueEntries = 64):
		self.callbackHits = 0
		self.callbackInfo = 0
		self.callbackData = 0
		self.overruns = 0
		self.queue = queue.Queue(queueEntries)
		self.type = extIO.hwtype
		self.sampleRate = None
		self.typesSupported = typesSupported
		self.extIO = extIO

		self.debugCallbackData = False
		self.debugCallbackInfo = False

	def iqStreamCallback(self, cnt, status, IQoffs, IQdata):
		""" callback function """
		#  (int cnt, int status, float IQoffs, void *IQdata);

		self.callbackHits += 1

		if cnt > 0:
			# we have data
			self.callbackData += 1
			if self.type == self.extIO.ExtHWtype.USBdata16:
				# INT16
				tempBuf = cast(IQdata, POINTER(c_int))			
				tempArray = np.ctypeslib.as_array(tempBuf, shape=(2 * int(cnt/sizeof(c_int)),))
				try:
					self.queue.put_nowait(tempArray)
				except queue.Full:
					self.overruns += 1

			#do this later...elif iqStream.type == ...:
				# INT24, etc.

			else:
				print('[iqStreamCallback] No valid type set (' + str(self.type) + ')')
				# should handle this better... but for now
				exit()

		elif cnt == -1:
			# we have driver info
			self.callbackInfo += 1

			# TODO: changing sample rate and/or format mid recording should cause some 
			# kind of event to stop the recorder, save the file, and reopen a new file for
			# new data
			# one possibility is to insert this type of state change into the queue

			if status == self.extIO.ExtHWstatus.Changed_SampleRate:
				self.sampleRate = self.extIO.ExtIoGetSrates(self.extIO.ExtIoGetActualSrateIdx())		

			elif status == self.extIO.ExtHWstatus.SampleFmt_IQ_INT16:
				self.type = self.extIO.ExtHWtype.USBdata16 

			elif status == self.extIO.ExtHWstatus.SampleFmt_IQ_UINT8:
				self.type = self.extIO.ExtHWtype.USBdataU8

			elif status == self.extIO.ExtHWstatus.SampleFmt_IQ_INT24:
				self.type = self.extIO.ExtHWtype.USBdata24 

			elif status == self.extIO.ExtHWstatus.SampleFmt_IQ_INT32:
				self.type = self.extIO.ExtHWtype.USBdata32 

			elif status == self.extIO.ExtHWstatus.SampleFmt_IQ_FLT32:
				self.type = self.extIO.ExtHWtype.USBfloat32 

			if self.type not in self.typesSupported:
				# should handle this better... but for now				
				print('[iqStreamCallback] Unsupported Hardware Type') 
				print(self.type)
				print(self.typesSupported)
				exit()

		# this is really slow, and if enabled (especially for data)
		# may cause data loss
		if (self.debugCallbackData) or (self.debugCallbackInfo and cnt < 0):	
			print('[Callback] ', end = '')
			print(cnt, end = '')
			print(' ', end = '')
			print(status, end = '')
			print(' ', end = '')
			print(IQoffs, end = '')
			print(' ', end = '')
			print(IQdata)
