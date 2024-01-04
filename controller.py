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
        self.start_time = 0
        self.last_job = None

    def start(self, sample_no:int, dir:str):
        """
        Start testing, prepare a priority queue to store the test processes
        """
        try:
            # prepare a priority queue to store the test processes
            self.sample_no = sample_no
            self.new_file_name = dir + '/report' if dir else 'report'
            self.initialList()
            self.start_time = time.process_time()
            
        except ValueError as error:
            # show an error message
            self.view.show_error(error)

    def runTest(self):
        """
        when the state is testing, execute job to update the communication orders periodically with devices
        """
        now = time.process_time()
        if len(self.job_list) > 0:
            job = self.job_list[0]
            if now - self.start_time > job[0]:
                res = job[1]
                self.last_job = self.job_list.pop(0)
    
    def initialList(self):
        """
        test actions are store in list of tuple(int(trigger time in sec), action)
        steps:
        * 0 s: reset power supply, signal generator
        * 0 s: power supply voltage 12V, signal generator pwm 0
        * 10 s: measure pwm / rpm, write at column E / F
        * 10 s: set signal generator pwm 50
        * 20 s: measure pwm / rpm, write at column G / H
        * 20 s: set signal generator pwm 100
        * 30 s: measure pwm / rpm, write at column I / J
        * (to be determined test process after column K)
        * show success message
        """
        self.job_list.append((0, self.model.power.reset))
        self.job_list.append((0, self.model.signal.reset))
        self.job_list.append((0, self.model.power.setVoltage(12)))
        self.job_list.append((0, self.model.signal.setPWMOutput))
        self.job_list.append((0, self.model.signal.setPWMDuty(0)))
        self.job_list.append((1, self.model.power.setOutputOn))
        self.job_list.append((10, self.model.osc.measure_RPM_under_PWM(0, 3, self.sample_no, self.new_file_name, 'E', 'F')))
        self.job_list.append((10, self.model.signal.setPWMDuty(50)))
        self.job_list.append((20, self.model.osc.measure_RPM_under_PWM(50, 3, self.sample_no, self.new_file_name, 'G', 'H')))
        self.job_list.append((20, self.model.signal.setPWMDuty(100)))
        self.job_list.append((30, self.model.osc.measure_RPM_under_PWM(100, 3, self.sample_no, self.new_file_name, 'I', 'J')))
        self.job_list.append((30, self.model.power.setOutputOff))
        self.job_list.append((30, self.view.show_success('Test completed.')))

    def resumeTest(self):
        """
        resume from pause
        """
        self.start_time = time.process_time()
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
        update the dropdown list of instrument of the app, if there is only 1 instrument of that type, select it automatically
        """
        if inst.update == True:
            self.view.window[type].update(values = inst.list_id)
            inst.update = False
            if len(inst.list_id) == 1:
                self.view.window[type].update(value = inst.list_id[0])

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
            print(event, values)
            # --------- Display updates in window --------
            self._controller.selectDevices()

            if event == view.sg.WIN_CLOSED or event == 'Quit':
                break
            self._view.fsm(event, values)
            if self._view.state == self._view.State.Testing:
                self._controller.runTest()
        self._view.window.close()

if __name__ == '__main__':
    app = App()
    app.mainloop()    
        