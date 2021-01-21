from ctypes import *
from .extio_constants import *

"""


Note: Relied heavily on, and resused some function comments
from the C header example:
http://www.hdsdr.de/download/LC_ExtIO_Types.h

"""

class ExtIO():
	""" ExtIO Class """
	def __init__(self, dllName):
		""" Create the ExtIO object and load the DLL """
		self.extIo = WinDLL(dllName)
		self.name = None
		self.model = None
		self.hwtype = None
		self.callback = None
		self.iqPairs = None
		self.extLOfreq = None

	# Mandatory Functions - all radios should support these

	def InitHW(self):
		""" Initialize the radio, returns name, model and hwtype """
		name = create_string_buffer(EXTIO_MAX_NAME_LEN)
		model = create_string_buffer(EXTIO_MAX_MODEL_LEN)
		hwtype = c_int()
		self.extIo.InitHW(byref(name), byref(model), byref(hwtype))
		self.name = name.value.decode('utf-8')
		self.model = model.value.decode('utf-8')
		self.hwtype = hwtype.value
		return self.name, self.model, self.hwtype

	def SetCallback(self, callbackFunction):
		""" 
		Set callback function 
		Should be defined like this:
		def extIoCallback(cnt, status, IQoffs, IQdata):

		With C call looking like this:
		ExtIOCallback(int cnt, int status, float IQoffs, void *IQdata) 
		"""
		callbackType = CFUNCTYPE(None, c_int, c_int, c_float, c_void_p)
		self.callback = callbackType(callbackFunction)
		self.extIo.SetCallback(self.callback)

	def OpenHW(self):
		""" Open radio, returns True if successfull """
		return c_bool(self.extIo.OpenHW()).value

	def StartHW(self, extLOfreq):
		""" 
		Starts data capture at local oscillator frequency (in Hertz)
		There are two versions of this DLL call,
		one that takes a 32-bit frequency, and another that
		takes a 64-bit frequency

		This function will attempt to call the 64-bit version
		first

		Returns the number of I/Q pairs that will be returned
		with each callback call
		"""

		try:
			self.iqPairs = c_int(self.extIo.StartHW64(c_int64(extLOfreq))).value
		except:
			self.iqPairs = c_int(self.extIo.StartHW(c_long(extLOfreq))).value

		self.extLOfreq = extLOfreq
		return self.iqPairs

	def StopHW(self):
		self.extIo.StopHW()

	def CloseHW(self):
		""" Close radio, returns True if successfull """
		return c_bool(self.extIo.CloseHW()).value

	def SetHWLO(self, extLOfreq):
		"""
		Sets the local oscillator

		Attempts to call the 64-bit version first,
		then falls back to the 32-bit version
	
		Returns:
			== 0: The function did complete without errors.
			< 0 (a negative number N):
				The specified frequency is lower than the minimum that
				the hardware is capable to generate. The absolute value
				of N indicates what is the minimum supported by the HW.
			> 0 (a positive number N):
				The specified frequency is greater than the maximum
				that the hardware is capable to generate. The value
				of N indicates what is the maximum supported by the HW.
		"""
		try:
			retVal = c_int64(self.extIo.SetHWLO64(c_int64(extLOfreq))).value
		except:
			retVal = c_int(self.extIo.SetHWLO(c_int(extLOfreq))).value

		self.extLOfreq = extLOfreq
		return retVal

	# Optional Functions - not all radios will support these

	def foo(self):
		""" used to verify exception catching of non-existent DLL functions """
		self.extIo.FooBar(c_int(10))


	def ExtIoGetSrates(self, idx = None):
		""" returns sample rate of index value, or an ordered list of all the sample rate 
		    which is slightly different than the original C call
		    but probably what they would have done if it was as easy as Python
		"""
		retVal = None
		if idx != None:
			sampleRateValue = c_double()		
			ret = c_int(self.extIo.ExtIoGetSrates(c_int(idx), byref(sampleRateValue))).value
			if ret == 0:
				retVal = sampleRateValue.value
			else:
				retVal = None
		else:
			sampleRateValue = c_double()		
			self.sRates = []
			ret = 0
			index = 0
			while ret == 0:
				ret = c_int(self.extIo.ExtIoGetSrates(c_int(index), byref(sampleRateValue))).value
				if ret == 0:
					self.sRates.append(sampleRateValue.value)
					index += 1
			retVal = self.sRates
		return retVal

	def ExtIoGetActualSrateIdx(self):
		""" Returns index of sample rate setting """
		self.actualSrateIdx = c_int(self.extIo.ExtIoGetActualSrateIdx()).value
		if self.actualSrateIdx == -1:
			self.actualSrateIdx = None 
		return self.actualSrateIdx

	def ExtIoSetSrate(self, idx):
		""" Sets sample rate index to idx , False if an error """
		if c_int(self.extIo.ExtIoSetSrate(c_int(idx))).value != -1:
			return True
		else:
			return False

