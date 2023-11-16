import model
import os
# select model
def selectModel():
    # osc
    # visa_address = 'USB0::0x0699::0x0527::C033493::INSTR' # hard coded name for test
    # power supply
    visa_address = 'USB0::0x1698::0x0837::001000005648::INSTR'
    return visa_address

def autosetSingleCurvePlot():
    osc = model.Oscilloscope(selectModel())
    osc.reset()
    osc.autoset()
    osc.ioConfig()
    osc.acqConfig()
    osc.dataQuery()
    osc.retrieveAcqSetting()
    osc.errorChecking()
    osc.scope.close()
    osc.rm.close()

    osc.createScaledVectors()
    osc.plotting()
    osc.saveCurve('osc_curve')

def outputAllChannelSignal():
    osc = model.Oscilloscope(selectModel())
    osc.saveHardcopy('hardcopy')
    osc.saveWaveform('waveform')
    osc.errorChecking()
    osc.scope.close()
    osc.rm.close()

def takeMeasurement():
    osc = model.Oscilloscope(selectModel())
    osc.acquireMeasure()
    osc.scope.close()
    osc.rm.close()

def controlPowerSupply():
    power = model.PowerSupply(selectModel())
    power.reset()
    power.setVoltage(7)
    power.setOutputOn()
    power.errorChecking()
    power.scope.close()
    power.rm.close()

if __name__ == '__main__':
    controlPowerSupply()    