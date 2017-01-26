'''
/*
 * Copyright 2010-2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License").
 * You may not use this file except in compliance with the License.
 * A copy of the License is located at
 *
 *  http://aws.amazon.com/apache2.0
 *
 * or in the "license" file accompanying this file. This file is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 * express or implied. See the License for the specific language governing
 * permissions and limitations under the License.
 */
 '''

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import sys
import logging
import time
import json
import getopt

import requests
import arrow
import RPi.GPIO as GPIO


import os
import spidev
import time

# Function to convert digital data to Volts
def Volts(data, places, Vref):
  return round((data * Vref) / float(4096), places)

# Function to read Digital Data from a MCP3208 channel
# Channel 0-7
def ReadADCChannel(channel):
  adc = spi.xfer2([6 + ((channel&4) >> 2),(channel&3) << 6, 0])
  data = ((adc[1] & 15) << 8) + adc[2]
  return data

# Custom Shadow update callback
def customShadowCallback_Update(payload, responseStatus, token):
	# payload is a JSON string ready to be parsed using json.loads(...)
	# in both Py2.x and Py3.x
	if responseStatus == "timeout":
		print("Update request " + token + " time out!")
	if responseStatus == "accepted":
		payloadDict = json.loads(payload)
		print("~~~~~~~~~~~~~~~~~~~~~~~")
		print("Update request with token: " + token + " accepted!")
		#print("property: " + str(payloadDict["state"]["desired"]["property"]))
		print("~~~~~~~~~~~~~~~~~~~~~~~\n\n")
	if responseStatus == "rejected":
		print("Update request " + token + " rejected!")


def customShadowCallback_Get(payload, responseStatus, token):
	# Get desired state
	payloadDict = json.loads(payload)
	print "payload is: " + payload
	"""
	print payloadDict
        print "desired state:"
        print payloadDict['state']['desired']
	
        print "current reported state:"
        print payloadDict['state']['reported']
	# Set reported state
	payloadDict['state']['reported'] = dict(payloadDict['state']['desired'])
        jsonDict =  '{"state":{"reported":' + json.dumps(payloadDict['state']['reported']) + '}, "desired":null}'
	print "calc New state:"
        print jsonDict
	print "Calling updater..."
	Bot.shadowUpdate(jsonDict, customShadowCallback_Update, 5)
	print "Finished updating to new state."
	"""

# Custom Shadow callback
def customShadowCallback_Delta(payload, responseStatus, token):
	# payload is a JSON string ready to be parsed using json.loads(...)
	# in both Py2.x and Py3.x
	print(responseStatus)
	#payloadDict = json.loads(payload)
        Bot.shadowGet(customShadowCallback_Get, 5)
	#print payloadDict
	#print("++++++++DELTA++++++++++")
	#print("property: " + str(payloadDict["state"]["pwm"]))
	#print("property: " + str(payloadDict["state"]["manualOverride"]))
        #JSONPayload = '{"state":{"reported":{"pwm":' + str(payloadDict["state"]["pwm"]) + ', "manualOverride":"' + payloadDict["state"]["manualOverride"] + '"}}}'
        #print JSONPayload
	#Bot.shadowUpdate(JSONPayload, customShadowCallback_Update, 5)


# Usage
usageInfo = """Usage:

Use certificate based mutual authentication:
python basicShadowDeltaListener.py -e <endpoint> -r <rootCAFilePath> -c <certFilePath> -k <privateKeyFilePath>

Use MQTT over WebSocket:
python basicShadowDeltaListener.py -e <endpoint> -r <rootCAFilePath> -w

Type "python basicShadowDeltaListener.py -h" for available options.


"""
# Help info
helpInfo = """-e, --endpoint
	Your AWS IoT custom endpoint
-r, --rootCA
	Root CA file path
-c, --cert
	Certificate file path
-k, --key
	Private key file path
-w, --websocket
	Use MQTT over WebSocket
-h, --help
	Help information


"""

# Read in command-line parameters
useWebsocket = False
host = ""
rootCAPath = ""
certificatePath = ""
privateKeyPath = ""
try:
	opts, args = getopt.getopt(sys.argv[1:], "hwe:k:c:r:", ["help", "endpoint=", "key=","cert=","rootCA=", "websocket"])
	if len(opts) == 0:
		raise getopt.GetoptError("No input parameters!")
	for opt, arg in opts:
		if opt in ("-h", "--help"):
			print(helpInfo)
			exit(0)
		if opt in ("-e", "--endpoint"):
			host = arg
		if opt in ("-r", "--rootCA"):
			rootCAPath = arg
		if opt in ("-c", "--cert"):
			certificatePath = arg
		if opt in ("-k", "--key"):
			privateKeyPath = arg
		if opt in ("-w", "--websocket"):
			useWebsocket = True
except getopt.GetoptError:
	print(usageInfo)
	exit(1)

# Missing configuration notification
missingConfiguration = False
if not host:
	print("Missing '-e' or '--endpoint'")
	missingConfiguration = True
if not rootCAPath:
	print("Missing '-r' or '--rootCA'")
	missingConfiguration = True
if not useWebsocket:
	if not certificatePath:
		print("Missing '-c' or '--cert'")
		missingConfiguration = True
	if not privateKeyPath:
		print("Missing '-k' or '--key'")
		missingConfiguration = True
if missingConfiguration:
	exit(2)

# Configure logging
logger = logging.getLogger("AWSIoTPythonSDK.core")
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

# Init AWSIoTMQTTShadowClient
myAWSIoTMQTTShadowClient = None
if useWebsocket:
	myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient("HumiditySensor", useWebsocket=True)
	myAWSIoTMQTTShadowClient.configureEndpoint(host, 443)
	myAWSIoTMQTTShadowClient.configureCredentials(rootCAPath)
else:
	myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient("HumiditySensor")
	myAWSIoTMQTTShadowClient.configureEndpoint(host, 8883)
	myAWSIoTMQTTShadowClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

# AWSIoTMQTTShadowClient configuration
#myAWSIoTMQTTShadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTShadowClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTShadowClient.configureMQTTOperationTimeout(5)  # 5 sec

# Connect to AWS IoT
myAWSIoTMQTTShadowClient.connect()
myDeviceShadow = myAWSIoTMQTTShadowClient.createShadowHandlerWithName("humidity_sensor_1", True)


# Create a deviceShadow with persistent subscription
#Bot = myAWSIoTMQTTShadowClient.createShadowHandlerWithName("humiditySensors", True)

# Listen on deltas
#Bot.shadowRegisterDeltaCallback(customShadowCallback_Delta)

# Reference Voltage, Jumper selected 5.0 (default), 3.3, 1.0, or 0.3 Volts
Vref = 5.0
#Vref = 3.3

# (jumper CE0 on) chip = 0 (default), (jumper CE1 on) chip = 1
chip = 0

# Open SPI bus
spi = spidev.SpiDev()
spi.open(0, chip)

# Loop forever
while True:
	v = []
        v.append(str(Volts(ReadADCChannel(0), 2, Vref)/Vref*100))
        v.append(str(Volts(ReadADCChannel(1), 2, Vref)/Vref*100))
        v.append(str(Volts(ReadADCChannel(2), 2, Vref)/Vref*100))
        v.append(str(Volts(ReadADCChannel(3), 2, Vref)/Vref*100))
        v.append(str(Volts(ReadADCChannel(4), 2, Vref)/Vref*100))
        v.append(str(Volts(ReadADCChannel(5), 2, Vref)/Vref*100))
        v.append(str(Volts(ReadADCChannel(6), 2, Vref)/Vref*100))
        v.append(str(Volts(ReadADCChannel(7), 2, Vref)/Vref*100))

	print v
	voltagePayload = '{"state":{"reported":{"humidity_percentages":[' + ','.join(v) + ']}}}' 
	print voltagePayload
	myDeviceShadow.shadowGet(customShadowCallback_Get, 5)
        myDeviceShadow.shadowUpdate(voltagePayload, customShadowCallback_Update, 5)

	time.sleep(2)
