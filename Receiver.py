#!/usr/bin/python

import sys
import socket
import struct
import select
import time

DATA_PACKET_TYPE = 0
ACK_PACKET_TYPE = 1
EOT_PACKET_TYPE = 2

DUMMY_IP = "0.0.0.0"
DUMMY_PORT = 0

RECEIVER_INFO_FILE = "recvInfo"
CHANNEL_INFO_FILE = "channelInfo"


def receive_go_back_n(filename):
    expt_seq_num = 1
    receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   # receiver_socket.sendto("dummy", (DUMMY_IP, DUMMY_PORT))  # this lets the OS assign a port number to this socket
    receiver_socket.bind((DUMMY_IP, DUMMY_PORT))

    with open(RECEIVER_INFO_FILE, 'w') as f:
        f.write("{0} {1}\n".format(receiver_socket.getsockname()[0], receiver_socket.getsockname()[1]))
    print "RECEIVER: ", receiver_socket.getsockname()

    file_to_write = open(filename, 'ab')
    while True:
        print "blocking while waiting for incoming packet"
        readers, _, _ = select.select([receiver_socket], [], [])
        data, addr = readers[0].recvfrom(512)
        header = struct.unpack('>III', data[:12])
        print "addr: ", addr
        print "header: ", header
        print "expected: ", expt_seq_num
        if header[0] == DATA_PACKET_TYPE:
            payload = struct.unpack('>{0}s'.format(header[1] - 12), data[12:header[1]])
            print "recvd:\n", payload
            if header[2] == expt_seq_num:
                print "got expected seq"
                file_to_write.write(payload[0])
                ack_packet = struct.pack('>III', ACK_PACKET_TYPE, 12, expt_seq_num)
                receiver_socket.sendto(ack_packet, (addr[0], addr[1]))
                expt_seq_num += 1
            elif header[2] < expt_seq_num:  # sender did not recv ack
                print "resending ack"
                ack_packet = struct.pack('>III', ACK_PACKET_TYPE, 12, header[2])
                receiver_socket.sendto(ack_packet, (addr[0], addr[1]))
            elif header[2] > expt_seq_num:
                print "wrong order, header2 = ", header[2]
                ack_packet = struct.pack('>III', ACK_PACKET_TYPE, 12, expt_seq_num-1)
                receiver_socket.sendto(ack_packet, (addr[0], addr[1]))
        elif header[0] == EOT_PACKET_TYPE:
            eot_packet = struct.pack('>III', EOT_PACKET_TYPE, 12, 0)
            receiver_socket.sendto(eot_packet, (addr[0], addr[1]))
            file_to_write.close()
            sys.exit()


if len(sys.argv) != 3:
    sys.exit("Error: Expected 2 arguments")

protocol_selector = int(sys.argv[1])
filename = sys.argv[2]

receive_go_back_n(filename)
