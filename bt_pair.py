#!/usr/bin/python
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import absolute_import, print_function, unicode_literals
import argparse
from optparse import OptionParser
import sys
import dbus
import dbus.service
import dbus.mainloop.glib
try:
  from gi.repository import GObject, GLib
except ImportError:
  import gobject as GObject
import bluezutils

BUS_NAME = 'org.bluez'
AGENT_INTERFACE = 'org.bluez.Agent1'
AGENT_PATH = "/test/agent"

bus = None
device_obj = None
pairing_dev_path = None
compact = True
devices= {}

def print_compact(address, properties):
    name = ""
    address = "<unknown>"

    for key, value in properties.items():
        if type(value) is dbus.String:
            value = str(value) #unicode(value).encode('ascii', 'replace')
        if (key == "Name"):
            name = value
        elif (key == "Address"):
            address = value

    if "Logged" in properties:
        flag = "*"
    else:
        flag = " "

    print("%s%s %s" % (flag, address, name))

    properties["Logged"] = True

def print_normal(address, properties):
    print("[ " + address + " ]")

    for key in properties.keys():
        value = properties[key]
        if type(value) is dbus.String:
            value = str(value) #unicode(value).encode('ascii', 'replace')
        if (key == "Class"):
            print("    %s = 0x%06x" % (key, value))
        else:
            print("    %s = %s" % (key, value))

    print()

    properties["Logged"] = True

def skip_dev(old_dev, new_dev):
    if not "Logged" in old_dev:
        return False
    if "Name" in old_dev:
        return True
    if not "Name" in new_dev:
        return True
    return False

def interfaces_added(path, interfaces):
    if 'org.bluez.Device1' not in interfaces:
        return
    properties = interfaces["org.bluez.Device1"]
    if not properties:
        return

    if path in devices:
        dev = devices[path]

        if compact and skip_dev(dev, properties):
            return
        devices[path] = dict(devices[path].items() + properties.items())
    else:
        devices[path] = properties

    if "Address" in devices[path]:
        address = properties["Address"]
    else:
        address = "<unknown>"

    if compact:
        print_compact(address, devices[path])
    else:
        print_normal(address, devices[path])

def properties_changed(interface, changed, invalidated, path):
    if interface != "org.bluez.Device1":
        return

    if path in devices:
        dev = devices[path]

        if compact and skip_dev(dev, changed):
            return
        devices[path] = dict(list(devices[path].items()) + list(changed.items()))
    else:
        devices[path] = changed

    if "Address" in devices[path]:
        address = devices[path]["Address"]
    else:
        address = "<unknown>"

    if compact:
        print_compact(address, devices[path])
    else:
        print_normal(address, devices[path])

def property_changed(name, value):
    if (name == "Discovering" and not value):
        mainloop.quit()

def end_discovery():
    """Handler for end of discovery"""
    mainloop.quit()
    adapter.StopDiscovery()

def ask(prompt):
    try:
        return raw_input(prompt)
    except:
        return input(prompt)

def set_trusted(path):
    props = dbus.Interface(bus.get_object("org.bluez", path),
                    "org.freedesktop.DBus.Properties")
    props.Set("org.bluez.Device1", "Trusted", True)

def dev_connect(path):
    dev = dbus.Interface(bus.get_object("org.bluez", path),
                            "org.bluez.Device1")
    dev.Connect()

class Rejected(dbus.DBusException):
    _dbus_error_name = "org.bluez.Error.Rejected"

class Agent(dbus.service.Object):
    exit_on_release = True

    def set_exit_on_release(self, exit_on_release):
        self.exit_on_release = exit_on_release

    @dbus.service.method(AGENT_INTERFACE,
                    in_signature="", out_signature="")
    def Release(self):
        print("Release")
        if self.exit_on_release:
            mainloop.quit()

    @dbus.service.method(AGENT_INTERFACE,
                    in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        print("AuthorizeService (%s, %s)" % (device, uuid))
        authorize = ask("Authorize connection (yes/no): ")
        if (authorize == "yes"):
            return
        raise Rejected("Connection rejected by user")

    @dbus.service.method(AGENT_INTERFACE,
                    in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        print("RequestPinCode (%s)" % (device))
        set_trusted(device)
        return ask("Enter PIN Code: ")

    @dbus.service.method(AGENT_INTERFACE,
                    in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        print("RequestPasskey (%s)" % (device))
        set_trusted(device)
        passkey = ask("Enter passkey: ")
        return dbus.UInt32(passkey)

    @dbus.service.method(AGENT_INTERFACE,
                    in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        print("DisplayPasskey (%s, %06u entered %u)" %
                        (device, passkey, entered))

    @dbus.service.method(AGENT_INTERFACE,
                    in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        print("DisplayPinCode (%s, %s)" % (device, pincode))

    @dbus.service.method(AGENT_INTERFACE,
                    in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        print("RequestConfirmation (%s, %06d)" % (device, passkey))
        confirm = ask("Confirm passkey (yes/no): ")
        if (confirm == "yes"):
            set_trusted(device)
            return
        raise Rejected("Passkey doesn't match")

    @dbus.service.method(AGENT_INTERFACE,
                    in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        print("RequestAuthorization (%s)" % (device))
        auth = ask("Authorize? (yes/no): ")
        if (auth == "yes"):
            return
        raise Rejected("Pairing rejected")

    @dbus.service.method(AGENT_INTERFACE,
                    in_signature="", out_signature="")
    def Cancel(self):
        print("Cancel")

def pair_reply():
    print("Device paired")
    set_trusted(pairing_dev_path)
    dev_connect(pairing_dev_path)
    mainloop.quit()

def pair_error(error):
    err_name = error.get_dbus_name()
    if err_name == "org.freedesktop.DBus.Error.NoReply" and device_obj:
        print("Timed out. Cancelling pairing")
        device_obj.CancelPairing()
    else:
        print("Creating device failed: %s" % (error))


    mainloop.quit()

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SystemBus()

    capability = "KeyboardDisplay"

    '''parser = OptionParser()
    parser.add_option("-i", "--adapter", action="store",
                    type="string",
                    dest="adapter_pattern",
                    default=None)
    parser.add_option("-c", "--capability", action="store",
                    type="string", dest="capability")
    parser.add_option("-t", "--timeout", action="store",
                    type="int", dest="timeout",
                    default=60000)
    (options, args) = parser.parse_args()
    if options.capability:
        capability  = options.capability'''
    parser = argparse.ArgumentParser(description='Bluetooth pair/remove/scan')
    parser.add_argument('--action',type=str,required=True,help='actions')
    parser.add_argument('--target',type=str,required=False,help='target address')
    args = parser.parse_args()

    #lets scan first
    adapter = bluezutils.find_adapter()
    bus.add_signal_receiver(interfaces_added,
            dbus_interface = "org.freedesktop.DBus.ObjectManager",
            signal_name = "InterfacesAdded")

    bus.add_signal_receiver(properties_changed,
            dbus_interface = "org.freedesktop.DBus.Properties",
            signal_name = "PropertiesChanged",
            arg0 = "org.bluez.Device1",
            path_keyword = "path")

    bus.add_signal_receiver(property_changed,
                    dbus_interface = "org.bluez.Adapter1",
                    signal_name = "PropertyChanged")

    om = dbus.Interface(bus.get_object("org.bluez", "/"),
                "org.freedesktop.DBus.ObjectManager")
    objects = om.GetManagedObjects()
    for path, interfaces in objects.items():
        if "org.bluez.Device1" in interfaces:
            devices[path] = interfaces["org.bluez.Device1"]

    mainloop = GObject.MainLoop()
    adapter.StartDiscovery()
    GLib.timeout_add_seconds(5, end_discovery)
    mainloop.run()
    #then pair

    path = "/test/agent"
    agent = Agent(bus, path)
    agent.set_exit_on_release(False)

    manager = dbus.Interface(bus.get_object('org.bluez','/org/bluez'), "org.bluez.AgentManager1")
    manager.RegisterAgent(path, capability)

    print("Agent registered")

    print("looking for device",args.target=="58:8E:81:A5:4A:6A")
    #device = bluezutils.find_device(options.target)
    for path in devices:
        if str(devices[path]['Address'])==args.target:
            if args.action=='pair':
                print("pair")
                if bool(devices[path]['Paired']):# and args.action=='pair':
                    print("Cannot pair, already paired!")
                else:
                    pairing_dev_path=path
                    device=dbus.Interface(bus.get_object('org.bluez',path),'org.bluez.Device1')
                    device.Pair(reply_handler=pair_reply, error_handler=pair_error,
                                            timeout=60000)
            elif args.action=='remove':
                print("removed")
                adapter.RemoveDevice(path)
            else:
                print("broke")

    mainloop.run()

    #adapter.UnregisterAgent(path)
    #print("Agent unregistered")
