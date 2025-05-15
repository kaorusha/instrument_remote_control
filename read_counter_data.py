from pymodbus import FramerType
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException
import time
import csv

def read_counter_data(name: str = 'COM4', 
                      slave_address: int = 0, 
                      starting_address: int = 0x0040, 
                      quantity: int = 2, 
                      sleep_time: int = 5, 
                      output_file: str = 'counter_data.csv'):
    try:
        # Configure the serial connection
        client = ModbusSerialClient(
            framer=FramerType.RTU,
            port=name,  # Replace with your COM port
            baudrate=19200,  # Adjust baudrate as per your device
            timeout=1,
            stopbits=2,
            bytesize=8,
            parity='N'
        )
        if client.connect():
            print("Connected to Modbus device on %s."%name)
        
            while True:
                # Read holding registers
                result = client.read_holding_registers(address=starting_address, count=quantity, slave=slave_address)  # Read available data
                if not result.isError():  # Check for errors
                    print(f"Received: {result.registers}")
                    # Save data to file
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    data = [timestamp, merge_registers_to_int(result.registers)]
                    save_data_to_file(data, filename=output_file)
                else:
                    print(f"Error reading data: {result}")

                time.sleep(sleep_time)  # Wait for sleep_time in second

    except ModbusIOException as e:
        print(f"Modbus error: {e}")
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        client.close()
        print("Connection closed.")

def save_data_to_file(data, filename='counter_data.csv'):
    # Append data to CSV file
    # Check if file exists and is not empty
    with open(filename, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write header if file is empty
        if csvfile.tell() == 0:
            writer.writerow(['Timestamp', 'Data'])
        writer.writerow(data)

def merge_registers_to_int(register_array):
    # Convert register array to integer
    result = 0
    for register in register_array:
        result = (result << 16) | register
    return result

if __name__ == "__main__":
    read_counter_data()