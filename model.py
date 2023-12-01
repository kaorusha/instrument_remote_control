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

def selectModel(rm: visa.ResourceManager):
    """Run at the beginning to map different devices with their address and names.
    When detecting matched key word of model, initiating with matched device class.
    ## Parameters
    ### rm : str
        resource manager instance
    ## Returns
    ### device
        grouping power supply, signal generator, and oscilloscope for running test
    """
    info = rm.list_resources()
    device = Devices()
    
    for visa_add in info:
        try:
            resource = rm.open_resource(visa_add)
            scopename = resource.query("*IDN?")
            if '62012P' in scopename:
                device.power = PowerSupply(scopename, resource)
            elif 'AFG' in scopename:
                device.signal = SignalGenerator(scopename, resource)
            elif 'MDO' in scopename:
                device.osc = Oscilloscope(scopename, resource)
            elif 'MSO' in scopename:
                device.osc = Oscilloscope(scopename, resource)
            else:
                print("Please check new device: " + scopename)
            break
        except visa.VisaIOError:
            print("No instrument found: " + visa_add)
            break
        except:
            print("Error Communicating with this device")
        
    # oscilloscope idn: TEKTRONIX,MSO46,C033493,CF:91.1CT FV:1.44.3.433
    # device.osc.visa_address = 'USB0::0x0699::0x0527::C033493::INSTR' # hard coded name for test
    # power supply idn: CHROMA,62012P-80-60,03.30.1,05648
    # device.power.visa_address = 'USB0::0x1698::0x0837::001000005648::INSTR'
    # signal generator idn: TEKTRONIX,AFG31052,C013019,SCPI:99.0 FV:1.5.2
    # device.signal.visa_address = 'USB0::0x0699::0x0358::C013019::INSTR'
    return device

def autosetSingleCurvePlot():
    rm = visa.ResourceManager()
    osc = selectModel(rm).osc
    osc.autoset()
    osc.ioConfig()
    osc.acqConfig()
    osc.dataQuery()
    osc.retrieveAcqSetting()
    osc.errorChecking()
    osc.scope.close()
    rm.close()

    osc.createScaledVectors()
    osc.plotting()
    osc.saveCurve('osc_curve')

def outputAllChannelSignal():
    rm = visa.ResourceManager()
    osc = selectModel(rm).osc
    osc.saveHardcopy('hardcopy')
    osc.saveWaveform('waveform')
    osc.errorChecking()
    osc.scope.close()
    rm.close()

def takeMeasurement():
    rm = visa.ResourceManager()
    osc = selectModel(rm).osc
    osc.acquireMeasure()
    osc.scope.close()
    rm.close()

def controlPowerSupply():
    rm = visa.ResourceManager()
    power = selectModel(rm).power
    power.reset()
    power.setVoltage(7)
    power.setOutputOn()
    power.errorChecking()
    power.scope.close()
    rm.close()

def controlSignalGenerator():
    rm = visa.ResourceManager()
    pwm = selectModel(rm).signal
    pwm.reset()
    pwm.setPWMOutput()
    pwm.setPWMDuty(50)
    pwm.errorChecking()
    pwm.scope.close()
    rm.close()

class Devices():
    def __init__(self):
        self.osc: Oscilloscope
        self.power: PowerSupply
        self.signal: SignalGenerator

class Oscilloscope:
    def __init__(self, name: str, scope: visa.resources.Resource):
        self.id = name
        self.visa_address = scope.resource_name
        self.scope = scope
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
    def __init__(self, name: str, scope: visa.resources.Resource):
        self.id = name
        self.visa_address = scope.resource_name
        self.scope = scope
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
    def __init__(self, name: str, scope: visa.resources.Resource):
        self.id = name
        self.visa_address = scope.resource_name
        self.scope = scope
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
