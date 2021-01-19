import os

if os.name != 'nt':
	raise ImportError ('extio is only supported under Windows')
else:
	from .extio import *
	from .extio_constants import *

