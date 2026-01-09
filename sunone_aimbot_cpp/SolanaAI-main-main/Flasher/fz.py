import os
import serial.tools.list_ports
import time

def find_arduino_bootloader():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if 'Arduino Leonardo' in port.description or 'bootloader' in port.description:
            return port.device
    else:
        return None

def flash_arduino(hex_file, com_port):
    command = f'avrdude -v -patmega32u4 -cavr109 -P{com_port} -b57600 -D -Uflash:w:{hex_file}:i'
    os.system(command)

def main(hex_file):
    print('Waiting for bootloader...')
    while True:
        com_port = find_arduino_bootloader()
        if com_port:
            print(f'ARBL {com_port}, flashing...')
            flash_arduino(hex_file, com_port)
            print('Complete.')
            os.system('pause')
            return
        print('ARBL.False Retrying...')
        time.sleep(2)
hex_file_path = 'firmware.hex'
main(hex_file_path)