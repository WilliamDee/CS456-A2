#!/usr/bin/python
import socket
from struct import *
import time
import sys
import signal
import select

DATA_PACKET_TYPE = 0
ACK_PACKET_TYPE = 1
EOT_PACKET_TYPE = 2

DUMMY_IP = "0.0.0.0"
DUMMY_PORT = 500

CHANNEL_INFO_FILE = "channelInfo"
MAX_PAYLOAD = 10


# timeout in milliseconds
def go_back_n(filename, utimeout, window_size):
    base = next_seq_num = 1
    timeout = utimeout/1000
    window = []

    sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    for i in range(6):  # try opening channelInfo for 1 minute
        try:
            with open(CHANNEL_INFO_FILE, 'r') as f:
                temp = f.readline().split(' ')
                channel_info = (temp[0], int(temp[1]))
                break
        except IOError as e:
            time.sleep(10)  # wait for user to run channel script
    if 'channel_info' in locals():
        print "channel: ", channel_info
    else:
        sys.exit("Error: Could not retrieve channelInfo")

    def timeout_handler(signum, frame):
        print "timed out in handler"
        signal.setitimer(signal.ITIMER_REAL, timeout)
        for i in range(base, next_seq_num):
            print "i: ", i
            sender_socket.sendto(window[i - 1], (channel_info[0], channel_info[1]))

    signal.signal(signal.SIGALRM, timeout_handler)
    file_to_send = open(filename, 'rb')
    while True:
        try:
            print "in try"
            readers, _, _ = select.select([sender_socket], [], [], timeout/10)
            if len(readers) == 1:
                print "in select if statement"
                data, addr = readers[0].recvfrom(12)  # since sender only recieves ack and eots
                header = unpack('>III', data[:12])
                print "header: ", header
                print "seq: ", next_seq_num
                print "base: ", base
                if header[0] == ACK_PACKET_TYPE & header[2] + 1 >= base:  # ignore dup acks
                    base = header[2] + 1
                    if base == next_seq_num and file_to_send.closed:
                        signal.setitimer(signal.ITIMER_REAL, 0)
                        eot_packet = pack('>III', EOT_PACKET_TYPE, 12, 0)
                        sender_socket.sendto(eot_packet, (channel_info[0], channel_info[1]))
                    else:
                        signal.setitimer(signal.ITIMER_REAL, timeout)
                elif header[0] == EOT_PACKET_TYPE:
                    sys.exit()
        except select.error:
            print "select error"
            pass

        print "after try"
        if (next_seq_num < base + window_size) and not file_to_send.closed:
            payload = file_to_send.read(MAX_PAYLOAD)
            print "payload:\n", payload

            if payload == "":
                file_to_send.close()
            else:
                fmt = '>III{0}s'.format(len(payload))

                packet = pack(fmt, DATA_PACKET_TYPE, calcsize(fmt), next_seq_num, payload)
                window.append(packet)
                sender_socket.sendto(packet, (channel_info[0], channel_info[1]))
                if base == next_seq_num:
                    signal.setitimer(signal.ITIMER_REAL, timeout)
                    print "set timeout to: ", signal.getitimer(signal.ITIMER_REAL)
                next_seq_num += 1


def selective_repeat(filename, timeout, window_size):
    base, next_seq_num = 1
    with open(filename, 'rb') as f:
        while True:
            if next_seq_num < base + window_size:
                payload = f.read(500)

                if payload == "":
                    break

                fmt = '>iii{0}s'.format(len(payload))

                packet = pack(fmt, DATA_PACKET_TYPE, calcsize(fmt), next_seq_num, payload)
                unpacked = unpack(fmt, packet)
