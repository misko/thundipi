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


#this toggles the LED on the thunderboard
p = Peripheral("58:8e:81:a5:4a:6a")
services=p.getServices()
for service in services:
    s = p.getServiceByUUID(service.uuid)
    if s.uuid!='00001815-0000-1000-8000-00805f9b34fb':
        continue
    char_button,char_led=s.getCharacteristics('2a56')
    led=struct.unpack('B', char_led.read())[0]
    char_led.write(struct.pack('B',1-led),withResponse=True)
exit()
while True:
    #print(scan())
    scanner = Scanner().withDelegate(ScanDelegate())
    devices = scanner.scan(10.0)

    for dev in devices:
        print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi),dev)
        for (adtype, desc, value) in dev.getScanData():
            print("  %s = %s" % (desc, value))
    exit()
