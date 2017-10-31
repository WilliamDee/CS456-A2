#!/usr/bin/python
import socket
from struct import *
import time
import sys
import signal
import select
import thread

DATA_PACKET_TYPE = 0
ACK_PACKET_TYPE = 1
EOT_PACKET_TYPE = 2

DUMMY_IP = "0.0.0.0"
DUMMY_PORT = 500

CHANNEL_INFO_FILE = "channelInfo"
MAX_PAYLOAD = 10
WINDOW_SIZE = 10


def log(packet_header, was_sent):
    if was_sent:
        sent_or_recv = 'SEND'
    else:
        sent_or_recv = 'RECV'

    if packet_header[0] == DATA_PACKET_TYPE:
        pkt_type = 'DAT'
    elif packet_header[0] == ACK_PACKET_TYPE:
        pkt_type = 'ACK'
    else:
        pkt_type = 'EOT'

    print 'PKT {0} {1} {2} {3}'.format(sent_or_recv, pkt_type, packet_header[1], packet_header[2])


def read_channel_info():
    for i in range(6):  # try opening channelInfo for 1 minute
        try:
            with open(CHANNEL_INFO_FILE, 'r') as f:
                temp = f.readline().split(' ')
                channel_info = (temp[0], int(temp[1]))
                break
        except IOError as e:
            time.sleep(10)  # wait for user to run channel script

    if 'channel_info' not in locals():
        sys.exit("Error: Could not retrieve channelInfo")

    return channel_info

# timeout in milliseconds
def go_back_n(filename, utimeout):
    base = next_seq_num = 1
    sent_EOT = False
    timeout = utimeout/1000.0
    window = []

    sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    channel_info = read_channel_info()

    def timeout_handler(signum, frame):
        # print "timed out in handler"
        signal.setitimer(signal.ITIMER_REAL, timeout)
        for i in range(base, next_seq_num):
            print "i: ", i
            sender_socket.sendto(window[i - 1], (channel_info[0], channel_info[1]))

    signal.signal(signal.SIGALRM, timeout_handler)
    file_to_send = open(filename, 'rb')
    while True:
        try:
            print 'blocking temporarily to check for acks'
            readers, _, _ = select.select([sender_socket], [], [], timeout/1000.0)
            if len(readers) == 1:
                # print "in select if statement"
                data, addr = readers[0].recvfrom(12)  # since sender only recieves ack and eots
                header = unpack('>III', data[:12])
                # print "header: ", header
                # print "seq: ", next_seq_num
                # print "base: ", base
                log(header, False)
                if header[0] == ACK_PACKET_TYPE and header[2] == base:  # ignore dup acks
                    base = header[2] + 1
                    signal.setitimer(signal.ITIMER_REAL, timeout)
                    # print "resetting timeout to: ", signal.getitimer(signal.ITIMER_REAL)
                elif header[0] == EOT_PACKET_TYPE:
                    sys.exit()
        except select.error:
            # print "select error"
            pass

        if (next_seq_num < base + WINDOW_SIZE) and not file_to_send.closed:
            payload = file_to_send.read(MAX_PAYLOAD)
            # print "payload:\n", payload

            if payload == "":
                file_to_send.close()
            else:
                fmt = '>III{0}s'.format(len(payload))

                packet = pack(fmt, DATA_PACKET_TYPE, calcsize(fmt), next_seq_num, payload)
                window.append(packet)
                sender_socket.sendto(packet, (channel_info[0], channel_info[1]))
                log((DATA_PACKET_TYPE, calcsize(fmt), next_seq_num), True)
                if base == next_seq_num:
                    signal.setitimer(signal.ITIMER_REAL, timeout)
                    # print "set timeout to: ", signal.getitimer(signal.ITIMER_REAL)
                next_seq_num += 1
        elif base == next_seq_num and not sent_EOT:
            # print "sending EOT"
            signal.setitimer(signal.ITIMER_REAL, 0)
            eot_packet = pack('>III', EOT_PACKET_TYPE, 12, 0)
            sender_socket.sendto(eot_packet, (channel_info[0], channel_info[1]))
            log((EOT_PACKET_TYPE, 12, 0), True)
            sent_EOT = True


def selective_repeat(filename, utimeout):
    base = next_seq_num = 1
    sent_EOT = False
    timeout = utimeout / 1000.0
    acks = {}

    channel_info = read_channel_info()

    def send_packet(packet, size, seq):
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_socket.settimeout(timeout)
        send_socket.sendto(packet, channel_info)
        log((DATA_PACKET_TYPE, size, seq), True)

        print "waiting on pkt: ", seq
        data, addr = send_socket.recvfrom(12)
        header = unpack('>III', data[:12])
        log(header, False)

    file_to_send = open(filename, 'rb')
    while True:
        if (next_seq_num < base + WINDOW_SIZE) and not file_to_send.closed:
            payload = file_to_send.read(MAX_PAYLOAD)
            # print "payload:\n", payload

            if payload == "":
                file_to_send.close()
            else:
                fmt = '>III{0}s'.format(len(payload))

                packet = pack(fmt, DATA_PACKET_TYPE, calcsize(fmt), next_seq_num, payload)
                thread.start_new_thread(send_packet, (packet, calcsize(fmt), next_seq_num))
                log((DATA_PACKET_TYPE, calcsize(fmt), next_seq_num), True)
                next_seq_num += 1
        elif base == next_seq_num and not sent_EOT:
            # print "sending EOT"
            eot_packet = pack('>III', EOT_PACKET_TYPE, 12, 0)
            eot_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            eot_socket.sendto(eot_packet, channel_info)
            log((EOT_PACKET_TYPE, 12, 0), True)
            sent_EOT = True