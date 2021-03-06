import re
import subprocess
import os
import signal
import errno
import xml.etree.ElementTree as ET
import urllib2
import logging
import errno as errorcode
import inspect
from socket import timeout
import os.path as PATH
import threading
import argparse
import pylibmc
import netifaces
import datetime
import shutil
import calendar

#config_path = "/Users/orkazaz/Developments/WiFinderService/Sensor/analoc/wifly_config.xml"
config_path = "/boot/analoc/wifly_config.xml"
threadLocker = threading.Lock()
defaultWifiNetworkInterface = 'wlan0'
secondaryWifiNetworkInterface = 'wlan1'
kismetWifiNetworkInterface = 'wlan0mon'

def printDebug(message):
    minLogLevel = int(readConfigValue('min-error-level-to-log'))
    if (minLogLevel <= logging.DEBUG):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print 'Thread: ' + threading.currentThread().name + ', ' + timestamp + "  " + str(message)

#=======================================================================================
# Method Description: The method returns the line number where this method was called.
# Parameters: None.
# Return Value: The line number.
# Aditional Info: None.
#=======================================================================================
def lineno():
    # Returns the current line number in our program
    return inspect.currentframe().f_back.f_lineno

def deleteDir(moduleName, dirPath):
    try:
        shutil.rmtree(dirPath)
    except OSError as err:
        
        # Permission denied or File in busy
        if  err.errno != errorcode.EACCES or err.errno != errorcode.EBUSY:
            writeLog(logging.ERROR, moduleName, 'Line: ' + str(lineno()) + '. Does not have permission \ file is busy -> Could not delete the directory: ' + dirPath + '. Error: ' + err.strerror)
        else:
            writeLog(logging.ERROR, moduleName, 'Line: ' + str(lineno()) + '. Could not delete the directory: ' + dirPath + '. Error: ' + err.strerror)
        
        return False
    return True

def deleteFile(moduleName, filePath):
    try:
        os.remove(filePath)
    except OSError as err:
        
        # Permission denied or File in busy
        if  err.errno != errorcode.EACCES or err.errno != errorcode.EBUSY:
            writeLog(logging.ERROR, moduleName, 'Line: ' + str(lineno()) + '. Does not have permission \ file is busy -> Could not delete the file: ' + filePath + '. Error: ' + err.strerror)
        else:
            writeLog(logging.ERROR, moduleName, 'Line: ' + str(lineno()) + '. Could not delete the file: ' + filePath + '. Error: ' + err.strerror)
        
        return False
    return True

#=======================================================================================
# Method Description: The method writes to the errors log
# Parameters:   errorLevel = the error level of the line to write: DEBUG, INFO, WARNING, ERROR, CRITICAL
#               moduleName = the name of the module the error ocured
#               message = the message to write
# Return Value: None.
# Aditional Info: None.
#=======================================================================================
def writeLog(errorLevel, moduleName, message):
    minLogLevel = int(readConfigValue('min-error-level-to-log'))
    
    # Checks if the log error level is bigger than the min error level to log
    if (errorLevel >= minLogLevel):
        # Setting the looger. We use DEBUg level to enable debug messages
        logFilePath = readConfigValue('error-log-file-path')
        
        # Checks if the file is is bigger than 50MB. If so, delete it
        if (PATH.exists(logFilePath) and (PATH.getsize(logFilePath) / 1024 / 1024 >= 50.0)):
            deleteFile('WiflyUtils', logFilePath)
            
        logging.basicConfig(filename=logFilePath, format='%(message)s', level=logging.DEBUG)
        messageFormat = 'timestamp$$%s~~errorlevel$$%s~~module$$%s~~message$$%s'
        
        utcTimestamp = calendar.timegm(datetime.datetime.utcnow().utctimetuple())
        
        message = message.replace('\n', '->')
        if (errorLevel == logging.CRITICAL):
            logging.critical(messageFormat, utcTimestamp, errorLevel, moduleName, message)
        elif (errorLevel == logging.ERROR):
            logging.error(messageFormat, utcTimestamp, errorLevel, moduleName, message)
        elif (errorLevel == logging.WARNING):
            logging.warning(messageFormat, utcTimestamp, errorLevel, moduleName, message)
        elif (errorLevel == logging.INFO):
            logging.info(messageFormat, utcTimestamp, errorLevel, moduleName, message)
        elif (errorLevel == logging.DEBUG):
            logging.debug(messageFormat, utcTimestamp, errorLevel, moduleName, message)
            
    printDebug('========================================================')
    printDebug('Error level:' + str(errorLevel))
    printDebug('In module:' + str(moduleName))
    printDebug('Error:' + str(message))
    printDebug('========================================================')        

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
        writeLog(logging.WARNING, 'WiflyUtils', 'General error - trying to connect to the in memory server. Error: ' + str(err))
        return None

#=======================================================================================
# Method Description: The method updates the value of a given node key.
# Parameters: key: The key of the node to update.
#             newValue: The new value to update to.
# Return Value: Boolean - if the operation went well or not.
# Aditional Info: If the key doesn't exists return False.
#=======================================================================================
def updateConfigValue(key, newValue):
    strKey = str(key).lower()
    try:
        # Gets the xml tree
        tree = ET.parse(config_path)
    except BaseException as err:
        error = 'Line: ' + str(lineno()) + '. Unable to parse the config xml file. Error: ' + str(err)
        writeLog(logging.ERROR, 'WiflyUtils-updateConfigValue', error)
        return False
    else:
        # Gets the root of the tree
        root = tree.getroot()
        
        elementToUpdate = root.find(strKey)
        
        # Checks if the key doesn't exists
        if (elementToUpdate is None):
            error = 'Line: ' + str(lineno()) + '. The key: ' + strKey + ' doesn\'t exists in the config file'
            writeLog(logging.ERROR, 'WiflyUtils-updateConfigValue', error)
            return False
        else:
            try:
                elementToUpdate.text = str(newValue)
                tree = ET.ElementTree(root)
                with open(config_path, "w") as fh:
                    tree.write(fh)
            except BaseException as err:
                error = 'Line: ' + str(lineno()) + '. Unable to update the config file. Error: ' + str(err)
                writeLog(logging.ERROR, 'WiflyUtils-updateConfigValue', error)
                return False
            # All went well
            else:
                return True
            
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
        
        nCurrentInternetFailureTimesString = readFailureValue('internet-connection-current-failues-times')
        
        # Checks if we need to update the failures to zero
        if (nCurrentInternetFailureTimesString != '' and int(nCurrentInternetFailureTimesString) > 0):
            updateFailureValue('internet-connection-current-failues-times', 0)
        
        return True
    except (IOError, urllib2.URLError) as err:
        print 'Not connected to the internet:', err
        
        nCurrentInternetFailureTimesString = readFailureValue('internet-connection-current-failues-times')
        
        if (nCurrentInternetFailureTimesString != ''):
            nCurrentInternetFailureTimes = int(nCurrentInternetFailureTimesString)
            updateFailureValue('internet-connection-current-failues-times', nCurrentInternetFailureTimes + 1)
        else:
            writeLog(logging.ERROR, 'WiflyUtils-isConnecionOnline', 'Line: ' + str(lineno()) + '. Unable to read from failures file - key: internet-connection-current-failues-times doesn\' exists.')
        
        return False
    # timeout = from socket import timeout
    except timeout:
        print 'Not connected to the internet - operation time out.'
        return False
    except BaseException as errObject:
        writeLog(logging.WARNING, 'WiflyUtils-isConnectedInline', 'Line: ' + str(lineno()) + '. Some thing went wrong witht he internet connection checking. Error: ' + errObject.strerror)
        return False

def __restartWifiLanConnection(wifiNetworkInterfaceName = 'eth0'):
    cmd = ['sudo', 'ifdown', '--force', wifiNetworkInterfaceName]
    procBringWifiDown = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    procBringWifiDown.wait()
    
    # Checks for an error
    if (procBringWifiDown.returncode != 0):
        writeLog(logging.WARNING, 'WiflyUtils-__restartWifiLanConnection', 'Line: ' + str(lineno()) + '. Couldn\'t bring down the WIFI \ LAN \'' + wifiNetworkInterfaceName + '\' connection back up. Error: ' + str(procBringWifiDown.stderr.read()))
    else:
        cmd = ['sudo', 'ifup', '--force', wifiNetworkInterfaceName]
        procBringWifiUp = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        procBringWifiUp.wait()
        
        # Checks for an error
        if (procBringWifiUp.returncode != 0):
            writeLog(logging.WARNING, 'WiflyUtils-__restartWifiLanConnection', 'Line: ' + str(lineno()) + '. Couldn\'t bring back up the WIFI \ LAN: \'' + wifiNetworkInterfaceName + '\' after we brought it down. Error: ' + str(procBringWifiUp.stderr.read()))

#=======================================================================================
# Method Description: The method returns the mac address of all the network interfaces in a given array, if exists.
# Parameters: ifaces - array of network interfaces names.
# Return Value: A dictionary with 2 keys: 1. interface 2. mac_address
# Aditional Info: None.
#=======================================================================================
def getMacAddressByNetworkInterfaces(ifaces = []):
    returnInterfacesArray = []
    # Checks if we want to check mac address for a specific network interface or for all of them
    if (len(ifaces) == 0):
        writeLog(logging.WARNING, 'WiflyUtils-getMacAddressByNetworkInterfaces', 'Line: ' + str(lineno()) + '. Got an empty array of network interfaces. The array must contain 1 or more.')
    else:
        
        for currentNetworkInterface in ifaces:
            # Checks if the current network interface exists
            if (isNetworkInterfaceExists(currentNetworkInterface)):
                cmd = ['sudo', 'ifconfig', currentNetworkInterface]
                procIfConfig = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                procIfConfig.wait()
                
                if (procIfConfig.returncode != 0):
                    writeLog(logging.WARNING, 'WiflyUtils-getMacAddressByNetworkInterfaces', 'Line: ' + str(lineno()) + '. Some thing went wrong when trying to get network interface data using ifconfig command. Error: ' + str(procIfConfig.stderr.read()))
                else:
                    words = str(procIfConfig.stdout.read()).split()
                    # Linux support
                    if "HWaddr" in words:
                        returnInterfacesArray.append({"interface" : currentNetworkInterface, "mac_address" : str(words[ words.index("HWaddr") + 1 ]).upper().replace('-',':')})
                    # OSX support
                    elif "ether" in words:
                        returnInterfacesArray.append({"interface" : currentNetworkInterface, "mac_address" : str(words[ words.index("ether") + 1 ]).upper().replace('-',':')})
    return returnInterfacesArray

#=======================================================================================
# Method Description: The method returns the network interface by a specific mac address.
# Parameters: mac_address - The mac address to look for
# Return Value: The name of the network interface. If not found return an empty string.
# Aditional Info: None.
#=======================================================================================
def getNetworkInterfaceByMacAddress(mac_address):
    arrayInterfaces = getMacAddressByNetworkInterfaces(netifaces.interfaces())
    mac_address = mac_address.upper().replace('-',':')
    
    # Runs iver all the returned interfaces
    for currentInterface in arrayInterfaces:
        
        # CHecks if the current interface is the one we are looking for according to the mac address
        if (mac_address == currentInterface['mac_address']):
            return currentInterface['interface']
    return ''

#=======================================================================================
# Method Description: The method restart the internet connection: WIFI / GSM
# Parameters: None.
# Return Value: Boolean - if the internet connection was restored or not.
# Aditional Info: None.
#=======================================================================================
def restartInternetConnection():
    global defaultWifiNetworkInterface
    global secondaryWifiNetworkInterface
    global kismetWifiNetworkInterface
    
    # Checks if we are connected online now
    if (isConnectedOnline()):
        return True
    else:
        # Try to reconect 4 times before we give up
        for nCount in range(4):
            try:
                # Checks if the wlan1 exists. If so, we are on wifi connection. If not, we are on GSM connection / Lan connection
                if (isNetworkInterfaceExists(secondaryWifiNetworkInterface)):
                    __restartWifiLanConnection(secondaryWifiNetworkInterface)
                # Checks if wlan0 exists and wlan0mon exists. If so, the wifi dongle was connected after system already started and changed the wlan0 to wlan0mon.
                # In this case the new dongle will get wlan0 name so we connect to wifi using wlan0 and not wlan1 (wlan0mon still exists and used by Kismet)
                elif (isNetworkInterfaceExists(defaultWifiNetworkInterface) and isNetworkInterfaceExists(kismetWifiNetworkInterface)):
                    __restartWifiLanConnection(defaultWifiNetworkInterface)
                # We are connected using GSM / LAN
                else:
                    apn = readConfigValue('usbmodem-apn')
                    
                    # Checks if we are on GSM network
                    if (apn != ''):
                        apnUserName = readConfigValue('usbmodem-apn-user')
                        apnPassword = readConfigValue('usbmodem-apn-password')
                        
                        cmd = ['sudo', '/boot/wifly/sakis3g', 'connect', 'APN=\"' + apn + '\"', 'APN_USER=\"' + apnUserName + '\"', 'APN_PASS=\"' + apnPassword + '\"', 'USBINTERFACE=\"2\"']
                        procRestartGSM = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        procRestartGSM.wait()
                        
                        if (procRestartGSM.returncode != 0):
                            writeLog(logging.WARNING, 'WiflyUtils-restartInternetConnection-GSM', 'Line: ' + str(lineno()) + '. Couldn\'t restart the GSM connection. Error: ' + str(procRestartGSM.stderr.read()))
                    # We are on LAN connection
                    else:
                        __restartWifiLanConnection()
                
                # Checks if we are connected online now
                if (isConnectedOnline()):
                    print 'Internet connection restored..'
                    return True
        
            except BaseException as err:
                writeLog(logging.WARNING, 'WiflyUtils-restartInternetConnection', 'Line: ' + str(lineno()) + '. Couldn\'t bring the internet(WIFI/GSM) connection back up. Error: ' + str(err))
                print 'Restarting internet connection failed..'
                return False
    
    print 'Restarting internet connection failed..'
    
    # We couldn't reconnect
    return False
  
#=======================================================================================
# Method Description: The method replaces a prhase with another one.
# Parameters: dic: The dictionary of replacments, could be words, sentences or characters.
#             text: The text to replace the prahses in.
# Return Value: The altered string.
# Aditional Info: Usage Example:
#                  dic = {
#                       'Larry Wall' : 'Guido van Rossum',
#                        'creator' : 'Benevolent Dictator for Life',
#                        'Perl' : 'Python',
#                  }
#                  text = 'The Larry Wall creator used Perl programming language'
#                  new_text = multiple_replace(dic, text)
#                  print text ==> The Larry Wall creator used Perl programming language
#                  print new_text ==> The Guido van Rossum Benevolent Dictator for Life used Python programming language
#=======================================================================================
def multiple_replace(dic, text):
    pattern = "|".join(map(re.escape, dic.keys()))
    return re.sub(pattern, lambda m: dic[m.group()], text)

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
# Method Description: The method creates the failures xml file
# Parameters: failureFilePath = the failures xml file path
# Return Value: Boolean - if the operation went well or not
# Aditional Info: None.
#=======================================================================================
def createFailuresFile(failureFilePath):
    try:
        if (not PATH.exists(failureFilePath)):
            root = ET.Element("root")
            fieldKismetFailures = ET.SubElement(root, "kismet-current-failures-times")
            fieldKismetFailures.text = "0"
            fieldInternetConnectionFailureTimes = ET.SubElement(root, "internet-connection-current-failues-times")
            fieldInternetConnectionFailureTimes.text = "0"
            tree = ET.ElementTree(root)
            tree.write(failureFilePath)
        return True
    except BaseException as err:
        writeLog(logging.ERROR, 'WiflyUtils-createFailuresFile', 'Line: ' + str(lineno()) + '. Unable to create the failures xml file. Error: ' + str(err))
        
        # Checks for exception, but if the file were created, delete it.
        if (PATH.exists(failureFilePath)):
            deleteFile(failureFilePath)
        return False

#=======================================================================================
# Method Description: The method updates a value of a given key in the failures xml file
# Parameters:   key = the key to search for
#               newValue = the new value to update to
# Return Value: Boolean - if the operation went well
# Aditional Info: None.
#=======================================================================================
def updateFailureValue(key, newValue):
    failureFilePath = readConfigValue('failure-times-file-path')
    if (failureFilePath != ''):
        if (PATH.exists(failureFilePath)):
            try:
                # Gets the xml tree
                tree = ET.parse(failureFilePath)
            except BaseException as err:
                writeLog(logging.ERROR, 'WiflyUtils-updateFailureValue', 'Line: ' + str(lineno()) + '. Unable to parse the failures xml file. Error: ' + str(err))
                return False
            else:
                # Gets the root of the tree
                root = tree.getroot()
               
                elementToUpdate = root.find(key)
                
                # Checks if the key doesn't exists
                if (elementToUpdate is None):
                    writeLog(logging.ERROR, 'WiflyUtils-updateFailureValue', 'Line: ' + str(lineno()) + '. The key: ' + key + ' doesn\'t exists in the failures file')
                    return False
                else:
                    try:
                        elementToUpdate.text = str(newValue)
                        tree = ET.ElementTree(root)
                        with open(failureFilePath, "w") as fh:
                            tree.write(fh)
                    except BaseException as err:
                        writeLog(logging.ERROR, 'WiflyUtils-updateFailureValue', 'Line: ' + str(lineno()) + '. Unable to update the failures file. Error: ' + str(err))
                        return False
                    # All went well
                    else:
                        return True
        else:
            fileCreationWentWell = createFailuresFile(failureFilePath)
            return False
    else:
        writeLog(logging.CRITICAL, 'WiflyUtils-updateFailureValue', 'Line: ' + str(lineno()) + '. The failures file path doesn\'t seem to be found in the coinfig file')
        return False

#=======================================================================================
# Method Description: The method reads a given key value from the failures xml file
# Parameters: key = the key to search for
# Return Value: The wanted value. If the key doesn't exists we return an empty string.
# Aditional Info: None.
#=======================================================================================
def readFailureValue(key):
    failureFilePath = readConfigValue('failure-times-file-path')
    if (failureFilePath != ''):
        if (PATH.exists(failureFilePath)):
            try:
                # Gets the xml tree
                tree = ET.parse(failureFilePath)
        
                # Gets the root of the tree
                root = tree.getroot()
            
                return getElementText(root, key)
            except BaseException:
                return ''
        # Create the failures times file
        else:
            fileCreationWentWell = createFailuresFile(failureFilePath)
            
            if (fileCreationWentWell):
                return 0
            else:
                return ''
    else:
        writeLog(logging.CRITICAL, 'WiflyUtils-readFailureValue', 'Line: ' + str(lineno()) + '. The failures file path doesn\'t seem to be found in the coinfig file')
        return ''

#=======================================================================================
# Method Description: The method checks to see if the network interface exists or not.
# Parameters: interfaceName = the name of the network interface to search for.
# Return Value: Boolean - if the network interface exists or not
# Aditional Info: None.
#=======================================================================================
def isNetworkInterfaceExists(interfaceName = 'eth0'):
    try:
        cmd = ['sudo', 'ifconfig', interfaceName]
        procCheckForWlanZero = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        procCheckForWlanZero.wait()
        
        # Checks if the network interface exists
        if (procCheckForWlanZero.returncode == 0):
            return True
        else:
            return False
    except BaseException as err:
        writeLog(logging.ERROR, 'WiflyUtils-isNetworkInterfaceExists', 'Line: ' + str(lineno()) + '. Error while trying to search for network interface name: ' + interfaceName + '. Error: ' + str(err))
        return False

#=======================================================================================
# Method Description: The method starts the kismet server
# Parameters: None.
# Return Value: Boolean - if the restart of the kismet server went well or not.
# Aditional Info: None.
#=======================================================================================
def __startOnlyKismet():
    cmd = ['sudo', '/usr/local/bin/kismet_server', '--silent', '--daemonize', '> /dev/null 2>&1 &']
    procStartKismet = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    procStartKismet.wait()

    return isProcessRunning('kismet_server') != -999
    
#=======================================================================================
# Method Description: The method starts the kismet server. This is a "private" method.
# Parameters: None.
# Return Value: None.
# Aditional Info: None.
#=======================================================================================
def __startKismet():
    global kismetWifiNetworkInterface
    try:
        if (isNetworkInterfaceExists(kismetWifiNetworkInterface)):
            cmd = ['sudo', 'ifdown', '--force', kismetWifiNetworkInterface]
            procWlanMonitorDown = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            procWlanMonitorDown.wait()
            
            if (procWlanMonitorDown.returncode == 0):
                cmd = ['sudo', 'iwconfig', kismetWifiNetworkInterface, 'mode', 'monitor']
                procWlanMonitorUp = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                procWlanMonitorUp.wait()
                
                if (procWlanMonitorUp.returncode == 0):
                    return __startOnlyKismet()
                else:
                    return False
            else:
                return False
        else:
            global defaultWifiNetworkInterface
            
            macAdressForWifiMonitor = readConfigValue('wifi-monitor-adapter-preferred-mac-address')
            networkInterfaceToMonitor = ''
            if (macAdressForWifiMonitor == ''):
                networkInterfaceToMonitor = defaultWifiNetworkInterface
            else:
                networkInterfaceToMonitor = getNetworkInterfaceByMacAddress(macAdressForWifiMonitor)
                
                # Cheks if we couldn't find the network interface according to the given mac address
                if (networkInterfaceToMonitor == ''):
                    networkInterfaceToMonitor = defaultWifiNetworkInterface
            
            # Checks if there is no wifi dongle connected to the sensor
            if (not isNetworkInterfaceExists(networkInterfaceToMonitor)):
                writeLog(logging.critical, 'WiflyUtils-startKismet', 'Line: ' + str(lineno()) + '. Error starting the kismet service - There is no wifi dingle connected to the sensor')
            else:
                cmd = ['sudo', 'iw', 'dev', kismetWifiNetworkInterface, 'del']
                procDeleteWlanMonitor = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                procDeleteWlanMonitor.wait()
                
                cmd = ['sudo', 'iw', 'dev', networkInterfaceToMonitor, 'interface', 'add', kismetWifiNetworkInterface, 'type', 'monitor']
                procCreateMonitionInterface = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                procCreateMonitionInterface.wait()
                
                if (procCreateMonitionInterface.returncode == 0):
                    cmd = ['sudo', 'iw', 'dev', networkInterfaceToMonitor, 'del']
                    procDeleteWlanZero = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    procDeleteWlanZero.wait()
                
                    if (procDeleteWlanZero.returncode == 0):
                        return __startOnlyKismet()
                    else:
                        return False
                else:
                    return False
        
    except BaseException as err:
        writeLog(logging.critical, 'WiflyUtils-startKismet', 'Line: ' + str(lineno()) + '. Error starting the kismet service. Error: ' + str(err))
        return False

#=======================================================================================
# Method Description: The method restarts the kismet server.
# Parameters: kismetProcessName: The kismet server name. By default: kismet_server
#             forceRestart: Send True to force restart and kill the running process. By default False.
# Return Value: None.
# Aditional Info: None.
#=======================================================================================
def kismetRestarter(kismetProcessName = 'kismet_server', forceRestart = False):
    pId = isProcessRunning(kismetProcessName)
    
    # Checks if we need to kill the process
    if (pId != -999 and forceRestart):
        try:
            os.kill(pId, signal.SIGKILL)
        except OSError as err:
            # Check if the kismet process is not running at all
            if err.errno == errno.ESRCH:
                doesAllWentWell = __startKismet()
                return doesAllWentWell
                print "Not running"
            # Checks if we don't have permissions to kill the process
            elif err.errno == errno.EPERM:
                writeLog(logging.ERROR, 'WiflyUtils-kismetRestarter', 'Line: ' + str(lineno()) + '. No permission to kill the kismet process. Error: ' + err.strerror)
                return False
            # Unknown error
            else:
                writeLog(logging.ERROR, 'WiflyUtils-kismetRestarter', 'Line: ' + str(lineno()) + '. Unknown error when killing the kismet process. Error: ' + err.strerror)
                return False
        else:
            doesAllWentWell = __startKismet()
            return doesAllWentWell
    elif (pId == -999):
        doesAllWentWell = __startKismet()
        return doesAllWentWell
    else:
        print 'kismet server already running'
        return True
    
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
    if ((element is not None) and (element.text is not None)):
        returnString = element.text
    
    return returnString

def main():
    parser = argparse.ArgumentParser(description='Wifly Utils')
    parser.add_argument('-c','--command', help='The util command to execute. Commands: kismet_restart, restart_internet', required=True, default='')
    parser.add_argument('-f','--force', help='Force the command. Used in restart kismet util command.', action='store_true', required=False, default=False)
    args = vars(parser.parse_args())

    # Checks if we got all the params needed
    if len(args) < 1:
        print 'incorrect number of arguments. expected 1 or more, got:', str(len(args))
    elif args['command'] == "kismet_restart":
        # Checks if we need to force the restart
        kismetRestarter('kismet_server', args['force'])
    elif args['command'] == 'restart_internet':
        # Checks if we are not connected online
        if (not isConnectedOnline()):
            restartInternetConnection()
    else:
        print 'No such command:', args['command']

if __name__ == "__main__":
    main()