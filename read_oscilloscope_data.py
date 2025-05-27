'''
This script reads data from an oscilloscope and saves it to a csv file.
'''
import model
import csv
import datetime
import time

def connect_oscilloscope():
    ''' Connect to the oscilloscope
    Returns:
        model.Model: The oscilloscope model object
    '''
    model_ = model.Model()
    model_.listDevices()
    if model_.connectDevice(visa_add=model_.id_dict[model_.osc.list_id[0]], inst=model_.osc):
        print("Connected to the oscilloscope.")
    
    return model_

def read_oscilloscope_data(filename: str = 'oscilloscope_data.csv', sleep_time:float = 1.0):
    ''' Read RPM and current from the oscilloscope and save it to a CSV file.
    (Because we use string transfer and it is slow, may delay if the sleep_time is less than 0.5sec)
    Args:
        filename (str): Name of the file to save data
        sleep_time (float): Time to wait between readings in seconds
    '''
    # connect to the oscilloscope
    model = connect_oscilloscope()
    model.osc.setMeasurement(res=True)
    model.osc.scope.write('acquire:stopafter RUNSTop')
    model.osc.scope.write('acquire:state 1') # run
    fg = 2 # 2 pulses per revolution

    try:
    
        while(True):
            # Read RPM and current from the oscilloscope
            rpm = float(model.osc.queryMeasurement("FREQUENCY", model.osc.Channel.FG, 'badge', log=False)) / fg * 60.0
            curr = float(model.osc.queryMeasurement(channel=model.osc.Channel.current, mode='badge', log=False))
            
            model.osc.scope.write('acquire:state 1') # run
            save_to_csv(rpm, curr, filename=filename)
            time.sleep(sleep_time)

    except Exception as e:
        print(f"Error reading data from oscilloscope: {e}")
        
    except KeyboardInterrupt:
        print("exiting...")
    
    finally:
        model.osc.scope.close()
        print("Oscilloscope connection closed.")
    
def save_to_csv(rpm: float, curr: float, filename: str = 'oscilloscope_data.csv'):
    ''' Save RPM and current data to a CSV file
    Args:
        rpm (float): RPM value
        curr (float): Current value
        filename (str): Name of the file to save data
    '''
    # Save the data to a CSV file
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        # Write header if file is empty
        if file.tell() == 0:
            writer.writerow(['Timestamp', 'RPM', 'Current'])
        now = datetime.datetime.now()
        # Format timestamp and write data, removing the last 5 digits of microseconds
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S.%f')
        writer.writerow([timestamp[:-5], rpm, curr])

if __name__ == "__main__":
    read_oscilloscope_data(filename='oscilloscope_data.csv', sleep_time=1.0)
    print("Data reading completed.")    
# This script reads data from an oscilloscope and saves it to a csv file.