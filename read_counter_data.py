from pymodbus import FramerType
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException
import time
import csv
import argparse

def read_and_store(client: ModbusSerialClient, 
                  starting_address: int = 0x0040, 
                  quantity: int = 2, 
                  slave_address: int = 0,
                  filename: str = 'counter_data.csv'):
    ''' Read and store data from Modbus device
    Args:
        client (ModbusSerialClient): Modbus client object
        starting_address (int): Starting address to read from
        quantity (int): Number of registers to read
        slave_address (int): Slave address(integer) of the Modbus device
        filename (str): Name of the file to save data
    '''
    # Read holding registers
    result = client.read_holding_registers(address=starting_address, count=quantity, slave=slave_address)
    if not result.isError():
        print(f"Slave id {slave_address} Received: {result.registers}")
        # Save data to file
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        data = [timestamp, merge_registers_to_int(result.registers)]
        save_data_to_file(data, filename=filename)        
    else:
        print(f"Slave id {slave_address}: Error reading data: {result}")

def read_counter_data(name: str = 'COM4', 
                      slave_addresses: list = [0,1], 
                      sleep_time: int = 5, 
                      output_files: list = ['counter_data_0.csv', 'counter_data_1.csv'],
                      **kwargs):
    ''' Read counter data from Modbus device through rs485
    Args:
        name (str): Serial port name (example: COM4 or /dev/ttyUSB0)
        slave_address (list): list of slave address(integer) of the Modbus device
        sleep_time (int): Time to wait before next read
        output_files (list): Output file name to save data
        **kwargs: Additional arguments
    '''
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
                for slave_address, output_file in zip(slave_addresses, output_files):
                    # Read and store data
                    read_and_store(client, slave_address=slave_address, filename=output_file, **kwargs)
                # Wait for sleep_time in seconds
                time.sleep(sleep_time)

    except ModbusIOException as e:
        print(f"Modbus error: {e}")
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        client.close()
        print("Connection closed.")

def save_data_to_file(data, filename='counter_data.csv'):
    ''' Save data to CSV file
    Args:
        data (list): Data to be saved
        filename (str): Name of the file to save data
    '''
    with open(filename, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write header if file is empty
        if csvfile.tell() == 0:
            writer.writerow(['Timestamp', 'Data'])
        writer.writerow(data)

def merge_registers_to_int(register_array):
    ''' Merge 2 registers to a single integer
    Args:
        register_array (list): List of registers to be merged
    Returns:
        int: Merged integer value
    '''
    # Convert register array to integer
    result = 0
    for register in register_array:
        result = (result << 16) | register
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Read and save counter data from Modbus device through rs485')
    parser.add_argument('serial_port', type=str, default='COM4', help='Serial port name (example: COM4 or /dev/ttyUSB0)')
    parser.add_argument('slave_id', nargs='+', type=int, default=0, help='Slave address(integer) of the Modbus device')
    parser.add_argument('file_name', nargs='+', type=str, default='counter_data.csv', help='Output file name to save data')
    args = parser.parse_args()
    # Check if the number of slave addresses and file names are equal
    if len(args.slave_id) != len(args.file_name):
        print("Error: The number of slave addresses and file names must be equal.")
        exit(1)
    print(f"Serial port: {args.serial_port}")
    print(f"Slave addresses: {args.slave_id}")
    print(f"Output file names: {args.file_name}")
    # Call the function with command line arguments
    read_counter_data(name=args.serial_port,
                      slave_addresses=args.slave_id,
                      output_files=args.file_name,
                      sleep_time=10)