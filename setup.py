import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="extio",
    version="0.0.1",
    author="Jay Francis",
    author_email="jay@robojay.us",
    description="Python access of ExtIO driver based Software Defined Radios (SDRs)",
    long_description="""\
# ExtIO-Python
Python package and examples to work with ExtIO driver based Software Defined Radios (SDRs)

## IMPORTANT NOTES!!!
- ExtIO DLLs are Windows DLLs.  The code in this repository has only been tested under Windows 10, and is not currently supported on any other operating system
- Consider the current status to be PRE-Alpha, a work in progress, lots of bugs and use case failures ;-)
- Receive only
- Testing is performed with an Icom R8600
- Future testing will include RTL-SDR, ADI Pluto, and SoftRock
- Python3 32-bit is required (the DLLs are 32-bit), testing with Python 3.8.6

## Reference Links
[HDSDR Homepage](http://www.hdsdr.de/): For information about ExtIO and links to specific [hardware](http://www.hdsdr.de/hardware.html) support.
""",
    long_description_content_type="text/markdown",
    url="https://github.com/robojay/ExtIO-Python",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Development Status :: 2 - Pre-Alpha",
    ],
    python_requires='>=3.8',
)
