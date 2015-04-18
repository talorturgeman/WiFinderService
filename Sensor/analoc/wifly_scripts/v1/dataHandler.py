import xml.etree.ElementTree as ET
import os.path as PATH
import os
import glob
import WiflyUtils
import WiflySender
import threading
import json
import logging
import datetime
import sys
from dateutil import parser
import calendar

nthreadCounter = 1
lstThreads = []
mc = WiflyUtils.openMemoryCache()
keyMaxTimeLastRun = "maxTimeLastRun"
keyCurrentMaxTime= "maxLastTime"

class myThreadSender(threading.Thread):
    def __init__(self, threadID, threadName, lstData, currentFile, backupDirectory, sendurl, isNetXmlFile):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = threadName
        self.data = lstData
        self.currentFile = currentFile
        self.backupDirectory = backupDirectory
        self.sendurl = sendurl
        self.isNetXmlFile = isNetXmlFile
    def run(self):
        print "Starting " + self.name
        
        # Sends the data
        allWentWell = WiflySender.sendData(self.data, self.currentFile, self.sendurl)
        
        # If we need to do any more operations in case of sending data
        # We don't need to do anything if we are sending errors right now, Or we are
        # sending jsons right now.
        # And also only if the something went wrong
        if (self.isNetXmlFile and (not allWentWell)):
            # Gets the file name without the path (file name + file extention)
            baseName = PATH.basename(self.currentFile)
            filenameParts = PATH.splitext(baseName)
            
            # Creates the new file name
            fileNameWithNewExtention = filenameParts[0] + '.json'
            newWiflyile = PATH.join(self.backupDirectory, PATH.basename(fileNameWithNewExtention))
            
            try:
                # Saves the data in a json file
                with open(newWiflyile, 'w') as fsStream:
                    fsStream.write(json.dumps(self.data, separators=(',',':'), sort_keys=False))
            except BaseException as err:
                WiflyUtils.writeLog(logging.ERROR, 'dataHandler', 'Line: ' + str(WiflyUtils.lineno()) + '. Unable to save the data in JSON format. Error: ' + str(err))
            
            isDeleteWentWell = WiflyUtils.deleteFile('dataHandler-myThreadSender-run', self.currentFile)
            
            # Checks if we couldn't delete the netxml file
            if (not isDeleteWentWell):
                WiflyUtils.deleteFile('dataHandler-myThreadSender-run', newWiflyile)

class myThreadJsonSender(threading.Thread):
    def __init__(self, threadID, threadName, backup_directory, sendurl):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = threadName
        self.sendurl = sendurl
        self.backupDirectory = backup_directory
    def run(self):
        print "Starting " + self.name
        global nthreadCounter
        # A loop that runs over all the json backup files and send it
        for currentJsonFile in glob.glob(PATH.join(self.backupDirectory, '*.json')):
            
            try:
                with open(currentJsonFile, 'r') as fsStream:
                    lstDataJson = json.load(fsStream)
            except BaseException as err:
                WiflyUtils.writeLog(logging.CRITICAL, 'dataHandler', 'Line: ' + str(WiflyUtils.lineno()) + '. Unable to load the data from the JSON file: ' + currentJsonFile + '. Error: ' + str(err))
            
            # Create new threads
            threadSender = myThreadSender(nthreadCounter, "Thread-Json-id-" + str(nthreadCounter), lstDataJson, currentJsonFile, '', self.sendurl, False)
            nthreadCounter += 1
            
            # Add threads to thread list
            lstThreads.append(threadSender)
            
            # Starts the thread sender to send the data
            threadSender.start()

class myThreadKismetRestarter(threading.Thread):
    def __init__(self, threadID, threadName):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = threadName
    def run(self):
        print "Starting " + self.name
        
        WiflyUtils.kismetRestarter('kismet_server', False)

class myThreadSendErrors(threading.Thread):
    def __init__(self, threadID, threadName, logFilePath):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = threadName
        self.logFilePath = logFilePath
    def run(self):
        print "Starting " + self.name
        
        # Check if the log file exists
        if (PATH.exists(self.logFilePath)):
            data = ''
            try:
                with open(self.logFilePath, 'r') as fsStream:
                    data = fsStream.read()
            except:
                print 'Unable to read from the errors file:', self.logFilePath
            
            # Checks if there are errors
            if (data != ''):
                global nthreadCounter
                
                # Creates the data in a format for the sender to work with
                data = data[:-1].strip()
                lstData = []
                for currentErrorLine in data.split('\n'):
                    keyValues = currentErrorLine.split('~~')
                    error = {}
                    for keyvalue in keyValues:
                        splitkeyvalue = keyvalue.split('$$')
                        key = splitkeyvalue[0]
                        value = splitkeyvalue[1]
                        error[key] = value
                    lstData.append(error)
                
                sendurl = WiflyUtils.readConfigValue('server-url-send-errors')
                
                # Create new threads
                threadSender = myThreadSender(nthreadCounter, "Thread-Errors-Sender-id-" + str(nthreadCounter), lstData, self.logFilePath, '', sendurl, False)
                nthreadCounter = nthreadCounter + 1
                
                # Add threads to thread list
                lstThreads.append(threadSender)
                
                # Starts the thread sender to send the data
                threadSender.start()
                
                # Wait until all errors were sent
                threadSender.join()
    
def main():
    # Threading objects
    global nthreadCounter
    global lstThreads
    
    logFilePath = WiflyUtils.readConfigValue('error-log-file-path')
    threadErrorSender = myThreadSendErrors(nthreadCounter, 'Thread-Erros-id-' + str(nthreadCounter), logFilePath)
    nthreadCounter += 1
    
    # Add threads to thread list
    lstThreads.append(threadErrorSender)
     
    # Start new Threads
    threadErrorSender.start()
    
    # Waits until the error sending ended
    threadErrorSender.join()
     
    # The directory of the kismet log files + backup files
    kismet_directory_path = WiflyUtils.readConfigValue('kismet-wifly-directory')            
    
    # The directory of the kismet log files + the netxml files extention
    kismet_logs_directory_path = PATH.join(kismet_directory_path, WiflyUtils.readConfigValue('kismet-logs-directory'))
    
    # Checks if the kismet directory exists
    if not PATH.exists(kismet_directory_path):
        try:
            os.makedirs(kismet_directory_path)
            os.makedirs(kismet_logs_directory_path)
        except BaseException as err:
            WiflyUtils.writeLog(logging.CRITICAL, 'dataHandler', 'Line: ' + str(WiflyUtils.lineno()) + '. Kismet directory was not found where was expected. Cannot create it: ' + kismet_logs_directory_path + '. Error: ' + str(err))
    
    # Check if the kismet directory of log files does NOT exists
    elif not PATH.exists(kismet_logs_directory_path):
        try:
            os.makedirs(kismet_logs_directory_path)
        except BaseException as err:
            WiflyUtils.writeLog(logging.CRITICAL, 'dataHandler', 'Line: ' + str(WiflyUtils.lineno()) + '. Kismet directory was not found where was expected. Cannot create it: ' + kismet_logs_directory_path + '. Error: ' + str(err))
    
    # If the logs directory does exists - start parsing
    # We do IF and not ELSE to save 1 run of the script at startup until we will create the kismet directories
    if (PATH.exists(kismet_logs_directory_path)):
        
        threadKismetRestarter = myThreadKismetRestarter(nthreadCounter, 'Thread-Kismet-Restarter-id-' + str(nthreadCounter))
        
        # Add threads to thread list
        lstThreads.append(threadKismetRestarter)
         
        # Start new Threads
        threadKismetRestarter.start()
        
        nthreadCounter += 1
        
        # Gets the backup directory from the config file
        backup_logs_directory = PATH.join(kismet_directory_path, WiflyUtils.readConfigValue('kismet-backup-logs-directory'))
        
        # Checks if the directory path is valid
        if (backup_logs_directory == ''):
            WiflyUtils.writeLog(logging.CRITICAL, 'dataHandler', 'Line: ' + str(WiflyUtils.lineno()) + '. The \'kismet-backup-logs-directory\' in the config file has no value or the key doesn\' exists')
        else:
            # Checks if the backups directory exists. If not, creates it
            if (not PATH.exists(backup_logs_directory)):
                os.makedirs(backup_logs_directory)
            
            sendurl = WiflyUtils.readConfigValue('server-url-send-data')
            
            # Creates the thread that will check for json backups files and send them
            threadJson = myThreadJsonSender(nthreadCounter, 'Thread-JsonSender-id-' + str(nthreadCounter), backup_logs_directory, sendurl)
            
            # Add threads to thread list
            lstThreads.append(threadJson)
            
            nthreadCounter += 1
            
            # Start new Threads
            threadJson.start()
            
            nNetXmlBackupCounter = 0
            # A loop that copies all the files from the kismet log directory to the backups directory
            for currentNetFile in glob.glob(PATH.join(kismet_logs_directory_path, '*.netxml')):
                try:
                    # We use this method of reading an writing the data instead of using the shutil.copy2
                    # We do that because this is the safets way to copy the data without getting the error:
                    ## IOError: [Errno 9] Bad file descriptor.
                    with file(currentNetFile, 'r') as original:
                        data = original.read()
                    with file(PATH.join(backup_logs_directory, datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + '-' + str(nNetXmlBackupCounter) + '.netxml'), 'w') as modified:
                        modified.write(data)
                except BaseException as err:
                    WiflyUtils.writeLog(logging.WARNING, 'dataHandler', 'Line: ' + str(WiflyUtils.lineno()) + '. Could not copy netxml file: ' + currentNetFile + '. Error: ' + str(err))
                else:
                    isDeleteWentWell = WiflyUtils.deleteFile('dataHandler', currentNetFile)
                    
                    # Checks that we couldn't delete the file.
                    # If so, delete the backup file
                    # We check for this just in case there was a problem but the file WAS deleted.
                    # So we won't lose any data and also delete the backupfile
                    if ((not isDeleteWentWell) and PATH.exists(currentNetFile)):
                        WiflyUtils.deleteFile('dataHandler', PATH.join(backup_logs_directory, PATH.basename(currentNetFile)))
                    else:
                        nNetXmlBackupCounter +=1
            
            restartKismetIfNecessary(nNetXmlBackupCounter, kismet_logs_directory_path, backup_logs_directory)
                
            # A loop that runs ofer all the log files in the kismet directory.
            # Only the files that match: *.netxml
            for currentBackupNetFile in glob.glob(PATH.join(backup_logs_directory, '*.netxml')):
                tree = ET.ElementTree()
                
                try:
                    # Gets the xml tree
                    tree = ET.parse(currentBackupNetFile)
                except BaseException as err:
                    WiflyUtils.deleteFile('dataHandler', currentBackupNetFile)
                else:
                    # Gets the root of the tree
                    root = tree.getroot()
                
                    # Gets the device node - contains all of the wanted devices
                    networks = root.findall('wireless-network')
                    
                    lstData = []
                    global mc
                
                    # A loop that runs over all the wifi networks
                    for currentWifiNetwork in networks:
                        # Gets the BSSID of the wifi network
                        bssid = WiflyUtils.getElementText(currentWifiNetwork, 'BSSID')
                        
                        # Gets all the client connected to the current wifi network
                        wifiClients = currentWifiNetwork.findall('wireless-client')
                        
                        # A loop that runs over all the clients
                        for currentClient in wifiClients:
                            dClientData = {}
                            
                            # Gets the mac address of the client
                            clientMacAddress = WiflyUtils.getElementText(currentClient, 'client-mac')
                            
                            # Gets the last time seen of the client
                            lastTimeSeenDateObject = parser.parse(currentClient.get('last-time'))
                            
                            updateMaxLastTime(lastTimeSeenDateObject)
                            
                            # Checks if this is the first time or that the current time bigger than the last run max time
                            # If so, the row should enter to the db
                            if (not ((keyMaxTimeLastRun in mc) and lastTimeSeenDateObject < mc.get(keyMaxTimeLastRun))):
                                lastTimeSeen = str(lastTimeSeenDateObject)
                                
                                # Gets the last signle dbm of the client
                                snrInfoElement = currentClient.find('snr-info')
                                lastSignleDbm = WiflyUtils.getElementText(snrInfoElement, 'last_signal_dbm')
                                
                                # Adda all the data to the list to be sent
                                dClientData['mac'] = clientMacAddress
                                dClientData['bssid'] = bssid
                                dClientData['power'] = lastSignleDbm
                                dClientData['timestamp'] = calendar.timegm(lastTimeSeenDateObject.utctimetuple())
                                lstData.append(dClientData)
                    
                    # Checks if we need to send new data
                    if (len(lstData) > 0):        
                        # Create new threads
                        threadSender = myThreadSender(nthreadCounter, "Thread-Sender-id-" + str(nthreadCounter), lstData, currentBackupNetFile, backup_logs_directory, sendurl, True)
                        nthreadCounter += 1
                        
                        # Add threads to thread list
                        lstThreads.append(threadSender)
                        
                        # Start new Threads
                        threadSender.start()
                    # Deletes the netxml file if no clients were found in it
                    else:
                        WiflyUtils.deleteFile('dataHandler-main', currentBackupNetFile)
                
    # Wait for all threads to complete
    for threadCurrent in lstThreads:
        threadCurrent.join()
    
    restartInternetIfNecessary()
    
    # Check if the memory cache exists
    if (mc is not None):
        mc.set(keyMaxTimeLastRun, mc.get(keyCurrentMaxTime))
    
    print "Exiting Main Thread. Done parsing."
    sys.exit(0)

def updateMaxLastTime(date):
    global mc
    global keyCurrentMaxTime
    
    # Checks if we succeded to connect to the memory cache
    if (mc is not None):
        # If this is the first time the value is inserted to the memory cache
        if (not(keyCurrentMaxTime in mc)):
            mc.set(keyCurrentMaxTime, date)
        # If the current date is bigger than the current max date
        elif (date > mc.get(keyCurrentMaxTime)):
            mc.set(keyCurrentMaxTime, date)
    else:
        mc = WiflyUtils.openMemoryCache()

#=======================================================================================
# Method Description: The method checks if we need to restart kismet.
# Parameters:   nNetXmlBackupCounter = the number of netxml files read by the system after kismet log it
#               kismetLogsPath = the path of thekismet logs directory
#               kismetBackupDirectory = the backup kismet directory path
# Return Value: None.
# Aditional Info: We restart kismet when we go over the max time of times we allow not to get netxml files in a raw.
#                 Also, if we don't have enough space on the partition, we are deleting the oldest json file  
#=======================================================================================
def restartKismetIfNecessary(nNetXmlBackupCounter, kismetLogsPath, kismetBackupDirectory):
    stringCurrentFailureTimesKismet = WiflyUtils.readFailureValue('kismet-current-failures-times')
    
    # Checks if we didn't get any kismet log files
    # If so, check if we need to restart kismet, and if not increment the
    # numbers of times in a raw kismet failed to log
    if (nNetXmlBackupCounter == 0):
        maxTimesAllowed = int(WiflyUtils.readConfigValue('failure-kismet-not-logging-max-times'))
        if (stringCurrentFailureTimesKismet != ''):
            nCurrentFailureTimesKismet = int(stringCurrentFailureTimesKismet)
            newValueToUpdate = 0
            
            # Check if went over the max times allowed
            if (nCurrentFailureTimesKismet + 1 >= maxTimesAllowed):
                isRunOutOfSpace = checkRunOutOfSpace(kismetLogsPath)
                
                # Checks if we ran out of space on the partition
                if (isRunOutOfSpace):
                    oldestFileToDelete = findOldestFile('json', kismetBackupDirectory)
                    if (oldestFileToDelete != ''):
                        WiflyUtils.deleteFile(oldestFileToDelete)
                    
                doesAllWentWell = WiflyUtils.kismetRestarter('kismet_server', True)
                if (not doesAllWentWell):
                    newValueToUpdate = nCurrentFailureTimesKismet + 1
            else:
                newValueToUpdate = nCurrentFailureTimesKismet + 1
            
            WiflyUtils.updateFailureValue('kismet-current-failures-times', newValueToUpdate)
    # The kismet started to work again - reset the failures
    elif (stringCurrentFailureTimesKismet != '' and int(stringCurrentFailureTimesKismet) > 0):
        WiflyUtils.updateFailureValue('kismet-current-failures-times', 0)

#=======================================================================================
# Method Description: The method returns the oldest file with the wanted extention in the wanted directory
# Parameters:   fileExtention = the wanted file extention
#               searchDirectory = the wanted directory to search inside it
# Return Value: The path of the oldest file
# Aditional Info: None.
#=======================================================================================
def findOldestFile(fileExtention, searchDirectory):
    oldest = ''
    try:
        gt = os.path.getmtime
        oldest = min([(currentfile, gt(currentfile)) for currentfile in glob.glob(PATH.join(searchDirectory, '*.'+ fileExtention))])[0]
    except BaseException as err:
        WiflyUtils.writeLog(logging.ERROR, 'dataHandler-findOldestFile', 'Line: ' + str(WiflyUtils.lineno()) + '. Can\'t get the oldest json file in the backup directory. Error: ' + str(err))
    return oldest

#=======================================================================================
# Method Description: The method checks if we got less memory than we ok with (in the config file)
# Parameters: path = the path of the file / directory to check its partition
# Return Value: The free space n KB(!!!)
# Aditional Info: None.
#=======================================================================================
def checkRunOutOfSpace(path):
    try:
        st = os.statvfs(path)
        
        # Free space in KB
        free = (st.f_bavail * st.f_frsize) / 1024
        
        minFreeSpaceString = WiflyUtils.readConfigValue('min-free-space-kb')
        
        if (minFreeSpaceString != ''):
            # Checks if the free space is smaller than a choosen space limit
            if (free <= int(minFreeSpaceString)):
                return True
            else:
                return False
        else:
            WiflyUtils.writeLog(logging.ERROR, 'dataHandler-checkRunOutOfSpace', 'Line: ' + str(WiflyUtils.lineno()) + '. The key: min-free-space-kb, doesn\'t exists in the config file.')
            return True
    except BaseException as err:
        WiflyUtils.writeLog(logging.ERROR, 'dataHandler-checkRunOutOfSpace', 'Line: ' + str(WiflyUtils.lineno()) + '. Cannot check partition free space. Error: ' + str(err))

#=======================================================================================
# Method Description: The method cchecks if we need to restart the internet connection.
# Parameters: None.
# Return Value: None.
# Aditional Info: We restart the internet if we go over the max times we allow not to have internet connection in a raw.
#=======================================================================================
def restartInternetIfNecessary():
    nCurrentInternetFailureTimes = int(WiflyUtils.readFailureValue('internet-connection-current-failues-times'))
    nMaxInternetFailuresTimes = int(WiflyUtils.readConfigValue('failure-internet-connection-max-times'))
    
    # Checks if we need to restart the internet
    if (nCurrentInternetFailureTimes != '' and
        nMaxInternetFailuresTimes != '' and
        nCurrentInternetFailureTimes >= nMaxInternetFailuresTimes):
        doesInternetRestartWentWell = WiflyUtils.restartInternetConnection()
        
        if (doesInternetRestartWentWell):
            WiflyUtils.updateFailureValue('internet-connection-current-failues-times', 0)

if __name__ == '__main__':
    main()