import model
import os
# select model
def selectModel(rm: model.visa.ResourceManager):
    info = rm.list_resources()
    device = model.Devices()
    
    for visa_add in info:
        try:
            resource = rm.open_resource(visa_add)
            scopename = resource.query("*IDN?")
            if '62012P' in scopename:
                device.power = model.PowerSupply(scopename, resource)
            elif 'AFG' in scopename:
                device.signal = model.SignalGenerator(scopename, resource)
            elif 'MDO' in scopename:
                device.osc = model.Oscilloscope(scopename, resource)
            elif 'MSO' in scopename:
                device.osc = model.Oscilloscope(scopename, resource)
            else:
                print("Please check new device: " + scopename)
            break
        except model.visa.VisaIOError:
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
    rm = model.visa.ResourceManager()
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
    rm = model.visa.ResourceManager()
    osc = selectModel(rm).osc
    osc.saveHardcopy('hardcopy')
    osc.saveWaveform('waveform')
    osc.errorChecking()
    osc.scope.close()
    rm.close()

def takeMeasurement():
    rm = model.visa.ResourceManager()
    osc = selectModel(rm).osc
    osc.acquireMeasure()
    osc.scope.close()
    rm.close()

def controlPowerSupply():
    rm = model.visa.ResourceManager()
    power = selectModel(rm).power
    power.reset()
    power.setVoltage(7)
    power.setOutputOn()
    power.errorChecking()
    power.scope.close()
    rm.close()

def controlSignalGenerator():
    rm = model.visa.ResourceManager()
    pwm = selectModel(rm).signal
    pwm.reset()
    pwm.setPWMOutput()
    pwm.setPWMDuty(50)
    pwm.errorChecking()
    pwm.scope.close()
    rm.close()

if __name__ == '__main__':
    rm = model.visa.ResourceManager()
    device = selectModel(rm)
        