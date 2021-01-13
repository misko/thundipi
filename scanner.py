from bluepy.btle import Scanner, DefaultDelegate, Peripheral
import struct
from time import sleep
known_bles={
    'c1:ec:7b:ca:46:2b':'car_keys',
    'cb:65:67:9a:fe:65':'bubs',
    'e2:4e:71:ce:bd:00':'daisy'
    }

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print("Discovered device", dev.addr)
        elif isNewData:
            print("Received new data from", dev.addr)
        return


def scan():
    scanner = Scanner().withDelegate(ScanDelegate())
    devices = scanner.scan(10.0)
    keys = list(known_bles.keys())
    keys.sort()
    addrs_found = {} 
    for dev in devices:
        addrs_found[dev.addr]=dev
    whos_here = []
    for key in keys:
        if key in addrs_found:
            # thing is here
            whos_here.append( (known_bles[key], addrs_found[key].rssi)) 
        else:
            #thing is not here
            whos_here.append( (known_bles[key], -1000))
    return whos_here,addrs_found

while False:
    #print(scan())
    scanner = Scanner().withDelegate(ScanDelegate())
    devices = scanner.scan(10.0)

    for dev in devices:
        print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi),dev)
        for (adtype, desc, value) in dev.getScanData():
            print("  %s = %s" % (desc, value))
    exit()
#this toggles the LED on the thunderboard
#p = Peripheral("58:8e:81:a5:4a:6a")
p = Peripheral("58:8e:81:a5:47:b4")
services=p.getServices()
for service in services:
    s = p.getServiceByUUID(service.uuid)
    #print("X",s,s.uuid,s.uuid.getCommonName())
    if False and s.uuid.getCommonName()=='Generic Access':
        for c in s.getCharacteristics():
            if c.uuid.getCommonName()=='Device Name':
                print(c.read())
                device_name=c.read().decode().rstrip('\x00')
                for x in device_name:
                    print("|%s|" % x,ord(x))
                print(device_name,"|%s|" % device_name,len(device_name),'thundipi'==device_name)
                if device_name=='thundipi':
                    print("FOUND A THUNDI PI")
    elif s.uuid.getCommonName()=='1815':
        devs=s.getCharacteristics()
        for dev in devs:
            print(dev.propertiesToString(),dev.supportsRead(),dev.getHandle())
            print(dev.read())
        dev_values=[ struct.unpack('B', dev.read())[0] for dev in devs ] 
        for dev in devs:
            print(dev.uuid,dev.propertiesToString(),dev.getHandle())
        for idx in range(4):
            #devs[idx].write(struct.pack('B',1-devs_values[idx]),withResponse=True)
            devs[idx].write(struct.pack('B',1-dev_values[idx]),withResponse=True)
            #devs[idx].write(struct.pack('B',1-devs_values[idx]),withResponse=True)
        #print(devs_values)

    #if s.uuid!='00001815-0000-1000-8000-00805f9b34fb':
    #    continue
    #char_button,char_led=s.getCharacteristics('2a56')
    #led=struct.unpack('B', char_led.read())[0]
    #char_led.write(struct.pack('B',1-led),withResponse=True)
exit()
