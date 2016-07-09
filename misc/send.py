#!/usr/bin/env python

import socket
import re
import struct
import argparse
try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("paho-mqtt not installed, MQTT will be unavailable.")


def discover_leds(timeout=2):
    # From https://stackoverflow.com/questions/10244117/how-can-i-find-the-ip-address-of-a-host-using-mdns
    UDP_PORT = 5353
    MCAST_GRP = '224.0.0.251'

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 5353))

    mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    packet = '\x00\x00\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\t_gameleds\x04_udp\x05local\x00\x00\x01\x00\x01'
    sock.sendto(packet, (MCAST_GRP, UDP_PORT))
    sock.settimeout(timeout)

    ips = []
    while True:
        try:
            m = sock.recvfrom(1024)
            if m[0] != packet:
                ips.append(m[1][0])
        except socket.timeout:
            break

    return ips


class LEDs(object):
    def __init__(self, mqtt_hostname=None, udp_ips=[]):
        self._mqtt_hostname = mqtt_hostname
        self._udp_ips = udp_ips

        if self._mqtt_hostname:
            self.client = mqtt.Client()
            self.client.connect(mqtt_hostname, 1883, 100)

        if self._udp_ips:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def send(self, r, g, b):
        message = bytearray("%s, %s, %s" % (r, g, b))
        for ip in self._udp_ips:
            self._socket.sendto(message, (ip, 19872))

        if self._mqtt_hostname:
            self.client.publish("leds/main/command", message)


def hex_to_rgb(value):
    value = value.lstrip('#')
    l = len(value)
    digits = tuple(int(value[i:i + l // 3], 16) for i in range(0, l, l // 3))
    if l == 3:
        digits = [digit * 16 for digit in digits]
    return digits


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Send some colors.')
    parser.add_argument('color', help="the hex color to send.")
    parser.add_argument('-m', '--mqtt-hostname',
                        help='specify the MQTT server hostname.')
    parser.add_argument('-u', '--udp-ips',
                        help='specify the list of UDP IPs to send to.')

    args = parser.parse_args()

    udp_ips = re.split("[, ]", args.udp_ips) if args.udp_ips else None
    if not args.mqtt_hostname and not udp_ips:
        print("Discovering Gamelights controllers...")
        udp_ips = discover_leds()
    print(udp_ips)

    leds = LEDs(mqtt_hostname=args.mqtt_hostname, udp_ips=udp_ips)

    rgb = hex_to_rgb(args.color)
    r, g, b = [col * 4 for col in rgb]
    leds.send(r, g, b)
