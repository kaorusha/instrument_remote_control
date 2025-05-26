'''
This script reads data from an oscilloscope and saves it to a csv file.
'''
import model
import csv
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

def read_oscilloscope_data(filename: str = 'oscilloscope_data.csv', sleep_time:float = 0.1):
    ''' Read RPM and current from the oscilloscope
    Args:
        model (model.Model): The oscilloscope model object
    Returns:
        tuple: RPM and current values
    '''
    # connect to the oscilloscope
    model = connect_oscilloscope()

    try:
    
        while(True):
            # Read RPM and current from the oscilloscope
            fg = 2 # 2 pulses per revolution
            rpm = model.osc.metric_prefix(float(model.osc.queryMeasurement("FREQUENCY", model.osc.Channel.FG))) / fg * 60.0
            curr = float(model.osc.queryMeasurement(channel=model.osc.Channel.current))
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
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        writer.writerow([timestamp, rpm, curr])

if __name__ == "__main__":
    read_oscilloscope_data(filename='oscilloscope_data.csv', sleep_time=0.1)
    print("Data reading completed.")    
# This script reads data from an oscilloscope and saves it to a csv file.