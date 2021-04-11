#
#--------------------------------------------------------------------------------
#--                                                                            --
#--                     Vastmindz - London UK                                  --
#--                 Santa Maria - Rio Grande do Sul/Brazil                     --
#--                                                                            --
#--------------------------------------------------------------------------------
#--                                                                            --
#-- File		: Vitals_ecg_ESP.py                                     	   --
#-- Authors     : Luis Felipe de Deus                                          --
#--                                                                            -- 
#--------------------------------------------------------------------------------
#--                                                                            --
#-- Created     : 09 Mar 2021                                                  --
#-- Update      : 04 Apr 2021                                                  --
#--------------------------------------------------------------------------------
#--                              Overview                                      --
#-- This script creates a serial comm with the Wrover board, then read the ECG --
# data. After X minutes of data, saves into a csv file, and then run the       --
# preprocessing stage. Ultimatelly, run the AI algorithms to extract the vitals--
# and send back to the board                                                   --
#
# NOTE: I didn't include the AI files and scripts because they are proprietary
# reach me out: luis@vastmindz.com
#-- Code executed in python3                                                   --
#--------------------------------------------------------------------------------
#

#Import the libs which we need
import os
import serial
from datetime import datetime
import numpy as np
import pandas as pd

def check_sync():
    '''
    @brief: This function purposes is only wait unitl the second 0 of the local time
    Thus, we have a time sync file e.g. 08:50:00 - 08:55:00
    '''
    #Random value different than zero
    second_start=10
    #Wait until second 0 to sync signal
    print("Waiting to start...")
    while(second_start != 0):
        #Get data from serial and throuw away
        trash = ser.readline()
        #Get current time
        time_init = datetime.now()
        time_init = time_init.strftime("%H:%M:%S")
        aux = str(time_init).split(":")
        #hour_start = int(aux[0])
        minute_start = int(aux[1])
        second_start = int(aux[2])
        
    return minute_start

def get_ecg_sample(minute_start):
    '''
    @brief: This function goal is collect the ECG sample that come from the serial.
    So, basically the function read the serial package until we close the script with CTRL+C
    Once its done, saves into a csv file along with timestamps
    @param: The minute that the experiment started
    '''
    print(">>Starting Experiment...Please wait")

    miss=0  #Control the number of packages we lose
    ecg_data, timestamps = [],[] #Lists where we'll store the ecg/timestamps

    while(True):
        try:
            #Wait until serial is available
            if (ser.inWaiting()):
                #Get current time
                time_now = datetime.now()
                time_now = time_now.strftime("%d-%m-%Y_%H:%M:%S")
                aux = str(time_now).split("_")
                aux2 = aux[1].split(":")
                m = int(aux2[1])

                #Get data from serial
                serial_data = ser.readline()
                serial_data = str(serial_data)
                serial_data = serial_data.replace("b'","")
                serial_data = serial_data.replace("\\r","")
                serial_data = serial_data.replace("\\n'","")
                try:
                    serial_data = int(serial_data)
                    ecg_data.append(serial_data)
                    timestamps.append(time_now)
                except:
                    miss+=1
            
            
        except KeyboardInterrupt:
            ecg_data = np.asarray(ecg_data)
            filename = 'luis_ecg_data_'+time_now.replace(':','_')+'.csv'
            df = pd.DataFrame(np.asarray([timestamps, ecg_data]).T, columns=['Timestamps', 'ECG'])
            df.to_csv(filename)
            print("Misses: ", miss)
            print("KEYBOARD INTERRUPT - FILE SAVED")
            return
                


if __name__ == '__main__':
    #------ CONFIGS ----- #
    # comm port and file
    commPort = "/dev/ttyUSB1" # PUT YOUR SERIAL PORT HERE.

    DEFAULT_BAUDRATE = 115200 # To use in serial communication
    

    #Get current time
    experiment_time = datetime.now()
    experiment_time = experiment_time.strftime("%d-%m-%Y_%H:%M:%S")

    print("\n\n ##### EXPERIMENT STARTED ########")
    print('>>',experiment_time)

    # Create a serial communication
    print("Starting serial communication...\n")
    ser = serial.Serial(commPort, DEFAULT_BAUDRATE)

    sample = 0
    results = []
    while(True):
        #Make sure to start on second 0 to sync
        minute_start = check_sync()
        #Get X minutes ECG sample
        get_ecg_sample(minute_start)
        print(" Data stored... ")
        print("DATA ACQUISITION ENDED")
        break
