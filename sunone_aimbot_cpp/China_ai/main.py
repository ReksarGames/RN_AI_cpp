# -*- coding: utf-8 -*-
import ctypes
from ctypes import *
import time
from queue import Queue
import _ctypes
import _queue
from threading import Thread
import cv2
import bettercam
import win32api
import win32con
import win32gui
from pynput import keyboard, mouse
from function import *
from infer_class import *
import onnxruntime as rt
from infer_function import *
from function import *
import json
import math
import win32gui
from cryptography.fernet import Fernet
import cv2
import numpy as np
import requests
import os
import random
import string
import kmNet
from dearpygui import dearpygui as dpg
import scipy
import filterpy
from scipy.optimize import linear_sum_assignment
from filterpy.kalman import KalmanFilter
from SimpleDeepSORT import SimpleDeepSORT
import base64
import websocket
from concurrent.futures import ThreadPoolExecutor
import pyclick
from pyclick import HumanCurve
import pydirectinput
import serial
import serial.tools.list_ports
from app import Valorant
import sys
import traceback


def global_exception_hook(exctype, value, tb):
    """
    Global exception hook to catch all unhandled exceptions.
    """
    # Write detailed exception information to log file
    with open('error_log.txt', 'a', encoding='utf-8') as f:
        f.write(f"[Global Exception] {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(''.join(traceback.format_exception(exctype, value, tb)))
        f.write('\n')
    # Display a friendly error message to the user
    print('An unhandled exception occurred. Details have been written to error_log.txt. Please report this file to the developer.')

# Set custom global exception handler
sys.excepthook = global_exception_hook

def handle_tensorrt_error():
    """
    Handle TensorRT-related import or initialization errors.
    """
    # Print detailed guidance information to console
    print('\n==================================================')
    print('TensorRT-related error detected, but program will continue using ONNX inference')
    print('If you want to use TensorRT acceleration, please install the following components:')
    print('1. CUDA Toolkit')
    print('2. cuDNN')
    print('3. TensorRT')
    print('4. For configuration tutorial, visit: https://www.yuque.com/huiyestudio/dqrld3/rislyof9zegdfira')
    print('==================================================\n')

    # Record error information to file
    with open('tensorrt_error.txt', 'a', encoding='utf-8') as f:
        f.write(f"[TensorRT Not Installed] {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write('Program will continue using ONNX inference\n\n')

# Main program entry point


if __name__ == '__main__':
    valorant_instance = None
    try:
        try:
            print('Starting program...')
            try:
                # Try to start main program
                valorant_instance = Valorant()
                valorant_instance.start()
            except ImportError as e:
                # Catch import errors, especially TensorRT-related ones
                error_str = str(e).lower()
                if 'tensorrt' in error_str or 'cuda' in error_str or 'nvinfer' in error_str:
                    handle_tensorrt_error()
                    valorant_instance = Valorant()
                    valorant_instance.start()
                else:
                    raise
            except OSError as e:
                # Catch OS errors, which may also be caused by missing GPU libraries
                error_str = str(e).lower()
                if 'nvinfer' in error_str or 'cudnn' in error_str or 'cuda' in error_str:
                    handle_tensorrt_error()
                    valorant_instance = Valorant()
                    valorant_instance.start()
                else:
                    raise
        except Exception as e:
            # Catch all other exceptions during startup
            with open('error_log.txt', 'w', encoding='utf-8') as f:
                f.write(traceback.format_exc())
            print('An error occurred. Details have been written to error_log.txt. Please report this file to the developer.')
            input('Press Enter to exit...')
    finally:
        # Ensure resource cleanup when program exits
        if valorant_instance is not None:
            try:
                print('Cleaning up program resources...')
                valorant_instance._secure_cleanup()
                print('Program resource cleanup completed')
            except Exception as e:
                # Handle exceptions that may occur during cleanup
                print(f"Error cleaning up program resources: {e}")
                with open('error_log.txt', 'a', encoding='utf-8') as f:
                    f.write(f"[Resource Cleanup Exception] {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Cleanup error: {str(e)}\n")
                    f.write(traceback.format_exc())
                    f.write('\n')