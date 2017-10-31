#!/usr/bin/python

import sys
import socket
import struct
import select

from test_function import log
from test_function import WINDOW_SIZE, DATA_PACKET_TYPE, ACK_PACKET_TYPE, EOT_PACKET_TYPE

DUMMY_IP = "0.0.0.0"
DUMMY_PORT = 0

RECEIVER_INFO_FILE = "recvInfo"


def receive_go_back_n(filename):
    expt_seq_num = 1
    receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver_socket.bind((DUMMY_IP, DUMMY_PORT))

    with open(RECEIVER_INFO_FILE, 'w') as f:
        f.write("{0} {1}\n".format(receiver_socket.getsockname()[0], receiver_socket.getsockname()[1]))

    file_to_write = open(filename, 'ab')
    while True:
        print "blocking while waiting for incoming packet using select()"
        readers, _, _ = select.select([receiver_socket], [], [])
        data, addr = readers[0].recvfrom(512)
        header = struct.unpack('>III', data[:12])
        log(data, False)
        if header[0] == DATA_PACKET_TYPE:
            payload = struct.unpack('>{0}s'.format(header[1] - 12), data[12:header[1]])
            if header[2] == expt_seq_num:
                file_to_write.write(payload[0])
                ack_packet = struct.pack('>III', ACK_PACKET_TYPE, 12, expt_seq_num)
                receiver_socket.sendto(ack_packet, (addr[0], addr[1]))
                expt_seq_num += 1
            elif header[2] < expt_seq_num:  # sender did not recv ack
                ack_packet = struct.pack('>III', ACK_PACKET_TYPE, 12, header[2])
                receiver_socket.sendto(ack_packet, (addr[0], addr[1]))
            elif header[2] > expt_seq_num:
                ack_packet = struct.pack('>III', ACK_PACKET_TYPE, 12, expt_seq_num-1)
                receiver_socket.sendto(ack_packet, (addr[0], addr[1]))
            log(ack_packet, True)
        elif header[0] == EOT_PACKET_TYPE:
            eot_packet = struct.pack('>III', EOT_PACKET_TYPE, 12, 0)
            receiver_socket.sendto(eot_packet, (addr[0], addr[1]))
            log(eot_packet, True)
            file_to_write.close()
            sys.exit()


def receive_selective_repeat(filename):
    rcv_base = 1
    window = {}
    receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver_socket.bind((DUMMY_IP, DUMMY_PORT))

    with open(RECEIVER_INFO_FILE, 'w') as f:
        f.write("{0} {1}\n".format(receiver_socket.getsockname()[0], receiver_socket.getsockname()[1]))

    file_to_write = open(filename, 'ab')
    while True:
        print "blocking while waiting for incoming packet using select()"
        readers, _, _ = select.select([receiver_socket], [], [])
        data, addr = readers[0].recvfrom(512)
        header = struct.unpack('>III', data[:12])
        log(data, False)

        if header[0] == DATA_PACKET_TYPE and header[2] < rcv_base + WINDOW_SIZE:
            payload = struct.unpack('>{0}s'.format(header[1] - 12), data[12:header[1]])
            if header[2] == rcv_base:
                file_to_write.write(payload[0])
                rcv_base += 1
                for key in window.keys():
                    if key == rcv_base:
                        file_to_write.write(window[key])
                        window.pop(key)
                        rcv_base += 1
                    else:
                        break

            elif len(window) < WINDOW_SIZE and header[2] not in window.keys() and header[2] > rcv_base:
                # print "elif"
                window[header[2]] = payload[0]

            if header[2] >= rcv_base - WINDOW_SIZE:
                ack_packet = struct.pack('>III', ACK_PACKET_TYPE, 12, header[2])
                receiver_socket.sendto(ack_packet, (addr[0], addr[1]))
                log(ack_packet, True)

        elif header[0] == EOT_PACKET_TYPE:
            eot_packet = struct.pack('>III', EOT_PACKET_TYPE, 12, 0)
            receiver_socket.sendto(eot_packet, (addr[0], addr[1]))
            log(eot_packet, True)
            file_to_write.close()
            sys.exit()


if len(sys.argv) != 3:
    sys.exit("Error: Expected 2 arguments")

protocol_selector = int(sys.argv[1])
filename = sys.argv[2]

if protocol_selector == 0:
    receive_go_back_n(filename)
else:
    receive_selective_repeat(filename)
