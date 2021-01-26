from ctypes import *
from .extio_constants import *
"""


Note: Relied heavily on, and resused some comments/text
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
		self.hwtype = self.ExtHWtype(hwtype.value)
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

	def ShowGUI(self):
		""" 
		Activates the radio's GUI, if it has one
		May require additional DLLs somewhere in the path
		Will also require a window handler in your application code (see examples)
		"""
		self.extIo.ShowGUI()

	def ShowGUI(self):
		""" 
		Hides the radio's GUI, if it has one
		"""
		self.extIo.HideGUI()

	def ShowGUI(self):
		""" 
		Switch visbility of the radio's GUI, if it has one
		"""
		self.extIo.SwitchGUI()

	def ExtIoGetSetting(self, idx = None):
		""" Get optional setting description and value at index idx
			or an ordered list of all the settings
		"""
		# max buffer size specified in header file, but no define was given
		description = create_string_buffer(1024)
		value = create_string_buffer(1024)
		retDescription = None
		retValue = None
		settings = []
		result = None
		if idx != None:
			ret = c_int(self.extIo.ExtIoGetSetting(c_int(idx), byref(description), byref(value))).value
			if ret == 0:
				retDescription = description.value.decode('utf-8')
				retValue = value.value
			result = retDescription, retValue.decode('utf-8')
		else:
			idx = 0
			ret = 0
			while ret == 0:
				ret = c_int(self.extIo.ExtIoGetSetting(c_int(idx), byref(description), byref(value))).value
				if ret == 0:
					settings.append({'description': description.value.decode('utf-8'), 'value': value.value.decode('utf-8')})
					idx += 1
			result = settings
		return result

	class ExtHWtype(Enum):
		NotDefined 		= 0
		SDR14		 	= 1
		SDRX 			= 2
		USBdata16 		= 3 		# the hardware does its own digitization and the audio data are returned to Winrad
									# via the callback device. Data must be in 16-bit  (short) format, little endian.
									#   each sample occupies 2 bytes (=16 bits) with values from  -2^15 to +2^15 -1
		SCdata			= 4			# The audio data are returned via the (S)ound (C)ard managed by Winrad. The external
									# hardware just controls the LO, and possibly a preselector, under DLL control.
		USBdata24 		= 5			# the hardware does its own digitization and the audio data are returned to Winrad
									# via the callback device. Data are in 24-bit  integer format, little endian.
									# each sample just occupies 3 bytes (=24 bits) with values from -2^23 to +2^23 -1
		USBdata32 		= 6			# the hardware does its own digitization and the audio data are returned to Winrad
									# via the callback device. Data are in 32-bit  integer format, little endian.
									# each sample occupies 4 bytes (=32 bits) but with values from  -2^23 to +2^23 -1
		USBfloat32 		= 7			# the hardware does its own digitization and the audio data are returned to Winrad
									# via the callback device. Data are in 32-bit  float format, little endian.
		HPSDR 			= 8			# HPSDR only!
		USBdataU8 		= 9			# the hardware does its own digitization and the audio data are returned to Winrad
									# via the callback device. Data must be in 8-bit  (unsigned) format, little endian.
									# intended for RTL2832U based DVB-T USB sticks
									# each sample occupies 1 byte (=8 bit) with values from 0 to 255
		USBdataS8 		= 10		# the hardware does its own digitization and the audio data are returned to Winrad
									# via the callback device. Data must be in 8-bit  (signed) format, little endian.
									# each sample occupies 1 byte (=8 bit) with values from -128 to 127
		FullPCM32 		= 11    	# the hardware does its own digitization and the audio data are returned to Winrad
									# via the callback device. Data are in 32-bit  integer format, little endian.
									# each sample occupies 4 bytes (=32 bits) with full range: from  -2^31 to +2^31 -1

	class ExtHWstatus(Enum):

		# only processed/understood for SDR14
		Disconnected        = 0     # SDR-14/IQ not connected or powered off
		READY               = 1     # IDLE / Ready
		RUNNING             = 2     # RUNNING  => not disconnected
		ERROR               = 3     # ??
		OVERLOAD            = 4     # OVERLOAD => not disconnected

		# for all extIO's
		Changed_SampleRate  = 100   # sampling speed has changed in the external HW
		Changed_LO          = 101   # LO frequency has changed in the external HW
		Lock_LO             = 102
		Unlock_LO           = 103
		Changed_LO_Not_TUNE = 104   # CURRENTLY NOT YET IMPLEMENTED
									# LO freq. has changed, Winrad must keep the Tune freq. unchanged
									# (must immediately call GetHWLO() )
		Changed_TUNE        = 105   # a change of the Tune freq. is being requested.
		                            # Winrad must call GetTune() to know which value is wanted
		Changed_MODE        = 106   # a change of demod. mode is being requested.
									# Winrad must call GetMode() to know the new mode
		Start               = 107   # The DLL wants Winrad to Start
		Stop                = 108   # The DLL wants Winrad to Stop
		Changed_FILTER      = 109   # a change in the band limits is being requested
									# Winrad must call GetFilters()

		# Above status codes are processed with Winrad 1.32.
		#   All Winrad derivation like WRplus, WinradF, WinradHD and HDSDR should understand them,
		#   but these do not provide version info with VersionInfo(progname, ver_major, ver_minor).

		Mercury_DAC_ON      = 110   # enable audio output on the Mercury DAC when using the HPSDR
		Mercury_DAC_OFF     = 111   # disable audio output on the Mercury DAC when using the HPSDR
		PC_Audio_ON         = 112   # enable audio output on the PC sound card when using the HPSDR
		PC_Audio_OFF        = 113   # disable audio output on the PC sound card when using the HPSDR

		Audio_MUTE_ON       = 114   # the DLL is asking Winrad to mute the audio output
		Audio_MUTE_OFF      = 115   # the DLL is asking Winrad to unmute the audio output

		# Above status codes are processed with Winrad 1.33 and HDSDR
		#   Winrad 1.33 and HDSDR still do not provide their version with VersionInfo()


		# Following status codes are processed when VersionInfo delivers
		#  0 == strcmp(progname, "HDSDR") && ( ver_major > 2 || ( ver_major == 2 && ver_minor >= 13 ) )

		# all extHw_XX_SwapIQ_YYY callbacks shall be reported after each OpenHW() call
		RX_SwapIQ_ON        = 116   # additionaly swap IQ - this does not modify the menu point / user selection
		RX_SwapIQ_OFF       = 117   #   the user selected swapIQ is additionally applied
		TX_SwapIQ_ON        = 118   # additionaly swap IQ - this does not modify the menu point / user selection
		TX_SwapIQ_OFF       = 119   #   the user selected swapIQ is additionally applied


		# Following status codes (for I/Q transceivers) are processed when VersionInfo delivers
		#  0 == strcmp(progname, "HDSDR") && ( ver_major > 2 || ( ver_major == 2 && ver_minor >= 13 ) )

		TX_Request          = 120   # DLL requests TX mode / User pressed PTT
									#   exciter/transmitter must wait until SetModeRxTx() is called!
		RX_Request          = 121   # DLL wants to leave TX mode / User released PTT
									#   exciter/transmitter must wait until SetModeRxTx() is called!
		CW_Pressed          = 122   # User pressed  CW key
		CW_Released         = 123   # User released CW key
		PTT_as_CWkey        = 124   # handle extHw_TX_Request as extHw_CW_Pressed in CW mode
									#  and   extHw_RX_Request as extHw_CW_Released
		Changed_ATT         = 125   # Attenuator changed => call GetActualAttIdx()


		# Following status codes are processed when VersionInfo delivers
		#  0 == strcmp(progname, "HDSDR") && ( ver_major > 2 || ( ver_major == 2 && ver_minor >= 14 ) )

		# Following status codes are for future use - actually not implemented !
		#  0 == strcmp(progname, "HDSDR") && ( ver_major > 2 || ( ver_major == 2 && ver_minor >>> 14 ) )

		# following status codes to change sampleformat at runtime
		SampleFmt_IQ_UINT8  = 126   # change sample format to unsigned 8 bit INT (Realtek RTL2832U)
		SampleFmt_IQ_INT16  = 127   #           -"-           signed 16 bit INT
		SampleFmt_IQ_INT24  = 128   #           -"-           signed 24 bit INT
		SampleFmt_IQ_INT32  = 129   #           -"-           signed 32 bit INT
		SampleFmt_IQ_FLT32  = 130   #           -"-           signed 16 bit FLOAT

		# following status codes to change channel mode at runtime
		RX_ChanMode_LEFT    = 131   # left channel only
		RX_ChanMode_RIGHT   = 132   # right channel only
		RX_ChanMode_SUM_LR  = 133   # sum of left + right channel
		RX_ChanMode_I_Q     = 134   # I/Q with left  channel = Inphase and right channel = Quadrature
									# last option set I/Q and clear internal swap as with extHw_RX_SwapIQ_OFF
		RX_ChanMode_Q_I     = 135   # I/Q with right channel = Inphase and left  channel = Quadrature
									# last option set I/Q and internal swap as with extHw_RX_SwapIQ_ON

		Changed_RF_IF       = 136   # refresh selectable attenuators and Gains
									# => starts calling GetAttenuators(), GetAGCs() & GetMGCs()
		Changed_SRATES      = 137   # refresh selectable samplerates => starts calling GetSamplerates()

		# Following status codes are for 3rd Party Software, currently not implemented in HDSDR
		Changed_PRESEL      = 138  # Preselector changed => call ExtIoGetActualPreselIdx()
		Changed_PRESELS     = 139  # refresh selectable preselectors => start calling ExtIoGetPresels()
		Changed_AGC         = 140  # AGC changed => call ExtIoGetActualAGCidx()
		Changed_AGCS        = 141  # refresh selectable AGCs => start calling ExtIoGetAGCs()
		Changed_SETTINGS    = 142  # settings changed, call ExtIoGetSetting()
		Changed_FREQRANGES  = 143  # refresh selectable frequency ranges, call ExtIoGetFreqRanges()

		Changed_VFO         = 144  # refresh selectable VFO => starts calling ExtIoGetVFOindex()

		# Following status codes are processed when VersionInfo delivers
		#  0 == strcmp(progname, "HDSDR") && ( ver_major > 2 || ( ver_major == 2 && ver_minor >= 60 ) )
		Changed_MGC         = 145  # MGC changed => call ExtIoGetMGC()

"""

// status codes for pfnExtIOCallback; used when cnt < 0
typedef enum
{
  // only processed/understood for SDR14
    extHw_Disconnected        = 0     // SDR-14/IQ not connected or powered off
  , extHw_READY               = 1     // IDLE / Ready
  , extHw_RUNNING             = 2     // RUNNING  => not disconnected
  , extHw_ERROR               = 3     // ??
  , extHw_OVERLOAD            = 4     // OVERLOAD => not disconnected

  // for all extIO's
  , extHw_Changed_SampleRate  = 100   // sampling speed has changed in the external HW
  , extHw_Changed_LO          = 101   // LO frequency has changed in the external HW
  , extHw_Lock_LO             = 102
  , extHw_Unlock_LO           = 103
  , extHw_Changed_LO_Not_TUNE = 104   // CURRENTLY NOT YET IMPLEMENTED
                                      // LO freq. has changed, Winrad must keep the Tune freq. unchanged
                                      // (must immediately call GetHWLO() )
  , extHw_Changed_TUNE        = 105   // a change of the Tune freq. is being requested.
                                      // Winrad must call GetTune() to know which value is wanted
  , extHw_Changed_MODE        = 106   // a change of demod. mode is being requested.
                                      // Winrad must call GetMode() to know the new mode
  , extHw_Start               = 107   // The DLL wants Winrad to Start
  , extHw_Stop                = 108   // The DLL wants Winrad to Stop
  , extHw_Changed_FILTER      = 109   // a change in the band limits is being requested
                                      // Winrad must call GetFilters()

  // Above status codes are processed with Winrad 1.32.
  //   All Winrad derivation like WRplus, WinradF, WinradHD and HDSDR should understand them,
  //   but these do not provide version info with VersionInfo(progname, ver_major, ver_minor).

  , extHw_Mercury_DAC_ON      = 110   // enable audio output on the Mercury DAC when using the HPSDR
  , extHw_Mercury_DAC_OFF     = 111   // disable audio output on the Mercury DAC when using the HPSDR
  , extHw_PC_Audio_ON         = 112   // enable audio output on the PC sound card when using the HPSDR
  , extHw_PC_Audio_OFF        = 113   // disable audio output on the PC sound card when using the HPSDR

  , extHw_Audio_MUTE_ON       = 114   // the DLL is asking Winrad to mute the audio output
  , extHw_Audio_MUTE_OFF      = 115   // the DLL is asking Winrad to unmute the audio output

  // Above status codes are processed with Winrad 1.33 and HDSDR
  //   Winrad 1.33 and HDSDR still do not provide their version with VersionInfo()


  // Following status codes are processed when VersionInfo delivers
  //  0 == strcmp(progname, "HDSDR") && ( ver_major > 2 || ( ver_major == 2 && ver_minor >= 13 ) )

  // all extHw_XX_SwapIQ_YYY callbacks shall be reported after each OpenHW() call
  , extHw_RX_SwapIQ_ON        = 116   // additionaly swap IQ - this does not modify the menu point / user selection
  , extHw_RX_SwapIQ_OFF       = 117   //   the user selected swapIQ is additionally applied
  , extHw_TX_SwapIQ_ON        = 118   // additionaly swap IQ - this does not modify the menu point / user selection
  , extHw_TX_SwapIQ_OFF       = 119   //   the user selected swapIQ is additionally applied


  // Following status codes (for I/Q transceivers) are processed when VersionInfo delivers
  //  0 == strcmp(progname, "HDSDR") && ( ver_major > 2 || ( ver_major == 2 && ver_minor >= 13 ) )

  , extHw_TX_Request          = 120   // DLL requests TX mode / User pressed PTT
                                      //   exciter/transmitter must wait until SetModeRxTx() is called!
  , extHw_RX_Request          = 121   // DLL wants to leave TX mode / User released PTT
                                      //   exciter/transmitter must wait until SetModeRxTx() is called!
  , extHw_CW_Pressed          = 122   // User pressed  CW key
  , extHw_CW_Released         = 123   // User released CW key
  , extHw_PTT_as_CWkey        = 124   // handle extHw_TX_Request as extHw_CW_Pressed in CW mode
                                      //  and   extHw_RX_Request as extHw_CW_Released
  , extHw_Changed_ATT         = 125   // Attenuator changed => call GetActualAttIdx()


  // Following status codes are processed when VersionInfo delivers
  //  0 == strcmp(progname, "HDSDR") && ( ver_major > 2 || ( ver_major == 2 && ver_minor >= 14 ) )

#if 0
  // Following status codes are for future use - actually not implemented !
  //  0 == strcmp(progname, "HDSDR") && ( ver_major > 2 || ( ver_major == 2 && ver_minor >>> 14 ) )

  // following status codes to change sampleformat at runtime
  , extHw_SampleFmt_IQ_UINT8  = 126   // change sample format to unsigned 8 bit INT (Realtek RTL2832U)
  , extHw_SampleFmt_IQ_INT16  = 127   //           -"-           signed 16 bit INT
  , extHw_SampleFmt_IQ_INT24  = 128   //           -"-           signed 24 bit INT
  , extHw_SampleFmt_IQ_INT32  = 129   //           -"-           signed 32 bit INT
  , extHw_SampleFmt_IQ_FLT32  = 130   //           -"-           signed 16 bit FLOAT
#endif
  // following status codes to change channel mode at runtime
  , extHw_RX_ChanMode_LEFT    = 131   // left channel only
  , extHw_RX_ChanMode_RIGHT   = 132   // right channel only
  , extHw_RX_ChanMode_SUM_LR  = 133   // sum of left + right channel
  , extHw_RX_ChanMode_I_Q     = 134   // I/Q with left  channel = Inphase and right channel = Quadrature
                                      // last option set I/Q and clear internal swap as with extHw_RX_SwapIQ_OFF
  , extHw_RX_ChanMode_Q_I     = 135   // I/Q with right channel = Inphase and left  channel = Quadrature
                                      // last option set I/Q and internal swap as with extHw_RX_SwapIQ_ON

  , extHw_Changed_RF_IF       = 136   // refresh selectable attenuators and Gains
                                        // => starts calling GetAttenuators(), GetAGCs() & GetMGCs()
  , extHw_Changed_SRATES      = 137   // refresh selectable samplerates => starts calling GetSamplerates()

  // Following status codes are for 3rd Party Software, currently not implemented in HDSDR
  , extHw_Changed_PRESEL      = 138  // Preselector changed => call ExtIoGetActualPreselIdx()
  , extHw_Changed_PRESELS     = 139  // refresh selectable preselectors => start calling ExtIoGetPresels()
  , extHw_Changed_AGC         = 140  // AGC changed => call ExtIoGetActualAGCidx()
  , extHw_Changed_AGCS        = 141  // refresh selectable AGCs => start calling ExtIoGetAGCs()
  , extHw_Changed_SETTINGS    = 142  // settings changed, call ExtIoGetSetting()
  , extHw_Changed_FREQRANGES  = 143  // refresh selectable frequency ranges, call ExtIoGetFreqRanges()

  , extHw_Changed_VFO         = 144  // refresh selectable VFO => starts calling ExtIoGetVFOindex()

  // Following status codes are processed when VersionInfo delivers
  //  0 == strcmp(progname, "HDSDR") && ( ver_major > 2 || ( ver_major == 2 && ver_minor >= 60 ) )
  , extHw_Changed_MGC         = 145  // MGC changed => call ExtIoGetMGC()

} extHWstatusT;

"""