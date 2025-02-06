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
        if self.tooltip != "":
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

def Collapsible(layout, key, title='', arrows=(sg.SYMBOL_DOWN, sg.SYMBOL_UP), collapsed=False):
    """
    User Defined Element
    A "collapsable section" element. Like a container element that can be collapsed and brought back
    :param layout:Tuple[List[sg.Element]]: The layout for the section
    :param key:Any: Key used to make this section visible / invisible
    :param title:str: Title to show next to arrow
    :param arrows:Tuple[str, str]: The strings to use to show the section is (Open, Closed).
    :param collapsed:bool: If True, then the section begins in a collapsed state
    :return:sg.Column: Column including the arrows, title and the layout that is pinned
    """
    return sg.Column([[sg.T((arrows[1] if collapsed else arrows[0]), enable_events=True, k=key+'-BUTTON-'),
                       sg.T(title, enable_events=True, key=key+'-TITLE-')],
                      [sg.pin(sg.Column(layout, key=key, visible=not collapsed, metadata=arrows))]], pad=(0,0))

class View():
    def __init__(self, cprint:bool = False, stdout:bool = False) -> None:
        '''
        initial layout of GUI
        
        Parameters
        ----------
        cprint : bool
            reroute cprint to GUI
        stdout : bool
            reroute stdout to GUI, default False, for ease of log checking when debugging.
        '''
        sg.theme('Default 1')
        sg.set_options(element_padding=(0, 0))
        # display test conditions and update user input values
        self.sec1_key = '-SEC1_KEY-'
        section1 = [
            [sg.Text('Connected device:')],
            [sg.Text('Power Supply:', size=(15,1)), sg.Combo(key='power', values={}, expand_x=True)],
            [sg.Text('Signal Generator:', size=(15,1)), sg.Combo(key='signal', values={}, expand_x=True)],
            [sg.Text('Oscilloscope:', size=(15,1)), sg.Combo(key='osc', values={}, expand_x=True)],
            [sg.Text('Output Report:', size=(15,1)), sg.Input('report', key='-filename-', expand_x=True), sg.FileSaveAs(key='-saved as-')]
        ]
        self.conditions = ('Duty 0%', 'Duty 50%', 'Duty 100%')
        self.cols = ('RPM', 'Current (A)')
        self.sec2_key = '-SEC2_KEY-'
        section2 =  [
            [sg.Column(self.custom_col(c, self.cols, size=(10,1), pad=(1,1))) for c in self.conditions],
        ]
        layout = [
                [Collapsible(section1, key=self.sec1_key, title='Change input instruments and output file directory', collapsed=True)],
                [Collapsible(section2, key=self.sec2_key, title='Specify Spec', collapsed=True)],     
                [sg.Submit('Start'), sg.Button('Pause'), sg.Button('Stop'), sg.Quit()],
                [sg.Multiline(size=(None, 5), expand_y=True, key='Multiline', write_only=True, reroute_cprint=cprint, reroute_stdout=stdout, autoscroll=True)]
        ]

        self.window = sg.Window('Fan assembly auto test', layout, auto_size_buttons=False, keep_on_top=True, grab_anywhere=True)
        
        # set the controller
        self.controller = None
        # set finite state machine initial state
        self.state = View.State.Idle

    def getSpecValue(self):
        event, values = self.window.read()
        spec = []
        for con in self.conditions:
            for col in self.cols:
                spec.append(values[(con, col)])
        return spec

    def changeCollapsibleSection(self, event, section_key):
        if event.startswith(section_key):
            self.window[section_key].update(visible=not self.window[section_key].visible)
            self.window[section_key+'-BUTTON-'].update(self.window[section_key].metadata[0] if self.window[section_key].visible else self.window[section_key].metadata[1])

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
            # when the sample no is 0, meaning the test is at the beginning, pop up window asking spec standard
            if self.controller.getSampleNo() == 0:
                sg.popup_ok('Specify spec', keep_on_top=True)
                # use the current file output directory and disable changing
                self.window['-filename-'].update(disabled = True)
                self.window['-saved as-'].update(disabled = True)
                
            # popup window ask sample number
            key1 = 'Number'
            dropdown_list_layout = sg.Spin([10,9,8,7,6,5,4,3,2,1], initial_value=self.controller.getSampleNo(), key=key1)
            sample_num = self.popup_input("Choose sample number", keep_on_top=True, content_layout=dropdown_list_layout, key=key1)
            if sample_num == 1:
                # choose a oscillator display scale
                radio_text = [scale.getName() for scale in self.controller.scale_list]
                radio_keys = range(len(radio_text))
                radio_layout = [[sg.Radio(text, group_id=1, key=key)] for text, key in zip(radio_text, radio_keys)]
                res = self.popup_input('choose current scale', content_layout=radio_layout, keep_on_top=True)
                for key, value in res.items():
                    if value == True:
                        self.controller.scale_no = key
                        break
            if self.controller.deviceReady(values['osc'], values['power'], values['signal']) == False:
                sg.popup_ok('Connect oscillator, power supply, and signal generator.', title= 'Check Instrument connection.', keep_on_top= True)
                self.state = View.State.Idle
                return
            # change the "status" element to be the value of "sample number" element
            self.show_success("Start testing sample number " + str(sample_num) + "...")
            self.controller.start(sample_num, values['-filename-'] + '.xlsx')
    
    def popup_input(self, message, title=None, button_color=None, content_layout=None, key=None,
                   background_color=None, icon=None, font=None, no_titlebar=False,
                   grab_anywhere=False, keep_on_top=None, location=(None, None), relative_location=(None, None), image=None, modal=True):
        """
        Display Popup with given layout. Returns the input or None if closed / cancelled
        
        Parameters
        ----------
        message : str
            message displayed to user
        title : str
            Window title
        button_color : (str, str) or str
            Color of the button (text, background)
        content_layout : list
            layout for popup windows
        key : str, optional
            the specified button key for outputting value, of none, returns all value 
        background_color : str
            background color of the entire window
        icon : bytes | str
            filename or base64 string to be used for the window's icon
        font : (str or (str, int[, str]) or None)
            specifies the  font family, size, etc. Tuple or Single string format 'name size styles'. Styles: italic * roman bold normal underline overstrike
        no_titlebar : bool
            If True no titlebar will be shown
        grab_anywhere : bool
            If True can click and drag anywhere in the window to move the window
        keep_on_top : bool
            If True the window will remain above all current windows
        location : (int, int)
            (x,y) Location on screen to display the upper left corner of window
        relative_location : (int, int)
            (x,y) location relative to the default location of the window, in pixels. Normally the window centers.  This location is relative to the location the window would be created. Note they can be negative.
        image : (str) or (bytes)
            Image to include at the top of the popup window
        modal : bool
            If True then makes the popup will behave like a Modal window... all other windows are non-operational until this one is closed. Default = True

        Returns
        -------             
        int | None
            value of specified key or None if window was closed or cancel button clicked
                       
        """
        if image is not None:
            if isinstance(image, str):
                layout = [[sg.Image(filename=image)]]
            else:
                layout = [[sg.Image(data=image)]]
        else:
            layout = [[]]
        layout += [[sg.Text(message, size=(15,1)), content_layout],
                  [sg.Ok(size=(6, 1))]]
        window = sg.Window(title=title or message, layout=layout, icon=icon, auto_size_text=True, button_color=button_color, no_titlebar=no_titlebar,
                    background_color=background_color, grab_anywhere=grab_anywhere, keep_on_top=keep_on_top, location=location, relative_location=relative_location, finalize=True, modal=modal, font=font)

        button, values = window.read()
        window.close()
        del window
        if button != 'Ok':
            return None
        else:
            if key != None:
                path = values[key]
                return path
            else:
                return values

    def custom_col(self, heading = 'heading', cols = None, size=(None, None), pad = (None, None)):
        layout = [
            [sg.Text(text = heading, justification='center', background_color = 'light gray', expand_x=True, pad=pad)],
            [sg.Column(layout=[
                [sg.Text(s, justification='center', background_color='light gray', expand_x=True, pad=pad)],
                [sg.Input('0', justification='r', key=(heading, s), size=size, pad=pad)]
            ], ) for s in cols]    
        ]
        return layout

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