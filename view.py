"""
Helps easily create GUIs for PyVISA instrumentation.

Provides class InstrumentOption which encapsulates information about a particular GUI option,
and function open_gui_return_input which takes in a list of InstrumentOptions, creates a GUI,
and returns the user's input when the GUI submit button is pressed.

GUI is formatted as a singular column of instrument options, with each option input presented 
as either a text box or check box.

Typical usage example:
    instrument_options = [
            InstrumentOption("High Current", "high_current", "0.001"),
            InstrumentOption("Filter Type", "filter_type"),
            InstrumentOption("Use Low to Earth", "lowToEarth_on", False, True),
            InstrumentOption("Use Input Capacitor", "inputCap_on", False, True),
        ]

    messages = "Message to display in GUI"

    parameters = open_gui_return_input(
        instrument_options, messages, "saved_parameters.txt"
    )


    Copyright 2023 Tektronix, Inc.                      
    See www.tek.com/sample-license for licensing terms. 

"""

import PySimpleGUI as sg
from enum import Enum

class InstrumentOption:
    """Class that encapsulates information about instrument parameters to present on GUI.

    A list of these can be passed to function open_gui_return_input() in order to automatically
    generate a PySimpleGUI GUI window for getting instrument parameters from a user.

    Attributes:
        option_label: A string indicating the option name displayed in the GUI.
        gui_key: The key (string) used to retrieve the input value from PySimpleGUI.
        default_value: A string (or bool if is_bool is True) indicating the default GUI value.
        is_bool: A boolean indicating if the GUI option should be a text field or boolean checkbox.
    """

    def __init__(
        self,
        label: str,
        gui_key: str,
        default_value="0",
        is_bool: bool = False,
        tooltip: str = "",
        permanent_tooltip=False,
    ) -> None:
        self.label = label
        self.gui_key = gui_key
        self.default_value = default_value
        self.is_bool = is_bool
        self.tooltip = tooltip
        self.permanent_tooltip = permanent_tooltip

    def py_simple_gui_row(self, label_length: int = 30):
        """Returns a list corresponding to a PySimpleGUI row for the instrument option input"""
        sg_option_label = sg.Text(
            text=self.label, size=label_length, justification="right"
        )
        tooltip_with_label = self.label
        if self.tooltip is not "":
            tooltip_with_label += ": " + self.tooltip

        if self.permanent_tooltip:
            sg_text_note = sg.Text(
                text=self.tooltip,
                expand_x=True,
                font="Arial 10 italic",
                justification="left",
            )
        else:
            sg_text_note = sg.Text(
                text="",
                expand_x=True,
                font="Arial 10 italic",
                justification="left",
            )
        if self.is_bool:
            return [
                sg_option_label,
                sg.Checkbox(
                    text="",
                    tooltip=tooltip_with_label,
                    expand_x=True,
                    default=self.default_value,
                    key=self.gui_key,
                ),
                sg_text_note,
            ]
        else:
            return [
                sg_option_label,
                sg.Input(
                    tooltip=tooltip_with_label,
                    default_text=self.default_value,
                    size=10,
                    key=self.gui_key,
                ),
                sg_text_note,
            ]


def open_gui_return_input(
    instrument_options, messages: str, saved_parameters_filename: str
):
    """Create GUI window with options specified by instrument_options, return input on user submit.

    Args:
        instrument_options (object): List of InstrumentOption objects to be added to GUI.

        messages (str): String that will be displayed as a note on the GUI window.

        saved_parameters_filename (str): Path name of file where user parameters will be saved
            to and reloaded from.

    Returns:
        (dict): Dictionary containing instrument parameters entered in the GUI, with keys determined
            by the gui_key attributes of the InstrumentOption objects in instrument_options.
    """
    # Open the parameters file or create one
    try:
        with open(saved_parameters_filename, "r", encoding="utf-8") as file:
            saved_params = file.read().splitlines()
    except FileNotFoundError:
        with open(saved_parameters_filename, "x", encoding="utf-8") as file:
            saved_params = []

    # Set GUI parameter default values to previously saved parameters
    if len(saved_params) == len(instrument_options):
        for i, value in enumerate(saved_params):
            if instrument_options[i].is_bool:
                instrument_options[i].default_value = True if value == "True" else False
            else:
                instrument_options[i].default_value = value

    # Get max length of any instrument_option label, used for alignment
    max_label_length = max(len(option.label) for option in instrument_options)

    # Iterate over instrument options and generate row in for each in column 1
    col1 = [
        option.py_simple_gui_row(label_length=max_label_length)
        for option in instrument_options
    ]

    # Create second column containing additional messages/notes
    col2 = [
        [
            sg.Text(
                messages,
                justification="center",
            )
        ]
    ]

    layout = [
        [sg.Column(col1, element_justification="right"), sg.Column(col2)],
        [sg.Submit("Run Test")],
    ]

    # Create the GUI window
    window = sg.Window(
        "Instrument Parameter GUI", layout, element_justification="center"
    )

    event, parameters = window.read()

    if event is not None:
        with open(saved_parameters_filename, "w", encoding="utf-8") as file:
            for value in parameters.values():
                file.write(str(value) + "\n")

    window.close()
    return parameters

class View():
    def __init__(self) -> None:
        sg.theme('Default 1')
        sg.set_options(element_padding=(0, 0))
        layout = [[sg.Text('Connected device:')],
                [sg.Text('Power Supply:', size=(15,1)), sg.Combo(key='power', values={}, size=(50 ,1))],
                [sg.Text('Signal Generator:', size=(15,1)), sg.Combo(key='signal', values={}, size=(50 ,1))],
                [sg.Text('Oscilloscope:', size=(15,1)), sg.Combo(key='osc', values={}, size=(50 ,1))],
                [sg.Text('Sample No.', size=(15,1)), sg.Combo([1,2,3,4,5,6,7,8,9,10], default_value=1, key='SampleNumber')],
                [sg.Text('Output directory:'), sg.InputText(), sg.FolderBrowse()],
                # after clicking Browse button, the following error message shows up
                # Qt: Untested Windows version 10.0 detected!
                # log4cplus:ERROR No appenders could be found for logger (AdSyncNamespace).
                # log4cplus:ERROR Please initialize the log4cplus system properly.
                [sg.Submit('Start'), sg.Button('Pause'), sg.Button('Stop'), sg.Quit()],
                [sg.Multiline(size=(None, 5), expand_y=True, key='Multiline', write_only=True, reroute_cprint=True, reroute_stdout=True)]
                ]

        self.window = sg.Window('Fan assembly auto test', layout, auto_size_buttons=False, keep_on_top=True, grab_anywhere=True)
        
        # set the controller
        self.controller = None
        # set finite state machine initial state
        self.state = View.State.Idle

    class State(Enum):
        Idle = 0
        Testing = 1
        Paused = 2
        Stopped = 3

    class Event(Enum):
        Start = 'Start'
        Pause = 'Pause'
        Stop = 'Stop'
        
    def fsm(self, event, values):
        """
        finite state machine to transition between states
        """
        if self.state == View.State.Idle:
            if event == View.Event.Start.value:
                self.state = View.State.Testing
                self.start_button_clicked(values)
        elif self.state == View.State.Testing:
            if event == View.Event.Pause.value:
                self.state = View.State.Paused
                self.pause_button_clicked()
            elif event == View.Event.Stop.value:
                self.state = View.State.Stopped
                self.stop_button_clicked()
        elif self.state == View.State.Paused:
            if event == View.Event.Start.value:
                self.state = View.State.Testing
                self.controller.resumeTest()
            elif event == View.Event.Stop.value:
                self.state = View.State.Stopped
                self.stop_button_clicked()
        elif self.state == View.State.Stopped:
            if event == View.Event.Start.value:
                self.state = View.State.Testing
                self.start_button_clicked(values)
        else:
            print("Invalid state")

    def set_controller(self, controller):
        """
        Set the controller
        :param controller:
        :return:
        """
        self.controller = controller
    
    def start_button_clicked(self, values):
        """
        Handle button click event
        :return:
        """
        if self.controller:
            if self.controller.deviceReady(values['osc'], values['power'], values['signal']) == False:
                sg.popup_ok('Connect oscillator, power supply, and signal generator.', title= 'Check Instrument connection.', keep_on_top= True)
                self.state = View.State.Idle
                return
            # change the "status" element to be the value of "sample number" element
            print("Start testing sample number " + str(values['SampleNumber']) + "...")
            self.controller.start(values['SampleNumber'], values['Browse'])

    def pause_button_clicked(self):
        """
        effective pause, stop power supply output
        """
        if self.controller:
            print("pause: output stop, press start to resume the test")
            self.controller.pause()

    def stop_button_clicked(self):
        """
        effective stop, stop power supply and also clear the job list
        """
        if self.controller:
            print("stop: output stop")
            self.controller.stop()

    def show_error(self, message):
        """
        Show an error message
        :param message:
        :return:
        """
        sg.cprint(message, text_color='red')
        pass

    def show_success(self, message):
        """
        Show a success message
        :param message:
        :return:
        """
        sg.cprint(message, text_color='blue')
        pass

    def hide_message(self):
        """
        Hide the message
        :return:
        """
        pass

    def pop_ok(self, message):
        """
        Show a pop ok message
        :param message:
        :return:
        """
        sg.popup_ok(message, keep_on_top= True)