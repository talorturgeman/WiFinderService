import xml.etree.ElementTree as ET
import os.path as PATH
import subprocess
import logging
import argparse
import pylibmc
from socket import timeout
import urllib2
import time


#config_path = "/Users/Or/Google Drive/raspberry-pi/PythonScripts/wifly_config.xml"
config_path = "/boot/wifly/wifly_config.xml"
dataHandlerFileName = 'dataHandler.py'
WiflyUtilsFileName = 'WiflyUtils.py'
WiflyCommandsFileName = 'WiflyCommands.py'

def returnCorrectScriptVersionPath(scriptNameToRun):
    pathToReturn = ''
    softwareDefaultDirectory = readConfigValue('software-default-directory')
    
    # Checks if the default software directory exists in the config file
    if (softwareDefaultDirectory != ''):
        currentVersionString = readConfigValue('version-number')
        
        # Checks if the current version number exists in the config file
        if (currentVersionString != ''):
            pathToReturn = PATH.join(softwareDefaultDirectory, 'v' + currentVersionString, scriptNameToRun)
            
            # Checks if the path exists
            if (not PATH.exists(pathToReturn)):
                pathToReturn = ''
                
    return pathToReturn

def checkForFirstSystemNtpSync(command):
    keyFirstSyncRunning = 'running'
    commansdAllowedToRun = ['restart_internet', 'ntp']
    
    # Checks if this command can pass this check and run even without syncing the system clock
    if (command in commansdAllowedToRun):
        return True
    else:
        mc = openMemoryCache()
        if (mc is None):
            return False
        else:
            # Checks if the first ntp sync is currently running
            if (keyFirstSyncRunning in mc and mc.get(keyFirstSyncRunning) == 1):
                return False
            # Checks if the first sync has already occured
            elif (keyFirstSyncRunning in mc and mc.get(keyFirstSyncRunning) == 0):
                return True
            # The first time
            else:
                try:
                    mc.set(keyFirstSyncRunning, 1)
                    isSyncOver = False
                    while (not isSyncOver):
                        restartConnectingAttempts = 1
                        
                        # Restarts the internet connection until it succeded
                        while (not isConnectedOnline()):
                            print 'Failed ', str(restartConnectingAttempts), 'attempt..'
                            if (restartConnectingAttempts >= 3):
                                print 'Restarting usb ports...'
                                cmd = ['sudo', '/boot/wifly/restart_usb_ports.sh']
                                procRestartUsbPorts = subprocess.Popen(cmd, stderr=subprocess.PIPE)
                                procRestartUsbPorts.wait()
                            
                                # Checks if the restart of the usb ports went well
                                if (procRestartUsbPorts.returncode != 0):
                                    writeLog(logging.ERROR, 'simpleLuncher-checkForFirstSystemNtpSync', 'Could not reload usb ports. Error: ' + str(procRestartUsbPorts.stderr.read()))
                                else:
                                    print 'USB ports reloaded..'
                                    restartConnectingAttempts = 0
                            restartConnectingAttempts += 1
                            main(WiflyUtilsFileName, 'restart_internet', '--command restart_internet')
                            time.sleep(2)
                        
                        # Sync using ntp
                        isSyncOver = updateNtpDate()
                    
                    # Sets that the process is over
                    mc.set(keyFirstSyncRunning, 0)
                    return True
                except BaseException:
                    # Write the error
                    if ((mc is not None) and (keyFirstSyncRunning in mc)):
                        mc.delete(keyFirstSyncRunning)
                    return False
        
def main(scriptNameToRun, command, parameters = ''):
    if (checkForFirstSystemNtpSync(command)):
        filePathToRun = returnCorrectScriptVersionPath(scriptNameToRun)
        
        # Checks if the file to run exists
        if (filePathToRun != ''):
            pId = isProcessRunning(scriptNameToRun)
            
            # Checks that the process is NOT currently running
            if (pId == -999):
                cmd = ['sudo', 'python', filePathToRun]
    
                # Adds all the parameters to the command line
                for currentParameter in parameters.split(' '):
                    cmd.append(currentParameter)
                procScriptToRun = subprocess.Popen(cmd, stderr=subprocess.PIPE)
                procScriptToRun.wait()
                
                # Checks if there are some uncought exception from the process. If so, write them down
                if (procScriptToRun.returncode != 0):
                    errorMessage = str(procScriptToRun.stderr.read())
                    writeLog(logging.ERROR, 'General-simpleLuncher', 'Uncought exception in script: ' + scriptNameToRun + ' with command line: ' + str(cmd) + '. Error: ' + errorMessage)

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
        pId = isProcessRunning('ntp')
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
            writeLog(logging.ERROR, 'simpleLuncher-updateNtpDate', 'Unable to update the time using the ntpd -q package.')
            return False
        else:
            return True
    except BaseException as err:
        writeLog(logging.ERROR, 'simpleLuncher-updateNtpDate', 'Unable to update the time using the ntpd package. Error: ' + str(err))
        return False
    finally:
        print 'Starting back ntp service..'
        cmd = ['sudo', 'service', 'ntp', 'start']
        procStartNtp = subprocess.Popen(cmd)
        procStartNtp.wait()
        
#=======================================================================================
# Method Description: The method checks if we are connected to the internet
# Parameters: None.
# Return Value: Boolean - if we are connected or not to the internet
# Aditional Info: None.
#=======================================================================================
def isConnectedOnline():
    try:
        # Tells the server to send fresh copy
        header = {"pragma" : "no-cache"}
        req = urllib2.Request("http://www.google.com", headers=header)
        
        # Open the request
        urllib2.urlopen(req, timeout=2)
        
        return True
    except (IOError, urllib2.URLError) as err:
        print 'Not connected to the internet:', err
        
        return False
    # timeout = from socket import timeout
    except timeout:
        print 'Not connected to the internet - operation time out.'
        return False
    except BaseException as errObject:
        writeLog(logging.WARNING, 'simpleLuncher-isConnectedInline', 'Some thing went wrong witht he internet connection checking. Error: ' + str(errObject))
        return False
    
#=======================================================================================
# Method Description: The method open a connection the memory cache.
# Parameters: None.
# Return Value: Memory Cache Client object. If connection didn't went well None is returned.
# Aditional Info: None.
#=======================================================================================
def openMemoryCache():
    try:
        # Create the memory cache object
        mc = pylibmc.Client(["127.0.0.1"], binary=True, behaviors={"tcp_nodelay": True, "ketama": True})
        return mc
    except BaseException as err:
        writeLog(logging.WARNING, 'simpleLuncher', 'General error - trying to connect to the in memory server. Error: ' + str(err))
        return None
    
#=======================================================================================
# Method Description: The method writes to the errors log
# Parameters:   errorLevel = the error level of the line to write: DEBUG, INFO, WARNING, ERROR, CRITICAL
#               moduleName = the name of the module the error ocured
#               message = the message to write
# Return Value: None.
# Aditional Info: None.
#=======================================================================================
def writeLog(errorLevel, moduleName, message):
    # Setting the looger. We use DEBUG level to enable debug messages
    logFilePath = readConfigValue('error-log-file-path')
    logging.basicConfig(filename=logFilePath, format='timestamp$$%(asctime)s~~%(message)s', level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')
    messageFormat = 'errorlevel$$%s~~module$$%s~~message$$%s'
    message = message.replace('\n', '->')
    if (errorLevel == logging.CRITICAL):
        logging.critical(messageFormat, errorLevel, moduleName, message)
    elif (errorLevel == logging.ERROR):
        logging.error(messageFormat, errorLevel, moduleName, message)
    elif (errorLevel == logging.WARNING):
        logging.warning(messageFormat, errorLevel, moduleName, message)
    elif (errorLevel == logging.INFO):
        logging.info(messageFormat, errorLevel, moduleName, message)
    elif (errorLevel == logging.DEBUG):
        logging.debug(messageFormat, errorLevel, moduleName, message)
        
#=======================================================================================
# Method Description: The method check if the process is runing
# Parameters: processName: the name of the process to look for
# Return Value: The process id. If not found returns -999.
# Aditional Info: None.
#=======================================================================================
def isProcessRunning(processName):
    pId = -999;
    processList = subprocess.Popen(["ps", "axw"], stdout=subprocess.PIPE)
    
    # Run over all the lines in the process list
    for currentProcessLine in processList.stdout:

        # Checks if the current process line contains the wanted process name
        if (processName in currentProcessLine):
            pId = int(currentProcessLine.split(None, 1)[0])
        
            return pId
    
    return pId

#=======================================================================================
# Method Description: The method reads the config file value by a given key.
# Parameters: The key to read from.
# Return Value: The wanted value. If the key doesn't exists, or if the value is empty, returns an
#               empty string
# Aditional Info: None.
#=======================================================================================
def readConfigValue(key):
    try:
        # Gets the xml tree
        tree = ET.parse(config_path)

        # Gets the root of the tree
        root = tree.getroot()
    
        return getElementText(root, key)
    except BaseException:
        return ''

#=======================================================================================
# Method Description: The method reads the data between an elements start and end tags.
# Parameters: fatherNode: The father tag.
#             elementName: The name of the element to get the data from.
# Return Value: The text of the element. If the element has no text between the start and end tags, then an empty string is returned.
# Aditional Info: None.
#=======================================================================================
def getElementText(fatherNode, elementName):
    returnString = ''
    
    # Gets the element
    element = fatherNode.find(elementName)
    
    # Checks if the elements has a text in the element
    if element is not None:
        returnString = element.text
    return returnString

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Wifly Simple Luncher')
    parser.add_argument('-c','--command', help='The util command to execute. Commands: kismet_restart, restart_internet, ntp, data_handler', required=True, default='')
    parser.add_argument('-f','--force', help='Force the command. Used in restart kismet util command.', action='store_true', required=False, default=False)
    args = vars(parser.parse_args())
    
    # Checks if we need to start the main data collection
    if (len(args) < 1):
        print 'incorrect number of arguments. expected 1 or more, got:', str(len(args))
    elif (args['command'] == "data_handler"):
        main(dataHandlerFileName, 'data_handler')
    elif args['command'] == "kismet_restart":
        if (args['force']):
            main(WiflyUtilsFileName, 'kismet_restart', '--command kismet_restart --force')
        else:
            main(WiflyUtilsFileName, 'kismet_restart', '--command kismet_restart')
    elif args['command'] == 'restart_internet':
        main(WiflyUtilsFileName, 'restart_internet', '--command restart_internet')
    elif args['command'] == 'ntp':
        main(WiflyCommandsFileName, 'ntp', '--command ntp')
    else:
        print 'No such command:', args['command']
