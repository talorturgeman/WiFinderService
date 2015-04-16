import subprocess
import WiflyUtils
import xml.etree.ElementTree as ET
import argparse
import logging
import time
import re
import os.path as PATH
import os
import zipfile

#=======================================================================================
# Method Description: The method updates the time on the machine using the ntpdate package.
# Parameters: None.
# Return Value: Boolean - if the operation went well
# Aditional Info: None.
#=======================================================================================
def updateNtpDate():
    print '\n==================================================='
    print 'Update date and time using the ntpdate package...'
    print '===================================================\n'
    
    try:
        pId = WiflyUtils.isProcessRunning('ntp')
        if (pId != -999):
            print 'Stoping ntp service..'
            cmd = ['sudo', 'service', 'ntp', 'stop']
            procStopNtp = subprocess.Popen(cmd)
            procStopNtp.wait()
            
            if (procStopNtp.returncode != 0):
                print 'Can\'t stop ntp service'
                return False
            
        print 'ntp service not running now..'
        print 'Updating time using ntpd..'
        
        # Set the time of the machine to the ntp time
        cmd = ['sudo', 'ntpd', '-q', '-x']
        procNtp = subprocess.Popen(cmd)
        time.sleep(20)
        returnCode = procNtp.poll()

        if (returnCode is None):
            print 'Ntp update TIMEOUT!!!'
            procNtp.kill()
            return False
        elif (returnCode != 0):
            print 'Can\'t update using ntpdate'
            WiflyUtils.writeLog(logging.ERROR, 'WiflyCommands-updateNtpDate', 'Unable to update the time using the ntpd -q package.')
            return False
        else:
            return True
    except BaseException as err:
        WiflyUtils.writeLog(logging.ERROR, 'WiflyCommands-updateNtpDate', 'Unable to update the time using the ntpd package. Error: ' + str(err))
        return False
    finally:
        print 'Starting back ntp service..'
        cmd = ['sudo', 'service', 'ntp', 'start']
        procStartNtp = subprocess.Popen(cmd)
        procStartNtp.wait()
        
def main():
    parser = argparse.ArgumentParser(description='Analoc commands')
    parser.add_argument('-c','--command', help='The command to execute. Commands: ntp', required=True)
    args = vars(parser.parse_args())

    # Checks if we got all the params needed
    if len(args) != 1:
        print 'incorrect number of arguments. expected 1, got:', str(len(args))
    elif args['command'] == "ntp":
        updateNtpDate()
    else:
        print 'No such command:', args['command']

if __name__ == "__main__":
    main()