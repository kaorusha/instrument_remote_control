import model
import view
import time

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
        self.job_list.append((0, self.model.osc.setMeasurement))
        self.job_list.append((0, self.model.power.setVoltage, 12))
        self.job_list.append((0, self.model.power.setCurrent, 5))
        self.job_list.append((0, self.model.signal.setPWMOutput))
        self.job_list.append((0, self.meanRPMandCurrentOfPWM, 100, 2, True, '100_pwm', ['H'], ['I','N'], ['M']))
        self.job_list.append((0, self.meanRPMandCurrentOfPWM, 50, 2, True, '50_pwm', ['F'], ['G']))
        self.job_list.append((0, self.meanRPMandCurrentOfPWM, 0, 2, True, '0_pwm', ['D'], ['E']))
        self.job_list.append((0, self.model.power.setVoltage, 7))
        self.job_list.append((0, self.model.power.setCurrent, 5))
        self.job_list.append((0, self.model.signal.setPWMDuty, 100))
        self.job_list.append((0, self.model.signal.setOutputOn))
        self.job_list.append((0, self.model.osc.scope.write, 'ACQUIRE:STATE RUN'))
        self.job_list.append((2, self.model.osc.check_PWM_and_FG, self.sample_no, self.new_file_name, ['K'], ['L', 'R']))
        self.job_list.append((0, self.model.power.setOutputOff))
        self.job_list.append((0, self.maxCurrentTestAfterPopup, 'Measure Max. Start up Current?', ['O'], 7, True, 'max_start_up_cur'))
        self.job_list.append((0, self.maxCurrentTestAfterPopup, 'Measure Max. Lock Current?', ['P'], 7, True, 'lock'))
        self.job_list.append((0, self.view.show_success,'Test completed.'))

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
                view.sg.popup_ok("Check signal generator wiring:\n ch1\t vcc,\n ch2\t pwm,\n ch3\t fg,\n ch4\t curr", keep_on_top=True)
            if len(inst.list_id) == 1:
                self.view.window[type].update(value = inst.list_id[0])

    def meanRPMandCurrentOfPWM(self, pwm:float = 0.0, fg:int = 2, hard_copy = False, hard_copy_file_name = 'hard_copy',
                                     col_rpm = None, col_curr = None, col_curr_max = None):
        self.model.signal.setPWMDuty(pwm)
        self.model.signal.setOutputOn()
        self.model.power.setOutputOn()
        if pwm == 0.0:
            self.model.osc.setScale()
        self.model.osc.scope.write('ACQUIRE:STATE RUN')
        self.job_list.insert(0, (10, self.model.osc.measure_RPM_and_Curr, pwm, fg, self.sample_no, self.new_file_name, col_rpm, col_curr, col_curr_max))
        if hard_copy:
            self.job_list.insert(1, (0, self.model.osc.saveHardcopy, self.new_file_dir + hard_copy_file_name))
    
    def maxCurrentTestAfterPopup(self, msg = 'msg', col=None, after_sec=8, hard_copy = False, hard_copy_file_name:str = 'hard_copy'):
        button = view.sg.popup_yes_no(msg, keep_on_top=True)

        if button != 'Yes':
            return None
        else:
            self.model.power.setVoltage(13.2)
            self.model.power.setCurrent(5)
            self.model.signal.setPWMDuty(100)
            self.model.osc.setScale('H', self.model.osc.Channel.current, '1')
            self.model.osc.setScale('V', self.model.osc.Channel.current, '1')
            self.model.osc.setPosition('V', self.model.osc.Channel.current, -4.5)
            self.model.osc.scope.write('acquire:state 0') # stop
            self.model.osc.setTrigger(self.model.osc.Channel.current, 2.0)
            self.model.osc.scope.write('acquire:stopafter SEQUENCE') # single
            self.model.osc.scope.write('acquire:state 1') # start
            while(self.model.osc.scope.query('TRIGger:STATE?') != 'READY\n'):
                time.sleep(1)
            # ready for test
            self.job_list.insert(0, (0, self.model.signal.setOutputOn))
            self.job_list.insert(1, (0, self.model.power.setOutputOn))
            # make sure the sequence data has acquired
            self.job_list.insert(2, (after_sec, self.model.osc.scope.query, '*opc?'))
            self.job_list.insert(3, (0, self.model.osc.measure_RPM_and_Curr, 100, 2, self.sample_no, self.new_file_name, None, None, col))
            self.job_list.insert(4, (0, self.model.power.setOutputOff))
            if hard_copy:
                self.job_list.insert(5, (0, self.model.osc.saveHardcopy, self.new_file_dir + hard_copy_file_name))

class App():
    def __init__(self) -> None:
        self._model = model.Model()
        self._view = view.View()
        self._controller = Controller(self._model, self._view)
        self._view.set_controller(self._controller)
    
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
        