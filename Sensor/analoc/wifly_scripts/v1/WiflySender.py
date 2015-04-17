import json
import pycurl
import urllib
import cStringIO
import mcrypt
import string
import random
import logging
import threading
import WiflyUtils

threadLocker = threading.Lock()
encryptionKeyExpectedSize = 32

#=======================================================================================
# Method Description: The method generates a random iv.
# Parameters:   size: The size of the iv, default value: 32.
#               chars: The set of options for the random iv characters. Default values: digits, uppercase and lowercase letters.
# Return Value: The random generated iv.
# Aditional Info: None.
#=======================================================================================
def iv_generator(size=encryptionKeyExpectedSize, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase):
    return ''.join(random.choice(chars) for x in range(size))

#=======================================================================================
# Method Description: The method decrypt the data
# Parameters:   dataToDecrypt = the data to decrypt
#               key = the encryption key
# Return Value: The decrypted data
# Aditional Info: None.
#=======================================================================================
def decryptData(dataToDecrypt, key):
    global encryptionKeyExpectedSize
    
    # Checks if the key is in the expected length
    if (len(key) != encryptionKeyExpectedSize):
        WiflyUtils.writeLog(logging.ERROR, 'WiflySender-decryptData', 'Line: ' + str(WiflyUtils.lineno()) + '. Could not encrypt the data. Expected key length is: ' + str(encryptionKeyExpectedSize) + ' But the key is: ' + str(len(key)))
        return None
    else:
        dicReplaceChars = {
                         '-' : '+',
                         '_' : '/',
                         '.' : '=',
                      }
        decryptedData = WiflyUtils.multiple_replace(dicReplaceChars, dataToDecrypt)
        
        try:
            decryptedData = decryptedData.decode('base64')
            #mc = mcrypt.MCRYPT('rijndael-256', 'ecb')
            #mc.init(key)
        except BaseException as err:
            WiflyUtils.writeLog(logging.ERROR, 'WiflySender-decryptData', 'Line: ' + str(WiflyUtils.lineno()) + '. Could not decrypt the data from the server. Error: ' + str(err))
            return None
        else:
            return decryptedData
            # Removes all the NULL strings \x00
            #return mc.decrypt(decryptedData).strip().replace('\x00', '')

#=======================================================================================
# Method Description: The method encrypt the data
# Parameters:   dataToEncrypt = the data to encrypt
#               key = the encryption key
# Return Value: The encrypt data
# Aditional Info: None.
#=======================================================================================
def encryptData(dataToEncrypt, key):
    global encryptionKeyExpectedSize
    
    # Checks if the key is in the expected length
    if (len(key) != encryptionKeyExpectedSize):
        WiflyUtils.writeLog(logging.ERROR, 'WiflySender-encryptData', 'Line: ' + str(WiflyUtils.lineno()) + '. Could not encrypt the data. Expected key length is: ' + str(encryptionKeyExpectedSize) + ' But the key is: ' + str(len(key)))
        return None
    else:
        try:
            #mc = mcrypt.MCRYPT('rijndael-256', 'ecb')
            #mc.init(key)
            #encrypted_data = mc.encrypt(dataToEncrypt)
            #encrypted_data = encrypted_data.strip()
            encrypted_data = dataToEncrypt
            encrypted_data = encrypted_data.encode('base64')
            dicReplaceChars = {
                                 '+' : '-',
                                 '/' : '_',
                                 '=' : '.',
                              }
            encrypted_data = WiflyUtils.multiple_replace(dicReplaceChars, encrypted_data)
        except BaseException as err:
            WiflyUtils.writeLog(logging.ERROR, 'WiflySender-encryptData', 'Line: ' + str(WiflyUtils.lineno()) + '. Could not encrypt the data. Error: ' + str(err))
            return None
        else:
            return encrypted_data

def __sendDataGeneral(dArrayData, url, encryptionKey):
    # Transforms the data to json
    json_to_send = json.dumps(dArrayData, separators=(',',':'), sort_keys=False)

    # Encrypt the data
    encrypted_json_to_send = encryptData(json_to_send, encryptionKey)
    
    if (encrypted_json_to_send is None):
        return None
    else:
        curlClient = pycurl.Curl()
        curlClient.setopt(curlClient.USERAGENT, WiflyUtils.readConfigValue('curl-user-agent'))
        
        # Sets the url of the php service
        curlClient.setopt(curlClient.URL, url)
        
        # Sets the request to be of the type POST
        curlClient.setopt(curlClient.POST, True)
           
        # Sets the params of the post request
        send_params = 'enc_data=' + urllib.quote(encrypted_json_to_send)
        curlClient.setopt(curlClient.POSTFIELDS, send_params)
        
        # Setting the buffer for the response to be written to
        bufResponse = cStringIO.StringIO()
        curlClient.setopt(curlClient.WRITEFUNCTION, bufResponse.write)
        
        # Setting to fail on error
        curlClient.setopt(curlClient.FAILONERROR, True)
        
        # Sets the time out for the connections
        curlClient.setopt(pycurl.CONNECTTIMEOUT, int(WiflyUtils.readConfigValue('curl-connection-timeout')))
        curlClient.setopt(pycurl.TIMEOUT, int(WiflyUtils.readConfigValue('curl-timeout')))
        
        response = ''
        
        try:
            # Performs the operation
            curlClient.perform()
    
        except pycurl.error as err:
            errno, errString = err
            WiflyUtils.writeLog(logging.WARNING, 'WiflySender-__sendDataGeneral', 'Line: ' + str(WiflyUtils.lineno()) + '. Error sending data using CURL for url: ' + url + '. CURL error code: ' + str(errno) + '. Error message: ' + errString)
            print '========'
            print 'ERROR sending the data:'
            print '========'
            print 'CURL error code:', errno
            print 'CURL error Message:', errString
            return None
        else:
            response = bufResponse.getvalue()
            try:
                json_object = json.loads(response)
            # The response is not in json format - it didn't come from the server so it must be an error
            except ValueError as err:
                WiflyUtils.writeLog(logging.WARNING, 'WiflySender-__sendDataGeneral', 'Line: ' + str(WiflyUtils.lineno()) + '. Error sending data using CURL for url: ' + url + '. Error message: ' + response)
                return None
            else:
                return json_object
        finally:
            curlClient.close()
            bufResponse.close()

#=======================================================================================
# Method Description: The method sends the data to the server
# Parameters:   lstData = the data to send
#               fileNameToDelete = the file path to delete if the operation went well
#               url = the controller url to send the data to
# Return Value: Boolean - if the operation went well or not
# Aditional Info: None.
#=======================================================================================
def sendData(lstData, fileNameToDelete, url):
    returnValue = True
    global threadLocker
    threadLocker.acquire()
    
    isConnectedOnline = WiflyUtils.isConnectedOnline()
    
    threadLocker.release()
    
    # Checks if we are connected to the internet
    if (not isConnectedOnline):
        returnValue = False
    else:
        identKey = WiflyUtils.readConfigValue('ident_key')
        identKeyEncoded = identKey.encode('base64')
        identKeyEncoded = urllib.quote(identKeyEncoded)
        url = url.format(identKeyEncoded)
        encryptionKey = WiflyUtils.readConfigValue('encryption-key')
        
        # Sets all the data to be sent
        dArrayData = {}
        dArrayData['ident_key'] = identKey
        dArrayData['data'] = lstData

        responseDictionary = __sendDataGeneral(dArrayData, url, encryptionKey)
        
        # Checks if every thing went well
        if (responseDictionary is None):
            returnValue = False
            print '\n#############################'
            print 'Data DIDN\'T send well:'
            print '###############################'
        else:
            if (not bool(responseDictionary['success'])):
                WiflyUtils.writeLog(logging.WARNING, 'WiflySender-sendData', 'Line: ' + str(WiflyUtils.lineno()) + \
                                     '. Error sending data to server. Error code: ' + str(responseDictionary['data']['errorCode']) + '. Error message: ' + str(responseDictionary['data']['developersMessage']))
                returnValue = False
                print '\n#############################'
                print 'Data DIDN\'T send well:'
                print '###############################'
            else:
                print '\n#############################'
                print 'Data sent well'
                print '###############################'
                if (fileNameToDelete != ''):
                    WiflyUtils.deleteFile('WiflySender-sendData', fileNameToDelete)
            
    return returnValue
