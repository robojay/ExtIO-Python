import ctypes

class ExtIO():
	""" ExtIO Class """ 
	def __init__(self, dllName):
		""" Create the ExtIO object and load the DLL """
		self.extIO = ctypes.WinDLL(dllName)
		 