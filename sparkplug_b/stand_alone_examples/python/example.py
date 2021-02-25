#!/usr/bin/python
"""
********************************************************************************
* Copyright (c) 2014, 2018 Cirrus Link Solutions and others
*
* This program and the accompanying materials are made available under the
* terms of the Eclipse Public License 2.0 which is available at
* http://www.eclipse.org/legal/epl-2.0.
*
* SPDX-License-Identifier: EPL-2.0
*
* Contributors:
*   Cirrus Link Solutions - initial implementation
********************************************************************************
"""
import sys
import time
import random
import string
import paho.mqtt.client as mqtt
sys.path.insert(0, "../../../client_libraries/python/")
#print(sys.path)
import sparkplug_b as sparkplug
from sparkplug_b import *

# Application variables
server_url = "localhost"
server_port = 61883
spb_namespace = "spBv1.0"
myGroupId = "Sparkplug B Devices"
myNodeName = "Python Edge Node 1"
myDeviceName = "Emulated Device"
#publishPeriod = 5000
myUsername = "admin"
myPassword = "changeme"
client = None

class AliasMap:
    Next_Server = 0
    Rebirth = 1
    Reboot = 2
    Dataset = 3
    Node_Metric0 = 4
    Node_Metric1 = 5
    Node_Metric2 = 6
    Node_Metric3 = 7
    Device_Metric0 = 8
    Device_Metric1 = 9
    Device_Metric2 = 10
    Device_Metric3 = 11
    My_Custom_Motor = 12

def on_connect(client, userdata, flags, rc):
    """The callback for when the client receives a CONNACK response from the server.
    """
    print(f"on_connect(): result code = {rc} ({mqtt.connack_string(rc)})")
    if rc != 0:
        sys.exit()
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe(spb_namespace + "/" + myGroupId + "/NCMD/" + myNodeName + "/#")
    client.subscribe(spb_namespace + "/" + myGroupId + "/DCMD/" + myNodeName + "/#")

def on_disconnect(client, userdata, rc):
    """The callback for when the client is disconnected from the server.
    """
    print(f"on_disconnect(): result code = {rc} ({mqtt.connack_string(rc)})")

def on_message(client, userdata, msg):
    """The callback for when a PUBLISH message is received from the server.
    """
    print(f"on_message(): message received: Topic: {msg.topic}, QoS: {msg.qos}, Payload Length: {len(msg.payload)}")
    (namespace, group_id, message_type, *last) = msg.topic.split("/")
    (edge_node_id, device_id) = (last[0], None if len(last) == 1 else last[1])
    if namespace != spb_namespace:
        print("Unknown/unsupported namespace: " + namespace)
    elif group_id != myGroupId:
        print("Unknown group_id: " + group_id)
    elif message_type not in ("NCMD", "DCMD"):
        print("Unsupported message_type: " + message_type)
    elif edge_node_id != myNodeName:
        print("Unknown edge_node_id: " + edge_node_id)
    else:
        inboundPayload = sparkplug_b_pb2.Payload()
        inboundPayload.ParseFromString(msg.payload)
        for metric in inboundPayload.metrics:
            if metric.name == "Node Control/Next Server" or metric.alias == AliasMap.Next_Server:
                # 'Node Control/Next Server' is an NCMD used to tell the device/client application to
                # disconnect from the current MQTT server and connect to the next MQTT server in the
                # list of available servers.  This is used for clients that have a pool of MQTT servers
                # to connect to.
                print("'Node Control/Next Server' is not implemented in this example")
            elif metric.name == "Node Control/Rebirth" or metric.alias == AliasMap.Rebirth:
                # 'Node Control/Rebirth' is an NCMD used to tell the device/client application to resend
                # its full NBIRTH and DBIRTH again.  MQTT Engine will send this NCMD to a device/client
                # application if it receives an NDATA or DDATA with a metric that was not published in the
                # original NBIRTH or DBIRTH.  This is why the application must send all known metrics in
                # its original NBIRTH and DBIRTH messages.
                publishBirth()
            elif metric.name == "Node Control/Reboot" or metric.alias == AliasMap.Reboot:
                # 'Node Control/Reboot' is an NCMD used to tell a device/client application to reboot
                # This can be used for devices that need a full application reset via a soft reboot.
                # In this case, we fake a full reboot with a republishing of the NBIRTH and DBIRTH
                # messages.
                publishBirth()
            elif metric.name == "output/Device Metric2" or metric.alias == AliasMap.Device_Metric2:
                # This is a metric we declared in our DBIRTH message and we're emulating an output.
                # So, on incoming 'writes' to the output we must publish a DDATA with the new output
                # value.  If this were a real output we'd write to the output and then read it back
                # before publishing a DDATA message.

                # We know this is an Int16 because of how we declated it in the DBIRTH
                newValue = metric.int_value
                print("CMD message for output/Device Metric2 - New Value: {}".format(newValue))

                # Create the DDATA payload - Use the alias because this isn't the DBIRTH
                payload = sparkplug.getDdataPayload()
                addMetric(payload, None, AliasMap.Device_Metric2, MetricDataType.Int16, newValue)

                # Publish a message data
                byteArray = bytearray(payload.SerializeToString())
                client.publish(spb_namespace + "/" + myGroupId + "/DDATA/" + myNodeName + "/" + myDeviceName, byteArray, 0, False)
            elif metric.name == "output/Device Metric3" or metric.alias == AliasMap.Device_Metric3:
                # This is a metric we declared in our DBIRTH message and we're emulating an output.
                # So, on incoming 'writes' to the output we must publish a DDATA with the new output
                # value.  If this were a real output we'd write to the output and then read it back
                # before publishing a DDATA message.

                # We know this is an Boolean because of how we declated it in the DBIRTH
                newValue = metric.boolean_value
                print("CMD message for output/Device Metric3 - New Value: %r" % newValue)

                # Create the DDATA payload - use the alias because this isn't the DBIRTH
                payload = sparkplug.getDdataPayload()
                addMetric(payload, None, AliasMap.Device_Metric3, MetricDataType.Boolean, newValue)

                # Publish a message data
                byteArray = bytearray(payload.SerializeToString())
                client.publish(spb_namespace + "/" + myGroupId + "/DDATA/" + myNodeName + "/" + myDeviceName, byteArray, 0, False)
            else:
                #print("Unknown metric: " + repr(metric))
                print(f"Unknown metric: name='{metric.name}', alias={metric.alias}")

def on_publish(client, userdata, mid):
    """The callback for when a message has been published to the server.
    """
    print(f"on_publish(): message published: msg id = {mid}")

def on_subscribe(client, userdata, mid, granted_qos):
    """The callback for when a server responds to a subscribe request.
    """
    print(f"on_subscribe(): subscribed: msg id = {mid}, granted_qos = {granted_qos}")

def publishBirth():
    """Publish the BIRTH certificates.
    """
    publishNodeBirth()
    publishDeviceBirth()

def publishNodeBirth():
    """Publish the NBIRTH certificate.
    """
    print("Publishing Node Birth")

    # Create the node birth payload
    payload = sparkplug.getNodeBirthPayload()

    # Set up the Node Controls
    addMetric(payload, "Node Control/Next Server", AliasMap.Next_Server, MetricDataType.Boolean, False)
    addMetric(payload, "Node Control/Rebirth", AliasMap.Rebirth, MetricDataType.Boolean, False)
    addMetric(payload, "Node Control/Reboot", AliasMap.Reboot, MetricDataType.Boolean, False)

    # Add some regular node metrics
    addMetric(payload, "Node Metric0", AliasMap.Node_Metric0, MetricDataType.String, "hello node")
    addMetric(payload, "Node Metric1", AliasMap.Node_Metric1, MetricDataType.Boolean, True)
    addNullMetric(payload, "Node Metric3", AliasMap.Node_Metric3, MetricDataType.Int32)

    # Create a DataSet (012 - 345) two rows with Int8, Int16, and Int32 contents and headers Int8s, Int16s, Int32s and add it to the payload
    columns = ["Int8s", "Int16s", "Int32s"]
    types = [DataSetDataType.Int8, DataSetDataType.Int16, DataSetDataType.Int32]
    dataset = initDatasetMetric(payload, "DataSet", AliasMap.Dataset, columns, types)
    row = dataset.rows.add()
    element = row.elements.add();
    element.int_value = 0
    element = row.elements.add();
    element.int_value = 1
    element = row.elements.add();
    element.int_value = 2
    row = dataset.rows.add()
    element = row.elements.add();
    element.int_value = 3
    element = row.elements.add();
    element.int_value = 4
    element = row.elements.add();
    element.int_value = 5

    # Add a metric with a custom property
    metric = addMetric(payload, "Node Metric2", AliasMap.Node_Metric2, MetricDataType.Int16, 13)
    metric.properties.keys.extend(["engUnit"])
    propertyValue = metric.properties.values.add()
    propertyValue.type = ParameterDataType.String
    propertyValue.string_value = "MyCustomUnits"

    # Create the UDT definition value which includes two UDT members and a single parameter and add it to the payload
    template = initTemplateMetric(payload, "_types_/Custom_Motor", None, None)    # No alias for Template definitions
    templateParameter = template.parameters.add()
    templateParameter.name = "Index"
    templateParameter.type = ParameterDataType.String
    templateParameter.string_value = "0"
    addMetric(template, "RPMs", None, MetricDataType.Int32, 0)    # No alias in UDT members
    addMetric(template, "AMPs", None, MetricDataType.Int32, 0)    # No alias in UDT members

    # Publish the node birth certificate
    byteArray = bytearray(payload.SerializeToString())
    client.publish(spb_namespace + "/" + myGroupId + "/NBIRTH/" + myNodeName, byteArray, 0, False)

def publishDeviceBirth():
    """Publish the DBIRTH certificate.
    """
    print("Publishing Device Birth")

    # Get the payload
    payload = sparkplug.getDeviceBirthPayload()

    # Add some device metrics
    addMetric(payload, "input/Device Metric0", AliasMap.Device_Metric0, MetricDataType.String, "hello device")
    addMetric(payload, "input/Device Metric1", AliasMap.Device_Metric1, MetricDataType.Boolean, True)
    addMetric(payload, "output/Device Metric2", AliasMap.Device_Metric2, MetricDataType.Int16, 16)
    addMetric(payload, "output/Device Metric3", AliasMap.Device_Metric3, MetricDataType.Boolean, True)

    # Create the UDT definition value which includes two UDT members and a single parameter and add it to the payload
    template = initTemplateMetric(payload, "My_Custom_Motor", AliasMap.My_Custom_Motor, "Custom_Motor")
    templateParameter = template.parameters.add()
    templateParameter.name = "Index"
    templateParameter.type = ParameterDataType.String
    templateParameter.string_value = "1"
    addMetric(template, "RPMs", None, MetricDataType.Int32, 123)    # No alias in UDT members
    addMetric(template, "AMPs", None, MetricDataType.Int32, 456)    # No alias in UDT members

    # Publish the initial data with the Device BIRTH certificate
    totalByteArray = bytearray(payload.SerializeToString())
    client.publish(spb_namespace + "/" + myGroupId + "/DBIRTH/" + myNodeName + "/" + myDeviceName, totalByteArray, 0, False)


######################################################################
# Main Application
######################################################################
if __name__ == '__main__':
    print("Starting main application")

    # Create the node death payload
    deathPayload = sparkplug.getNodeDeathPayload()

    # Start of main program - Set up the MQTT client connection
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.on_publish = on_publish
    client.on_subscribe = on_subscribe
    client.username_pw_set(myUsername, myPassword)
    deathByteArray = bytearray(deathPayload.SerializeToString())
    client.will_set(spb_namespace + "/" + myGroupId + "/NDEATH/" + myNodeName, deathByteArray, 0, False)
    client.connect(server_url, server_port, 60)

    # Short delay to allow connect callback to occur
    time.sleep(0.1)
    client.loop()

    # Publish the birth certificates
    publishBirth()

    while True:
        # Periodically publish some new data
        payload = sparkplug.getDdataPayload()

        # Add some random data to the inputs
        addMetric(payload, None, AliasMap.Device_Metric0, MetricDataType.String, ''.join(random.choice(string.ascii_lowercase) for i in range(12)))

        # Note this data we're setting to STALE via the propertyset as an example
        metric = addMetric(payload, None, AliasMap.Device_Metric1, MetricDataType.Boolean, random.choice([True, False]))
        metric.properties.keys.extend(["Quality"])
        propertyValue = metric.properties.values.add()
        propertyValue.type = ParameterDataType.Int32
        propertyValue.int_value = 500

        # Publish a message
        byteArray = bytearray(payload.SerializeToString())   # SerializeToString() returns a bytes type
        client.publish(spb_namespace + "/" + myGroupId + "/DDATA/" + myNodeName + "/" + myDeviceName, byteArray, 0, False)

        # Sit and wait for inbound or outbound events
        for _ in range(5):
            time.sleep(0.1)
            client.loop()
