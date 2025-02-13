import model
import view
import time
import argparse

class Controller:
    def __init__(self, model:model.Model, view:view.View) -> None:
        self.model = model
        self.view = view
        self.job_list = list()
        self.sample_no = 0
        self.new_file_name = ''
        self.new_file_dir = ''
        self.start_time = 0
        self.last_job = None
        self.scale_list = [ScaleSetting(12.0, 7.0,    13.2, 0.2, 1, 1, 1, 1, 1, 1),
                           ScaleSetting(12.0, 7.0,    13.2, 0.2, 2, 2, 2, 2, 2, 1),
                           ScaleSetting(12.0, 7.0,    13.2, 0.2, 5, 5, 5, 5, 5, 2),
                           ScaleSetting(12.0, 9.0,    13.2, 0.2, 5, 5, 5, 5, 5, 2),
                           ScaleSetting(12.0, 10.8,   13.2, 0.2, 5, 5, 5, 5, 5, 2),
                           ScaleSetting(48.0, 36.0,   60.0, 0.2, 1, 1, 1, 1, 1, 1)]
        self.scale_no = 0

    def start(self, sample_no:int, dir:str):
        """
        Start testing, prepare a priority queue to store the test processes
        """
        try:
            # prepare a priority queue to store the test processes
            self.sample_no = sample_no
            self.new_file_name = dir
            self.new_file_dir = model.os.path.dirname(dir) + '/'
            self.initialList()
            self.start_time = time.perf_counter()
            
        except ValueError as error:
            # show an error message
            self.view.show_error(error)

    def pause(self):
        """
        when pause button is clicked, stop power supply output
        """
        self.model.power.setOutputOff()

    def stop(self):
        """
        when stop button is clicked, stop power supply output, clear the job list
        """
        self.model.power.setOutputOff()
        self.job_list.clear()
        # in the end of the test, add an auto stop, change the state machine, for a new round to start
        self.view.state = view.View.State.Stopped

    def runTest(self):
        """
        when the state is testing, execute job to update the communication orders periodically with devices
        """
        now = time.perf_counter()
        if len(self.job_list) > 0:
            job = self.job_list[0]
            if now - self.start_time > job[0]:
                self.start_time = now
                print("doing task: "+ job[1].__qualname__)
                self.last_job = self.job_list.pop(0)
                if len(job) > 2:
                    job[1](*job[2:])
                else:
                    job[1]()
    
    def getSampleNo(self):
        return self.sample_no
    
    def initialList(self):
        """
        test actions are store in list of tuple(int(trigger time in sec after last step), action_function, action_parameters: list())
        steps:
        跳出提醒：ch1 vcc, ch2 pwm, ch3 fg, ch4 curr
        詢問spec 0% 50% 100%的RPM. CURR
        signal: 設定方波continueous offset 2.5v load high z
        osc: 設定waveformview overlay horizontal 1ms/div SR 1MS/s 13.2V horizontal 1s/div
        1.  設定power voltage 12V, 5A, signal generator pwm 100
            generator ouput on channel 1
            10s後
            記錄RPM (freq*30(需要轉換文字的k為1000))H欄, CURRENT(MEAN) I&N欄, CURRENT(MAX) M欄
        2.  設定signal generator pwm 50
            generator ouput on channel 1
            記錄RPM F欄, CURRENT(MEAN) G欄
        3.  設定signal generator pwm 0
            generator ouput on channel 1
            記錄RPM D欄, CURRENT(MEAN) E欄
        4.  設定power voltage 7V, 5A, signal generator pwm 100
            freq > 0
            確認有RPM，記錄L欄打勾
            確認有PWM及FG訊號，記錄K&R欄打勾
            power off
            詢問是否做max startup, 按確定後開始10s後記錄
        5.  設定power voltage 13.2V, signal generator pwm100
            停下來
            詢問是否做luck, 按確定後開始10s後記錄
            10s,記錄CURRENT(MAX) P欄
        * show success message
        """
        self.job_list.append((0, self.model.power.reset))
        self.job_list.append((0, self.model.signal.reset))
        self.job_list.append((0, self.setupDisplay, 'Reset Measurement badge?'))
        self.job_list.append((0, self.model.power.setVoltage, self.scale_list[self.scale_no].ratedV))
        self.job_list.append((0, self.model.power.setCurrent, 10))
        self.job_list.append((0, self.model.signal.setPWMOutput))
        self.job_list.append((0, self.meanRPMandCurrentOfPWM, 100, 2, True, '100_pwm', ['H'], ['I','N'], ['M']))
        self.job_list.append((0, self.meanRPMandCurrentOfPWM, 50, 2, True, '50_pwm', ['F'], ['G']))
        self.job_list.append((0, self.meanRPMandCurrentOfPWM, 0, 2, True, '0_pwm', ['D'], ['E']))
        self.job_list.append((0, self.lowVoltage, None, ['L']))
        self.job_list.append((0, self.maxCurrent, None, ['O'], True, 'max_start_up_cur', self.scale_list[self.scale_no].start))
        self.job_list.append((0, self.maxCurrent, 'Measure Max. Lock Current?', ['P'], True, 'lock', self.scale_list[self.scale_no].lock))
        self.job_list.append((0, self.writeSpecFromGUI, ['D','E','F','G','H','I']))
        self.job_list.append((0, self.view.show_success,'Sample No.%d Test completed.'%self.sample_no))
        self.job_list.append((0, self.stop))
        
    def resumeTest(self):
        """
        resume from pause
        """
        self.start_time = time.perf_counter()
        self.job_list.insert(0, self.last_job)

    def deviceReady(self, osc_id: str, power_id:str, signal_id:str):
        """
        check if selected device is online
        """
        res = True
        try:
            self.model.connectDevice(self.model.id_dict[osc_id], self.model.osc)
        except ValueError as e:
            self.view.show_error(e)
            res = False
        try:   
            self.model.connectDevice(self.model.id_dict[power_id], self.model.power)
        except ValueError as e:
            self.view.show_error(e)
            res = False
        try:
            self.model.connectDevice(self.model.id_dict[signal_id], self.model.signal)
        except ValueError as e:
            self.view.show_error(e)
            res = False
        return res
    
    def selectDevices(self):
        self.model.listDevices()
        self.updateDeviceList(self.model.osc, 'osc')
        self.updateDeviceList(self.model.signal, 'signal')
        self.updateDeviceList(self.model.power, 'power')
    
    def updateDeviceList(self, inst:model.Instrument, type:str):
        """
        if a oscilloscope is connected, show wiring note to make sure all channel are correctly wired.
        update the dropdown list of instrument of the app, if there is only 1 instrument of that type, select it automatically
        """
        if inst.update == True:
            self.view.window[type].update(values = inst.list_id)
            inst.update = False
            if type == 'osc':
                self.view.show_success('Oscilloscope ready for remote control')
                view.sg.popup_ok("Check signal generator wiring:\n ch1\t vcc,\n ch2\t pwm,\n ch3\t fg,\n ch4\t curr", keep_on_top=True)
            if len(inst.list_id) == 1:
                self.view.window[type].update(value = inst.list_id[0])

    def meanRPMandCurrentOfPWM(self, pwm:float = 0.0, fg:int = 2, hard_copy = False, hard_copy_file_name = 'hard_copy',
                                     col_rpm = None, col_curr = None, col_curr_max = None):
        self.model.signal.setPWMDuty(pwm)
        self.model.signal.setOutputOn()
        self.model.power.setOutputOn()
        if pwm == 0.0:
            self.model.osc.setScale(scale=self.scale_list[self.scale_no].duty0)
        elif pwm == 50.0:
            self.model.osc.setScale(scale=self.scale_list[self.scale_no].duty50)
        elif pwm == 100.0:
            self.model.osc.setScale(scale=self.scale_list[self.scale_no].duty100)
            # delete meas1 and add new measurement
            self.model.osc.scope.write('MEASUREMENT:DELETE "MEAS1"')
            self.model.osc.addMeasurement(9, self.model.osc.Channel.current, 'PDUTY', reset = True)

        self.model.osc.scope.write('ACQUIRE:STATE RUN')
        # check signal channel has value
        if pwm == 50.0:
            self.job_list.insert(0, (1, self.model.osc.check_PWM_and_FG, self.sample_no, self.new_file_name, ['K'], ['R']))
        
        self.job_list.insert(0, (10, self.model.osc.measure_RPM_and_Curr, pwm, fg, self.sample_no, self.new_file_name, col_rpm, col_curr, col_curr_max))
        # add meas1 back
        if pwm == 100.0:
            self.job_list.insert(1, (0, self.model.osc.scope.write, 'MEASUREMENT:DELETE "MEAS9"'))
            self.job_list.insert(2, (0, self.model.osc.addMeasurement, 1, self.model.osc.Channel.vcc, 'TOP', True))

        if hard_copy:
            hard_copy_file_name = 's%d/%s_s%d'%(self.getSampleNo(), hard_copy_file_name, self.getSampleNo())
            self.job_list.insert(1, (0, self.model.osc.saveHardcopy, self.new_file_dir + hard_copy_file_name))
        
    def lowVoltage(self, col_pwm = None, col_fg = None):
        self.model.power.setVoltage(self.scale_list[self.scale_no].lowV)
        self.model.power.setCurrent(10)
        self.model.signal.setPWMDuty(10)
        self.model.signal.setOutputOn()
        self.model.power.setOutputOn()
        self.model.osc.setScale(scale=self.scale_list[self.scale_no].low)
        self.model.osc.scope.write('ACQUIRE:STATE RUN')
        self.job_list.insert(0, (3, self.model.osc.check_PWM_and_FG, self.sample_no, self.new_file_name, col_pwm, col_fg))
        self.job_list.insert(1, (0, self.model.power.setOutputOff))
    
    def writeSpecFromGUI(self, cols):
        '''
        write spec from user input GUI box
        write low voltage spec from user option
        '''
        wb = self.model.osc.load_report(self.new_file_name)
        sheet = wb.active
        spec = self.view.getSpecValue()
        row = '10'
        for s, col in zip(spec, cols):
            if (sheet[col + row].value == None):
                sheet[col + row] = s
        
        if sheet['L' + row].value == None:
            sheet['L' + row] = '%s V'%self.scale_list[self.scale_no].lowV
        wb.save(self.new_file_name)
        wb.close()

    def setupDisplay(self, msg = 'msg'):
        self.model.osc.setMeasurement()
        res = True if view.sg.popup_yes_no(msg, keep_on_top=True) == 'Yes' else False
        # add measurements
        if res:
            self.model.osc.scope.write('MEASUrement:DELETEALL')
        self.model.osc.addMeasurement(1, self.model.osc.Channel.vcc, 'TOP', reset = res)
        self.model.osc.addMeasurement(2, self.model.osc.Channel.vcc, 'MEAN', reset = res)
        self.model.osc.addMeasurement(3, self.model.osc.Channel.pwm, 'PDUTY', reset = res)
        self.model.osc.addMeasurement(4, self.model.osc.Channel.FG, 'FREQUENCY', reset = res)
        self.model.osc.addMeasurement(5, self.model.osc.Channel.current, 'MAXIMUM', reset = res)
        self.model.osc.addMeasurement(6, self.model.osc.Channel.current, 'MEAN', reset = res)
        self.model.osc.addMeasurement(7, self.model.osc.Channel.current, 'RMS', reset = res)
        self.model.osc.addMeasurement(8, self.model.osc.Channel.current, 'PK2PK', reset = res)

    def maxCurrent(self, popup_msg = None, col=None, hard_copy = False, hard_copy_file_name:str = 'hard_copy', scale = 1.0):
        button = view.sg.popup_yes_no(popup_msg, keep_on_top=True) if popup_msg is not None else 'Yes'

        if button != 'Yes':
            return None
        else:
            self.model.power.setVoltage(self.scale_list[self.scale_no].highV)
            self.model.power.setCurrent(10)
            self.model.signal.setPWMDuty(100)
            self.model.osc.setScale(type='H', scale=self.scale_list[self.scale_no].max_curr_horizontal)
            self.model.osc.setScale(scale = scale)
            self.model.osc.scope.write('acquire:state 0') # stop
            self.model.osc.setTrigger(self.model.osc.Channel.current, 2.0)
            self.model.osc.scope.write('acquire:stopafter SEQUENCE') # single
            self.model.osc.scope.write('acquire:state 1') # start
            while(self.model.osc.scope.query('TRIGger:STATE?') != 'READY\n'):
                time.sleep(1)
            # ready for test
            self.job_list.insert(0, (0, self.model.signal.setOutputOn))
            self.job_list.insert(1, (0, self.model.power.setOutputOn))
            after_sec = 7 * self.scale_list[self.scale_no].max_curr_horizontal
            # make sure the sequence data has acquired
            # use *opc? to ensure the output display are shown
            self.job_list.insert(2, (after_sec, self.model.osc.scope.query, '*opc?'))
            self.job_list.insert(3, (0, self.model.power.setOutputOff))
            self.job_list.insert(4, (0, self.model.osc.measure_RPM_and_Curr, 100, 2, self.sample_no, self.new_file_name, None, None, col))
            if hard_copy:
                hard_copy_file_name = 's%d/%s_s%d'%(self.getSampleNo(), hard_copy_file_name, self.getSampleNo())
                self.job_list.insert(5, (0, self.model.osc.saveHardcopy, self.new_file_dir + hard_copy_file_name))

class ScaleSetting:
    def __init__(self, ratedV: float, lowV:float, highV:float,
                 duty0:float, duty50:float, duty100:float, 
                 start:float, lock:float, low:float,
                 max_curr_horizontal: float) -> None:
        # voltage spec
        self.ratedV = ratedV
        self.lowV = lowV
        self.highV = highV
        # vertical scale of current channel (A/div) of duty test
        self.duty0 = duty0 
        self.duty50 = duty50 
        self.duty100 = duty100
         # horizontal scale of time (sec/div) of max current test
        self.max_curr_horizontal = max_curr_horizontal
        # vertical scale of current channel (A/div) of start/lock/low voltage test
        self.start = start
        self.lock = lock
        self.low = low
    
    def getName(self) -> str:
        return '%.1f\t ~ %.1f V  %i A/div'%(self.lowV, self.highV, self.start) 

class App():
    def __init__(self) -> None:
        parser = argparse.ArgumentParser(description="add command-line arguments")
        parser.add_argument('-d', '--dummy', action='store_true', help='dummy device ids for testing without connecting devices')
        parser.add_argument('-c', '--cprint', action='store_true', help='showing cprint message on GUI')
        parser.add_argument('-s', '--stdout', action='store_true', help='showing stdout message on GUI')
        
        args = parser.parse_args()
        print(args)
        self._model = model.Model(dummy=args.dummy)
        self._view = view.View(cprint=args.cprint, stdout=args.stdout, default_filename=self.dir_format())
        self._controller = Controller(self._model, self._view)
        self._view.set_controller(self._controller)
    
    def dir_format(self):
        t = time.localtime()
        dir = './test%i%02i%02i_%02i%02i/report'%(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min)
        return dir

    def findDevice(self):
        return ""

    def mainloop(self):
        while (True):
            # --------- Read and update window --------
            event, values = self._view.window.read(timeout=1000)
            if event != '__TIMEOUT__' and \
               event != '-SEC1_KEY--BUTTON-' and event != '-SEC1_KEY--TITLE-' and \
               event != '-SEC2_KEY--BUTTON-' and event != '-SEC2_KEY--TITLE-':
                print(event)
            # --------- Display updates in window --------
            self._controller.selectDevices()

            if event == view.sg.WIN_CLOSED or event == 'Quit':
                break

            self._view.changeCollapsibleSection(event, self._view.sec1_key)
            self._view.changeCollapsibleSection(event, self._view.sec2_key)
            self._view.fsm(event, values)
            if self._view.state == self._view.State.Testing:
                self._controller.runTest()
        self._view.window.close()

if __name__ == '__main__':
    app = App()
    app.mainloop()    
        