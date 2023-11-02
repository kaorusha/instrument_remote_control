import model
# select model
def selectModel():
    visa_address = 'USB0::0x0699::0x0527::C033493::INSTR' # hard coded name for test
    return visa_address

osc = model.Oscilloscope(selectModel())
#osc.reset()
#osc.autoset()
osc.ioConfig()
osc.acqConfig()
osc.dataQuery()
osc.retrieveAcqSetting()
osc.errorChecking()
#osc.saveHardcopy('hardcopy')
osc.saveWaveform('waveform')
osc.scope.close()
osc.rm.close()

#osc.createScaledVectors()
#osc.plotting()
#osc.saveCurve('osc_curve')