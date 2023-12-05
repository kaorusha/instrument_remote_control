import model
import view

class Controller:
    def __init__(self, model, view) -> None:
        self.model = model
        self.view = view

    def start(self):
        """
        Start testing
        """
        try:
            # run all test
            self.model.test()
            # show success message
            self.view.show_success('Test completed.')
        except ValueError as error:
            # show an error message
            self.view.show_error(error)

import time
class App():
    def __init__(self) -> None:
        self._model = model.Model()
        self._view = view.View()
        self._controller = Controller(self._model, self._view)
        self._view.set_controller(self._controller)

    def mainloop(self):
        while (True):
            # --------- Read and update window --------
            event, values = self._view.window.read(timeout=1000)
            # print(event, values)
            id = self._model.device # todo: call selectmodel()
            # --------- Display updates in window --------
            self._view.window['power'].update('{}'.format(id.power))
            self._view.window['signal'].update('{}'.format(id.signal))
            self._view.window['osc'].update('{}'.format(id.osc))
            if event == view.sg.WIN_CLOSED or event == 'Cancel':
                break
            if event == 'Start':
                # change the "status" element to be the value of "sample number" element
                self._view.window['Status'].update("Start testing sample number " + str(values['SampleNumber']) + "...")
        self._view.window.close()

if __name__ == '__main__':
    app = App()
    app.mainloop()    
        