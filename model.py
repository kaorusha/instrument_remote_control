# modify from mdo_simple_plot.py (https://github.com/tektronix/Programmatic-Control-Examples)
# python v3.x, pyvisa v1.8
# should work with MSO70k, DPO7k, MSO5k, MDO4k, MDO3k, and MSO2k series
# 5/6 Series MSO 

# incompatible with TDS2k and TBS1k series (see tbs simple plot)

import time # std module
import pyvisa as visa # http://github.com/hgrecco/pyvisa
import matplotlib.pyplot as plt # http://matplotlib.org/
import numpy as np # http://www.numpy.org/
from enum import Enum
import openpyxl

class Oscilloscope:
    def __init__(self, visa_address):
        self.visa_address = visa_address
        self.rm = visa.ResourceManager()
        self.scope = self.rm.open_resource(visa_address)
        self.scope.timeout = 10000 # ms
        self.scope.encoding = 'latin_1'
        self.scope.read_termination = ''
        self.scope.write_termination = None
        # Good practice to flush the message buffers and clear the instrument status upon connecting.
        self.scope.clear()
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
        self.yunit = self.scope.query('WFMInpre:YUNit?')
    
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
        try:
            data = self.scope.read_raw() # return byte data
        except visa.VisaIOError as e:
            print("There was a visa error with the following message: {0} ".format(repr(e)))
            print("Oscilloscope Error Status Register is: "+str(self.scope.query("*ESR?")))
            print(self.scope.query("ALLEV?"))

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
        try:
            data = self.scope.read_raw()
        except visa.VisaIOError as e:
            print("There was a visa error with the following message: {0} ".format(repr(e)))
            print("Oscilloscope Error Status Register is: "+str(self.scope.query("*ESR?")))
            print(self.scope.query("ALLEV?"))

        # Save file to local PC
        fid = open(file_name + '.csv', 'wb')
        fid.write(data)
        fid.close()
        
        # delete the temporary waveform file of the Oscilloscope when this is done as well. 
        self.scope.write('FILESystem:DELEte \'c:/TEMP_ALL.CSV\'')

    class Channel(Enum):
    # channel definition
    # ch1:volt
    # ch2:PWM
    # ch3:FG signal
    # ch4:current
        vcc = 1
        pwm = 2
        FG = 3
        current = 4

    class Measure:
        rpm = 0.0
        pwm = 0.0
        start_up_volt = 0.0
        max_current_on_steady = 0.0
        avg_op_current = 0.0
        max_start_up_current = 0.0
        min_current_on_steady = 0.0

    def queryMeasurement(self, type = "MEAN", channel = Channel.vcc):
        self.scope.write("MEASUREMENT:IMMED:TYPE " + type)
        self.scope.write("MEASUREMENT:IMMED:SOURCE CH" + str(channel))
        res = self.scope.query("MEASUREMENT:IMMED:VALUE?")
        # log
        # print("channel " + str(channel.value) + "(" + type + "): " + res) 
        return res
    
    # measureing fan speed in RPM through FG signal frequency
    def acquireMeasure(self):
        result = self.Measure()
        result.start_up_volt = float(self.queryMeasurement())
        # MEASUrement:CH<x>:REFLevels:ABSolute:FALLHigh?
        result.pwm = float(self.queryMeasurement("PDUTY", self.Channel.pwm)) # '9.91E+37\n'
        result.rpm = float(self.queryMeasurement("FREQUENCY", self.Channel.FG)) # '9.91E+37\n'
        
        result.max_current_on_steady = float(self.queryMeasurement("MAXIMUM", self.Channel.current))
        result.avg_op_current = float(self.queryMeasurement("MEAN", self.Channel.current))
        result.max_start_up_current = float(self.queryMeasurement("RMS", self.Channel.current))        
        result.min_current_on_steady = float(self.queryMeasurement("PK2Pk", self.Channel.current))
        return result

    def saveResult(self, sample_no = 1, new_file_name = 'output'):
        result = self.acquireMeasure()
        wb = openpyxl.load_workbook('風扇樣品檢驗報告(for RD).xlsx')
        sheet = wb.active
        row = str(sample_no + 9)
        sheet['K' + row] = result.pwm
        sheet['L' + row] = result.start_up_volt
        sheet['M' + row] = result.max_current_on_steady
        sheet['N' + row] = result.avg_op_current
        sheet['O' + row] = result.max_start_up_current
        sheet['Q' + row] = result.max_current_on_steady/result.min_current_on_steady
        wb.save(new_file_name)

class PowerSupply:
    def __init__(self, visa_address):
        self.visa_address = visa_address
        self.rm = visa.ResourceManager()
        self.scope = self.rm.open_resource(visa_address)
        self.scope.timeout = 10000 # ms
        self.scope.read_termination = '\r\n'
        self.scope.query_termination = '\r\n'
        self.scope.write_termination = '\r\n'
        # Good practice to flush the message buffers and clear the instrument status upon connecting.
        self.scope.write('*cls') # clear ESR
        print(self.scope.query('*idn?'))
        input("""
        ACTION:
        Power supply ready for remote control.
        Press Enter to continue...
        """)
    def reset(self):
        self.scope.write('*rst') # reset
        t1 = time.perf_counter()
        r = self.scope.query('*opc?') # sync
        t2 = time.perf_counter()
        print('reset time: {}'.format(t2 - t1))

    def errorChecking(self):
        r = int(self.scope.query('*esr?'))
        print('event status register: 0b{:08b}'.format(r))
        r = self.scope.query('SYSTem:ERRor?').strip()
        print('all event messages: {}'.format(r))

    def setVoltage(self, volt):
        self.scope.write("SOUR:VOLT " + str(volt))

    def setOutputOn(self):
        self.scope.write("CONFIgure:OUTPut ON")

class SignalGenerator:
    def __init__(self, visa_address):
        self.visa_address = visa_address
        self.rm = visa.ResourceManager()
        self.scope = self.rm.open_resource(visa_address)
        self.scope.timeout = 10000 # ms
        self.scope.read_termination = '\n'
        self.scope.write_termination = None
        # Good practice to flush the message buffers and clear the instrument status upon connecting.
        self.scope.clear()
        self.scope.write('*cls') # clear ESR
        print(self.scope.query('*idn?'))
        input("""
        ACTION:
        Signal generator ready for remote control.
        Press Enter to continue...
        """)
    
    def reset(self):
        self.scope.write('*rst') # reset
        t1 = time.perf_counter()
        r = self.scope.query('*opc?') # sync
        t2 = time.perf_counter()
        print('reset time: {}'.format(t2 - t1))
    
    def errorChecking(self):
        r = int(self.scope.query('*esr?'))
        print('event status register: 0b{:08b}'.format(r))
        r = self.scope.query('SYSTem:ERRor?').strip()
        print('all event messages: {}'.format(r))

    def setPWMOutput(self):
        self.scope.write('SOURCE1:FUNCTION:SHAPE PULS')
        self.scope.write('SOURce1:PWM:STATe ON')
        self.scope.write('SOURce1:PWM:SOURce INTernal')
        self.scope.write('FREQuency 25E3')
        self.scope.write('SOURce1:PWM:INTernal:FUNCtion SQUare')
        self.scope.write('SOURce1:VOLTage:LEVel:IMMediate:AMPLitude 5VPP')
    
    def setPWMDuty(self, duty = 5.0):
        if (duty > 99.25):
            duty = 99.25
        if (duty < 1.0):
            duty = 1.0
        self.scope.write("SOURce1:PULSe:DCYCle " + str(duty))
        r = self.scope.query('*opc?') # sync
