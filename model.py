# modify from mdo_simple_plot.py (https://github.com/tektronix/Programmatic-Control-Examples)
# python v3.x, pyvisa v1.8
# should work with MSO70k, DPO7k, MSO5k, MDO4k, MDO3k, and MSO2k series
# 5/6 Series MSO 

# incompatible with TDS2k and TBS1k series (see tbs simple plot)

from ast import Tuple
import time
from typing import Literal
import warnings # std module
import pyvisa as visa # http://github.com/hgrecco/pyvisa
import matplotlib.pyplot as plt # http://matplotlib.org/
import numpy as np # http://www.numpy.org/
from enum import Enum
import openpyxl
import os
from math import floor, log

class TypeEnum(Enum):
    osc = 0
    power = 1
    signal = 2

class Instrument:
    """
    a template class to store instrument information and common base attribute using VISA resource.
    list: For gui update. Stores all instrument's id of these class that connect to PC.
    boolean update: notation for gui to update
    """
    def __init__(self):
        self.update = False
        self.list_id = list()
        self.id: str
        self.scope: visa.resources.Resource
    
    def printStartMsg(self, msg:str):
        """
        Good practice to flush the message buffers and clear the instrument status upon connecting.
        """
        self.scope.write('*cls') # clear ESR
        print(self.scope.query('*idn?'))
        print(msg)

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
    
    def setScope():
        """
        Base function for child class to set different termination signal of each instrument
        """
        pass

class Model:
    """
    Save different script of test steps.
    Use resource manager to call different instrument.
    Save an instrument dictionary.
    """
    
    class DictValue:
        def __init__(self, num: TypeEnum, id:str):
            self.type = num
            self.id = id

    def __init__(self, dummy:bool = False) -> None:
        '''
        Parameters
        ----------
        dummy : for testing, without device connected
        '''
        self.rm = visa.ResourceManager()
        self.inst_dict = dict()
        """
        dictionary
        * key: visa address
        * value: DictValue
        """
        self.id_dict = dict()
        """
        dictionary
        * key: id
        * value: visa address
        """
        self.osc = Oscilloscope()
        self.power = PowerSupply()
        self.signal = SignalGenerator()
        self.dummy = dummy

    def listDevices(self):
        """Run to map different devices with their address and names.
        Categorize the model by detecting matched key word, update the following attribute:
        * list_id: corresponding instrument class (for GUI)
        * inst_dict: memorize the visa address and its id and type
        * id_dict: if user select instrument from GUI, this dictionary memorize its address
        """
        # Currently use case:
        # 3 instrument are connected to PC via USB, which are power supply, signal generator,
        # and oscilloscope, so only one test sample at a time.
        # When instrument accidentally disconnect, delete the corresponding instance and update
        # connected instrument on the GUI panel. 
        # It is possible to test multiple samples parallel by connecting multiple devices 
        # through TCP/IP, but the code need modification.
        info = []
        try:
            info = self.rm.list_resources()
        except:
            print("No instrument found")
        if self.dummy:
            info = ['USB0::0x0699::0x0527::C033493::INSTR', 'USB0::0x1698::0x0837::001000005648::INSTR', 'USB0::0x0699::0x0358::C013019::INSTR']
        # oscilloscope idn: TEKTRONIX,MSO46,C033493,CF:91.1CT FV:1.44.3.433
        # visa_address = 'USB0::0x0699::0x0527::C033493::INSTR'
        # power supply idn: CHROMA,62012P-80-60,03.30.1,05648
        # visa_address = 'USB0::0x1698::0x0837::001000005648::INSTR'
        # signal generator idn: TEKTRONIX,AFG31052,C013019,SCPI:99.0 FV:1.5.2
        # visa_address = 'USB0::0x0699::0x0358::C013019::INSTR'
            
        for visa_add in info:
            if self.inst_dict and visa_add in self.inst_dict: 
                continue
            # new device detected
            try:
                scopename = self.getScopeName(visa_add)
                self.id_dict[scopename] = visa_add
                if '62012P' in scopename:
                    self.inst_dict[visa_add] = self.DictValue(TypeEnum.power, scopename)
                    self.power.list_id.append(scopename)
                    self.power.update = True
                elif 'AFG' in scopename:
                    self.inst_dict[visa_add] = self.DictValue(TypeEnum.signal, scopename)
                    self.signal.list_id.append(scopename)
                    self.signal.update = True
                elif 'MDO' in scopename or 'MSO' in scopename:
                    self.inst_dict[visa_add] = self.DictValue(TypeEnum.osc, scopename)
                    self.osc.list_id.append(scopename)
                    self.osc.update = True
                else:
                    print("Please check new device: " + scopename)
                    self.inst_dict[visa_add] = 'unknown'
            except visa.VisaIOError:
                print("No instrument found: " + visa_add)
            except:
                print("Error Communicating with %s"%visa_add)

        # delete disconnected instrument
        if (self.inst_dict):
            for old_address in self.inst_dict.keys():
            # todo: fix RuntimeError: dictionary changed size during iteration
            # after unplugging usb
                if old_address not in info:
                    id = self.inst_dict[old_address].id
                    self.id_dict.pop(id)
                    # find the corresponding instrument and remove it from the corresponding list_id
                    if self.inst_dict[old_address].type == TypeEnum.osc:
                        self.osc.update = True
                        self.osc.list_id.remove(id)
                    elif self.inst_dict[old_address].type == TypeEnum.power:
                        self.power.update = True
                        self.power.list_id.remove(id)
                    elif self.inst_dict[old_address].type == TypeEnum.signal:
                        self.signal.update = True
                        self.signal.list_id.remove(id)
                    else:
                        print("unspecified instrument type.")
                    self.inst_dict.pop(old_address)
        return
    
    def getScopeName(self, visa_add:str):
        """
        open visa address as resource and ask the id of that instrument, close the used resource and return the instrument id
        """
        try: 
            resource = self.rm.open_resource(visa_add)
            scopename = resource.query("*IDN?")
            # close unused scope
            resource.close()
        except:
            if visa_add == 'USB0::0x0699::0x0527::C033493::INSTR': # osc
                scopename = 'TEKTRONIX,MSO46,C033493,CF:91.1CT FV:1.44.3.433'
            elif visa_add == 'USB0::0x1698::0x0837::001000005648::INSTR': # power supply
                scopename = 'CHROMA,62012P-80-60,03.30.1,05648'
            elif visa_add == 'USB0::0x0699::0x0358::C013019::INSTR': # signal generator
                scopename = 'TEKTRONIX,AFG31052,C013019,SCPI:99.0 FV:1.5.2'
            else:
                print("unknown device: %s"%visa_add)
                scopename = visa_add
        return scopename

    def connectDevice(self, visa_add, inst:Instrument):
        """
        connect selected devices and call open_resource to enable communication
        """
        try:
            inst.scope = self.rm.open_resource(visa_add)
            inst.setScope()
            return True
        except visa.VisaIOError:
            raise ValueError("No instrument found: " + visa_add)
        except:
            raise ValueError("Error Communicating with" + visa_add)

    def autosetSingleCurvePlot(self):
        self.connectDevice('USB0::0x0699::0x0527::C033493::INSTR') # test single function through hard coded visa address
        self.osc.autoset()
        self.osc.ioConfig()
        self.osc.acqConfig()
        self.osc.dataQuery()
        self.osc.retrieveAcqSetting()
        self.osc.errorChecking()
        self.osc.scope.close()

        self.osc.createScaledVectors()
        self.osc.plotting()
        self.osc.saveCurve('osc_curve')

    def outputAllChannelSignal(self):
        self.connectDevice('USB0::0x0699::0x0527::C033493::INSTR') # test single function through hard coded visa address
        self.osc.saveHardcopy('hardcopy')
        self.osc.saveWaveform('waveform')
        self.osc.errorChecking()
        self.osc.scope.close()

    def takeMeasurement(self):
        self.connectDevice('USB0::0x0699::0x0527::C033493::INSTR') # test single function through hard coded visa address
        self.osc.acquireMeasure()
        self.osc.scope.close()

    def controlPowerSupply(self):
        self.connectDevice('USB0::0x1698::0x0837::001000005648::INSTR') # test single instrument through hard coded visa address
        self.power.reset()
        self.power.setVoltage(7)
        self.power.setOutputOn()
        self.power.errorChecking()
        self.power.scope.close()

    def controlSignalGenerator(self):
        self.connectDevice('USB0::0x0699::0x0358::C013019::INSTR') # test single instrument through hard coded visa address
        self.signal.reset()
        self.signal.setPWMOutput()
        self.signal.setPWMDuty(50)
        self.signal.errorChecking()
        self.signal.scope.close()

class Oscilloscope(Instrument):
    def __init__(self):
        super().__init__()
        self.measure = {}
    
    def setScope(self):
        self.scope.timeout = 10000 # ms
        self.scope.encoding = 'latin_1'
        self.scope.read_termination = ''
        self.scope.write_termination = None
        self.scope.clear()
        super().printStartMsg("""
        ACTION:
        Connect probe to oscilloscope Channel 1 and the probe compensation signal.
        """)

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
        '''
        change the acquire:stopafter from default RUNSTOP to SINGLE/SEQ mode
        '''       
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
        if not os.path.exists(file_name):
            #  Create the directory with error handling
            try:
                dir = os.path.dirname(file_name)
                os.makedirs(dir)
                print(f"Directory '{dir}' created successfully")
            except FileExistsError:
                pass
            except Exception as e:
                print(f"An error occurred: {e}")
        
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

    def queryMeasurement(self, type = "MEAN", channel:Channel = Channel.vcc, mode:Literal["immed", "badge"] = "immed"):
        if mode == 'immed':
            self.scope.write("MEASUREMENT:IMMED:TYPE " + type)
            self.scope.write("MEASUREMENT:IMMED:SOURCE CH" + str(channel))
            res = self.scope.query("MEASUREMENT:IMMED:VALUE?")
            
        if mode == 'badge':
            meas_no = self.measure.get((channel, type))
            # stop the window
            self.scope.write('ACQUIRE:STATE STOP')
            self.scope.query("*OPC?") # wait for the badge to update
            res = self.scope.query("MEASUrement:MEAS%d:RESUlts:CURRentacq:MEAN?"%meas_no)
        
        if res == '9.91E+37\n': # the oscilloscope zero used this value
            res = '0'
        # log
        print("channel " + str(channel.value) + "(" + type + "): " + res) 
        return res
    
    # measureing fan speed in RPM through FG signal frequency
    def acquireMeasure(self):
        result = self.Measure()
        result.start_up_volt = float(self.queryMeasurement())
        # MEASUrement:CH<x>:REFLevels:ABSolute:FALLHigh?
        result.pwm = float(self.queryMeasurement("PDUTY", self.Channel.pwm))
        result.rpm = float(self.queryMeasurement("FREQUENCY", self.Channel.FG))
        
        result.max_current_on_steady = float(self.queryMeasurement("MAXIMUM", self.Channel.current))
        result.avg_op_current = float(self.queryMeasurement("MEAN", self.Channel.current))
        result.max_start_up_current = float(self.queryMeasurement("RMS", self.Channel.current))        
        result.min_current_on_steady = float(self.queryMeasurement("PK2Pk", self.Channel.current))
        return result

    def load_report(self, new_file_name):
        """
        open the current editing report, if not created yet, open the template as blank report, and create specified directory"
        """
        if os.path.exists(new_file_name):
            return openpyxl.load_workbook(new_file_name)
        else:
            #  Create the directory with error handling
            try:
                dir = os.path.dirname(new_file_name)
                os.makedirs(dir)
                print(f"Directory '{dir}' created successfully")
            except FileExistsError:
                print(f"Directory '{dir}' already exists")
            except Exception as e:
                print(f"An error occurred: {e}")
            
            return openpyxl.load_workbook('風扇樣品檢驗報告(for RD).xlsx')
    
    def metric_prefix(self, num: float, length:int = 5):
        '''
        formatting long number into numbers of thousands, with fixed total length
        '''
        if num < 1000.0 : # prevent math domain error
            return num
        prefix = int(floor(log(num, 1000)))
        original_value = num/(1000**prefix)
        int_len = len(str(int(original_value)))
        round_len = length - 1 - int_len  # including point
        new_value = np.round(original_value, round_len)
        print('metric_prefix converting %f to %f'%(num, new_value))
        return new_value * (1000**prefix)
    
    def measure_RPM_and_Curr(self, duty = 0.0, fg = 3, sample_no = 1, new_file_name = 'output', column_rpm=None, column_curr=None,
                             column_curr_max=None):
        """
        under pwm duty, measure current and corresponding RPM from calculation of FG signal frequency divided by FG quantity 
        :param column_rpm:          columns to fill in measured rpm value
        :type column_rpm:           List[str] | Tuple[str]
        :param column_curr:         columns to fill in measured current value
        :type column_curr:          List[str] | Tuple[str]
        :param column_curr_max      columns to fill in measured current max value
        :type column_curr_max       List[str] | Tuple[str]
        """
        curr = 'N/A'
        rpm = 'N/A'
        curr_max = 'N/A'
        wb = self.load_report(new_file_name)
        sheet = wb.active
        row = str(sample_no + 10)
        warn_msg = 'Please specify columns in a list, the result will not be saved'
        # measure rpm
        if column_rpm is not None:
            if type(column_rpm) not in (list, Tuple):
                warnings.warn(warn_msg)
            else: 
                rpm = self.metric_prefix(float(self.queryMeasurement("FREQUENCY", self.Channel.FG, 'badge'))) / fg * 60.0
                # incase the cell has already written on previous step before resuming from pause
                for col in column_rpm:
                    if (sheet[col + row].value == None):
                        sheet[col + row] = rpm
                
        # measure current
        if column_curr is not None:
            if type(column_curr) not in (list, Tuple):
                warnings.warn(warn_msg)
            else:
                curr = float(self.queryMeasurement(channel=self.Channel.current, mode='badge'))
                for col in column_curr:
                    if (sheet[col + row].value == None):
                        sheet[col + row] = curr        
        
        # measure max current
        if column_curr_max is not None:
            if type(column_curr_max) not in (list, Tuple):
                warnings.warn(warn_msg)
            else:
                curr_max = float(self.queryMeasurement("MAXIMUM", self.Channel.current, 'badge'))
                for col in column_curr_max:
                    if (sheet[col + row].value == None):
                        sheet[col + row] = curr_max
            
        wb.save(new_file_name)
        wb.close()

    def check_PWM_and_FG(self, sample_no = 1, new_file_name = 'output', column_pwm = None, column_fg = None):
        """
        check measured value > 0 and put 'V' at specified columns
        """
        pwm = 'N/A'
        fg = 'N/A'
        wb = self.load_report(new_file_name)
        sheet = wb.active
        row = str(sample_no + 10)
        warn_msg = 'Please specify columns in a list, the result will not be saved'
        
        # measure pwm
        if column_pwm is not None:
            if type(column_pwm) not in (list, Tuple):
                warnings.warn(warn_msg)
            else:
                pwm = float(self.queryMeasurement("PDUTY", self.Channel.pwm))
                # incase the cell has already written on previous step before resuming from pause
                for col in column_pwm:
                    if (sheet[col + row].value == None):
                        sheet[col + row] = 'V' if pwm > 0 else 'FAIL'
        # measure fg
        if column_fg is not None:
            if type(column_fg) not in (list, Tuple):
                warnings.warn(warn_msg)
            else:
                fg = float(self.queryMeasurement("FREQUENCY", self.Channel.FG))
                # incase the cell has already written on previous step before resuming from pause
                for col in column_fg:
                    if (sheet[col + row].value == None):
                        sheet[col + row] = 'V' if fg > 0 else 'FAIL'
            
        wb.save(new_file_name)
        wb.close()

    def setScale(self, type: Literal['H','V'] = 'V', channel: Channel = Channel.current, scale = 0.2):
        """
        :param type: 'H' set horizontal scale for numbers of seconds per division
                     'V' set vertical scale for numbers of voltage or ampere per division
        """
        if type == 'H':
            self.scope.write('HORizontal:SCAle ' + str(scale))
        elif type == 'V':
            self.scope.write('DISplay:WAVEView1:CH%d:VERTical:SCAle %s'%(channel.value, str(scale)))
        else:
            warnings.warn('setScale: wrong type: %s'%type)
    
    def setPosition(self, type: Literal['H', 'V'] = 'V', channel: Channel = Channel.current, position:float = -3.50):
        """
        Adjust the vertical position of the specific channel signal waveform
        :param type: 'V' set vertical position for specified channel
                     'H' set horizontal position 
        :param position: for vertical 5.00 is the top most and -5.00 is the bottom
                         for horizontal from 0 to ≈100 and is the position of the trigger point on the screen
                         (0 = left edge, 100 = right edge)
        """
        if type == 'V':
            self.scope.write('DISplay:WAVEView1:CH%d:VERTical:POSition %f'%(channel.value, position))
        elif type == 'H':
            self.scope.write('HORIZONTAL:POSITION %f'%position)
        else:
            warnings.warn('setPosition: wrong type: %s'%type)

    def addMeasurement(self, num:int = 1, channel: Channel = Channel.current, type:str = 'MEAN', reset:bool = False):
        '''
        Add measurement probe into a dictionary with responding number

        Parameters
        ----------
        num : int
            the index number of measurement type
        channel : Channel
            the index number of oscilloscope input channel
        type : str
            measurement type, check oscilloscope manual
        reset : bool
            if true, add oscilloscope badge for new measurement
        '''
        if reset:
            self.scope.write('MEASUrement:MEAS%d:TYPe %s'%(num, type))
            self.scope.write('MEASUrement:MEAS%d:SOUrce CH%d'%(num, channel.value))
            self.scope.query("*OPC?")
        self.measure[(channel, type)] = num
    
    def turnOn(self, channel: Channel):
        self.scope.write(':DISPLAY:WAVEVIEW1:CH%d:STATE 1'%channel.value)

    def setMeasurement(self):
        self.turnOn(self.Channel.vcc)
        self.turnOn(self.Channel.pwm)
        self.turnOn(self.Channel.FG)
        self.turnOn(self.Channel.current)
        self.scope.write('DISplay:WAVEView1:VIEWStyle OVERLAY')
        self.scope.write('HORIZONTAL:MODE MANUAL')
        self.scope.write('HORIZONTAL:MODE:SAMPLERATE 1e6')
        self.setScale('H', scale=1e-3)
        self.setScale('V', self.Channel.vcc, 5)
        self.setScale('V', self.Channel.pwm, 2)
        self.setScale('V', self.Channel.FG, 2)
        self.setScale('V', self.Channel.current, 1)
        self.setPosition('V', self.Channel.vcc, 2.0)
        self.setPosition('V', self.Channel.pwm, 1.5)
        self.setPosition('V', self.Channel.FG, -1.5)
        self.setPosition('V', self.Channel.current, -3.7)
        self.setPosition('H', position=20)
        self.scope.write('TRIGGER:A:MODE AUTO')

    def setTrigger(self, channel: Channel = Channel.current, level:float = 2.0):
        self.scope.write('TRIGGER:A:MODE NORMAL')
        self.scope.write('TRIGGER:A:TYPe EDGE')
        self.scope.write('TRIGger:A:EDGE:SOUrce CH%d'%channel.value)
        self.scope.write('TRIGGER:A:LEVEL:CH%d '%channel.value + str(level))
        self.scope.write('TRIGGER:A:EDGE:SLOpe RISe')
        self.scope.query("*OPC?")

    def readImage(self, file_name:str = 'max_current'):
        #self.scope.query("*OPC?")  #Make sure the image has been saved before trying to read the file
        
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

class PowerSupply(Instrument):
    def __init__(self):
        super().__init__()

    def setScope(self):
        self.scope.read_termination = '\r\n'
        self.scope.query_termination = '\r\n'
        self.scope.write_termination = '\r\n'
        super().printStartMsg("""
        Power supply ready for remote control.
        """)

    def setVoltage(self, volt):
        self.scope.write("SOUR:VOLT " + str(volt))

    def setCurrent(self, cur):
        self.scope.write("SOUR:CURR " + str(cur))

    def setOutputOn(self):
        self.scope.write("CONFIgure:OUTPut ON")
    
    def setOutputOff(self):
        self.scope.write("CONFIgure:OUTPut OFF")

class SignalGenerator(Instrument):
    def __init__(self):
        super().__init__()
    
    def setScope(self):
        self.scope.read_termination = '\n'
        self.scope.write_termination = None
        self.scope.clear()
        super().printStartMsg("""
        Signal generator ready for remote control.
        """)

    def setPWMOutput(self):
        self.scope.write('SOURCE1:FUNCTION:SHAPE PULS')
        #self.scope.write('SOURce1:PWM:STATe ON')
        self.scope.write('SOURce1:PWM:SOURce INTernal')
        self.scope.write('FREQuency 25E3')
        self.scope.write('OUTPut1:IMPedance INFinity')
        self.scope.write('SOURce1:PWM:INTernal:FUNCtion SQUare')
        self.scope.write('SOURce1:VOLTage:LEVel:IMMediate:AMPLitude 5VPP')
        self.scope.write('SOURce1:VOLTage:LEVel:IMMediate:OFFSet 2.5V')
    
    def setPWMDuty(self, duty = 5.0):
        if (duty > 99.25):
            duty = 99.981
        if (duty < 1.0):
            duty = 0.025
        self.scope.write("SOURce1:PULSe:DCYCle " + str(duty))
        # offset 2.5V
        r = self.scope.query('*opc?') # sync

    def setOutputOn(self):
        self.scope.write("OUTPut1:STATe ON")