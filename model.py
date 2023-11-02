# modify from mdo_simple_plot.py
# python v3.x, pyvisa v1.8
# should work with MSO70k, DPO7k, MSO5k, MDO4k, MDO3k, and MSO2k series
# 5/6 Series MSO 

# incompatible with TDS2k and TBS1k series (see tbs simple plot)

import time # std module
import pyvisa as visa # http://github.com/hgrecco/pyvisa
import matplotlib.pyplot as plt # http://matplotlib.org/
import numpy as np # http://www.numpy.org/

class Oscilloscope:
    def __init__(self, visa_address):
        self.visa_address = visa_address
        self.rm = visa.ResourceManager()
        self.scope = self.rm.open_resource(visa_address)
        self.scope.timeout = 10000 # ms
        self.scope.encoding = 'latin_1'
        self.scope.read_termination = '\n'
        self.scope.write_termination = None
        self.scope.write('*cls') # clear ESR
        print(self.scope.query('*idn?'))
        input("""
        ACTION:
        Connect probe to oscilloscope Channel 1 and the probe compensation signal.

        Press Enter to continue...
        """)

    def reset(self):
        self.scope.write('*rst') # reset
        t1 = time.perf_counter()
        r = self.scope.query('*opc?') # sync
        t2 = time.perf_counter()
        print('reset time: {}'.format(t2 - t1))

    def autoset(self):
        self.scope.write('autoset EXECUTE') # autoset
        t3 = time.perf_counter()
        r = self.scope.query('*opc?') # sync
        t4 = time.perf_counter()
        print('autoset time: {} s'.format(t4 - t3))

    # io config
    def ioConfig(self):
        self.scope.write('header 0')
        self.scope.write('data:encdg SRIBINARY')
        self.scope.write('data:source CH1') # channel
        self.scope.write('data:start 1') # first sample
        self.record = int(self.scope.query('horizontal:recordlength?')) # default 10000 samples
        self.scope.write('data:stop {}'.format(self.record)) # last sample
        self.scope.write('wfmoutpre:byt_n 1') # 1 byte per sample

    # acq config
    def acqConfig(self):       
        self.scope.write('acquire:state 0') # stop
        #self.scope.write('SELECT:CH1 ON')
        self.scope.write('acquire:stopafter SEQUENCE') # single
        self.scope.write('acquire:state 1') # run
        t5 = time.perf_counter()
        r = self.scope.query('*opc?') # sync
        t6 = time.perf_counter()
        print('acquire time: {} s'.format(t6 - t5))

    # data query
    def dataQuery(self):
        t7 = time.perf_counter()
        self.bin_wave = self.scope.query_binary_values('curve?', datatype='b', container=np.array)
        t8 = time.perf_counter()
        print('transfer time: {} s'.format(t8 - t7))

    # retrieve scaling factors
    def retrieveAcqSetting(self):
        self.tscale = float(self.scope.query('wfmoutpre:xincr?'))
        self.tstart = float(self.scope.query('wfmoutpre:xzero?'))
        self.vscale = float(self.scope.query('wfmoutpre:ymult?')) # volts / level
        self.voff = float(self.scope.query('wfmoutpre:yzero?')) # reference voltage
        self.vpos = float(self.scope.query('wfmoutpre:yoff?')) # reference position (level)
        self.yunit = self.scope.query('WFMInpre:YUNit?') # return "v" with /" sign
    
    # error checking
    def errorChecking(self):
        r = int(self.scope.query('*esr?'))
        print('event status register: 0b{:08b}'.format(r))
        r = self.scope.query('allev?').strip()
        print('all event messages: {}'.format(r))

    # create scaled vectors
    def createScaledVectors(self):
        # horizontal (time)
        total_time = self.tscale * self.record
        tstop = self.tstart + total_time
        self.scaled_time = np.linspace(self.tstart, tstop, num=self.record, endpoint=False)
        # vertical (voltage)
        unscaled_wave = np.array(self.bin_wave, dtype='double') # data type conversion
        self.scaled_wave = (unscaled_wave - self.vpos) * self.vscale + self.voff
    # plotting
    def plotting(self):
        plt.plot(self.scaled_time, self.scaled_wave)
        plt.title('channel 1') # plot label
        plt.xlabel('time (seconds)') # x label
        plt.ylabel(self.yunit) # y label
        print("look for plot window...")
        plt.show()

    #save curve data in .csv format
    def saveCurve(self, file_name):
        f = open(file_name + '.csv', 'w')
        f.write('s' + ',' + self.yunit + '\n')
        for i in range(self.record):
            f.write(str(self.scaled_time[i]) + ',' + str(self.scaled_wave[i]) + '\n')
        f.close()
    
    def saveHardcopy(self, file_name):
        # Save image on scope harddrive
        self.scope.write('SAVE:IMAGE \'c:/TEMP.PNG\'')
        self.scope.query("*OPC?")  #Make sure the image has been saved before trying to read the file

        # Read file data over
        self.scope.write('FILESYSTEM:READFILE \'c:/TEMP.PNG\'')
        data = self.scope.read_raw() # return byte data

        # Save file to local PC
        fid = open(file_name + '.png', 'wb')
        fid.write(data)
        fid.close()
        
        # delete the temporary image file of the Oscilloscope when this is done as well. 
        self.scope.write('FILESystem:DELEte \'c:/TEMP.PNG\'')

    def saveWaveform(self, file_name):
        # Save wafeform in csv file
        self.scope.write('SAVe:WAVEform ALL,\'c:/TEMP.CSV\'')
        self.scope.query("*OPC?")
        
        # Read file data over
        self.scope.write('FILESYSTEM:READFILE \'c:/TEMP_ALL.CSV\'') # _ALL will be added automatically
        data = self.scope.read_raw()

        # Save file to local PC
        fid = open(file_name + '.csv', 'w')
        fid.write(data) # todo: convert byte to str
        fid.close()
        
        # delete the temporary image file of the Oscilloscope when this is done as well. 
        self.scope.write('FILESystem:DELEte \'c:/TEMP_ALL.CSV\'')
