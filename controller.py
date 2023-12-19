import model
import view

class Controller:
    def __init__(self, model:model.Model, view:view.View) -> None:
        self.model = model
        self.view = view

    def start(self):
        """
        Start testing
        """
        try:
            # run all test
            self.model.runTest()
            # show success message
            self.view.show_success('Test completed.')
        except ValueError as error:
            # show an error message
            self.view.show_error(error)
    
    def deviceReady(self, osc_id: str, power_id:str, signal_id:str):
        """
        check if selected device is online
        """
        if self.model.connectDevice(self.model.id_dict[osc_id], self.model.osc) and\
           self.model.connectDevice(self.model.id_dict[power_id], self.model.power) and\
           self.model.connectDevice(self.model.id_dict[signal_id], self.model.signal):
            return True
        else:
            return False
    
    def selectDevices(self):
        self.model.listDevices()
        self.updatDeviceList(self.model.osc, 'osc')
        self.updatDeviceList(self.model.signal, 'signal')
        self.updatDeviceList(self.model.power, 'power')
    
    def updatDeviceList(self, inst:model.Instrument, type:str):
        """
        update the dropdown list of instrument of the app, if there is only 1 instrument of that type, select it automatically
        """
        if inst.update == True:
            self.view.window[type].update(values = inst.list_id)
            inst.update = False
            if len(inst.list_id) == 1:
                self.view.window[type].update(value = inst.list_id[0])

import time
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
            if event == 'Start':
                if self._controller.deviceReady(values['osc'], values['power'], values['signal']) == False:
                    print( "popup rewire request")
                # change the "status" element to be the value of "sample number" element
                self._view.window['Status'].update("Start testing sample number " + str(values['SampleNumber']) + "...")
        self._view.window.close()

if __name__ == '__main__':
    app = App()
    app.mainloop()    
        