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
    def deviceReady(self):
        return True

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
            #self._model.connectDevices()
            # --------- Display updates in window --------
            # scan dictionary and get appended str
            str_power = self.findDevice(model.Model.Device.power)
            str_signal = self.findDevice(model.Model.Device.signal)
            str_osc = self.findDevice(model.Model.Device.osc)
            self._view.window['power'].update('{}'.format(str_power)))
            self._view.window['signal'].update('{}'.format(str_signal))
            self._view.window['osc'].update('{}'.format(str_osc))
            if event == view.sg.WIN_CLOSED or event == 'Quit':
                break
            if event == 'Start':
                if self._controller.deviceReady() == False:
                    print( "popup rewire request")
                # change the "status" element to be the value of "sample number" element
                self._view.window['Status'].update("Start testing sample number " + str(values['SampleNumber']) + "...")
        self._view.window.close()

if __name__ == '__main__':
    app = App()
    app.mainloop()    
        