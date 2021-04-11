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
import time
from datetime import datetime
import numpy as np
import pandas as pd

from helper.fatigue_status import *
from helper.bloodPressure import *
from helper.AFIB import *

import helper.custom_ampd as ampd
import helper.peak_detection_additional as pda
from helper.preprocessing_lib_luis import preprocess

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
        
        minute_start = int(aux[1])
        second_start = int(aux[2])
        
    return minute_start
    

def get_ecg_sample(minute_start):
    '''
    @brief: This function goal is collect the ECG sample that come from the serial.
    So, basically the function read the serial package, ajust and check if it reached the amount of data
    Once it collected X minutes of data, saves into a csv file along with timestamps
    @param: The minute that the experiment started
    '''
    print(">>Starting Experiment...Please wait")

    miss=0  #Control the number of packages we lose
    ecg_data, timestamps = [],[] #Lists where we'll store the ecg/timestamps

    while(True):
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
                #print("Timestamps: ", time_now, " value: ", (serial_data))
                ecg_data.append(serial_data)
                timestamps.append(time_now)
            except:
                miss+=1
                pass
            
            #Check if we reached the amount of data based on time
            #If so, save the data into a csv and return
            if(int(abs(m-minute_start)) >= TIME_SAMPLE):
                ecg_data = np.asarray(ecg_data)
                filename = 'luis_ecg_data_'+time_now.replace(':','_')+'.csv'
                df = pd.DataFrame(np.asarray([timestamps, ecg_data]).T, columns=['Timestamps', 'ECG'])
                df.to_csv(filename)
                print("Misses: ", miss)
                
                return ecg_data, filename, time_now


if __name__ == '__main__':
    #------ CONFIGS ----- #
    # comm port and file
    commPort = "/dev/ttyUSB1" # PUT YOUR SERIAL PORT HERE.

    DEFAULT_BAUDRATE = 115200 # To use in serial communication
    TIME_SAMPLE = 5 #Amount of data, in minutes e.g. 5 minutes = 300s * 100Hz = 30,000 samples

    #Get vitals configs
    #NOTE THIS FILES ARE NOT AVAILABLE ON THIS PUBLIC REPO
    settings_fatigue = fatigue_config()
    settings_BP = bp_config()
    settings_AFIB = afib_config()

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
        ecg_raw, filename, time_now = get_ecg_sample(minute_start)
        print(time_now," Data stored... SAMPLE: ", sample)
        #Preprocess ECG
        ECGf = preprocess(ecg_raw, settings_fatigue['sps'])
        #Extract peaks
        #-----------  PEAK DETECTION  --------------------#
        if(settings_fatigue['method']=='ampd'):
            peaks, hr = ampd.ampd_window2(ECGf, fs=settings_fatigue['sps'])
            #print("HR: ", hr)
        elif(settings_fatigue['method']=='pda'):
            maxes = pda.find_maxes(np.asarray(ECGf))
            peaks = np.where(maxes)[0]

        #-----------  GET HEART RATE  --------------------#
        rr_list = (np.diff(peaks)/settings_BP['sps'])*1000
        hr = 60000/np.mean(rr_list)

        #-----------  GET FATIGUE STATUS  --------------------#
        settings_fatigue['peaks'] = peaks
        try:
            status, preds_per_class = get_fatigue_status(settings_fatigue)
        
            preds_per_class = np.asarray(preds_per_class)
            preds_per_class = str(preds_per_class)
        except:
            status = 'NONE'
            preds_per_class = []
        

        #-----------  CALCULATE BLOOD PRESSURE  --------------------#
        settings_BP['peaks'] = peaks
        try:
            SBP, DBP = calculate_blood_pressure(settings_BP)
        except:
            SBP = 0
            DBP = 0

        #-----------  CALCULATE AFIB RISK  --------------------#
        settings_AFIB['peaks'] = peaks
        try:
            AFIB, preds_afib = calculate_AFIB_risk(settings_AFIB)
        except:
            AFIB = 0
            preds_afib = []

        print("\n>>HEART RATE: ", hr)
        print(">>FATIGUE STATUS: ", status)
        print(">>PREDICTIONS ----")
        print(preds_per_class)
        print(">>BLOOD PRESSURE (SBP/DBP): %d/%d"%(SBP,DBP))
        print(">>AFIB RISK : %.2f"%(AFIB))
        print("\n>>PREDICTIONS ----")
        print(preds_afib)

        #Save the results to further analysis
        results.append([filename, hr, status, preds_per_class, SBP, DBP, AFIB, str(preds_afib)])
        df = pd.DataFrame(results, columns=['filename','HR','Fatigue','preds', 'SBP','DBP', 'AFIB Risk %','AFIB[0,1]'])
        
        df.to_csv('DATAFRAME_RESULTS_'+experiment_time.replace(':','_')+'.csv')
        sample+=1

        #Send back the results to the board
        packet = 'HR:'+str(int(hr))+'\r\n'
        ser.write(packet.encode())
        time.sleep(1)

        packet = 'SBP:'+str(int(SBP))+'\r\n'
        ser.write(packet.encode())
        time.sleep(1)

        packet = 'DBP:'+str(int(DBP))+'\r\n'
        ser.write(packet.encode())
        time.sleep(1)

        packet = 'FAT:'+str(status)+'\r\n'
        ser.write(packet.encode())
        time.sleep(1)

