#!/usr/bin/python

import sys
import socket
import struct
import select

DATA_PACKET_TYPE = 0
ACK_PACKET_TYPE = 1
EOT_PACKET_TYPE = 2
WINDOW_SIZE = 10

DUMMY_IP = "0.0.0.0"
DUMMY_PORT = 0

RECEIVER_INFO_FILE = "recvInfo"
CHANNEL_INFO_FILE = "channelInfo"


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


def receive_go_back_n(filename):
    expt_seq_num = 1
    receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver_socket.bind((DUMMY_IP, DUMMY_PORT))

    with open(RECEIVER_INFO_FILE, 'w') as f:
        f.write("{0} {1}\n".format(receiver_socket.getsockname()[0], receiver_socket.getsockname()[1]))
    # print "RECEIVER: ", receiver_socket.getsockname()

    file_to_write = open(filename, 'ab')
    while True:
        print "blocking while waiting for incoming packet"
        readers, _, _ = select.select([receiver_socket], [], [])
        data, addr = readers[0].recvfrom(512)
        header = struct.unpack('>III', data[:12])
        # print "addr: ", addr
        # print "header: ", header
        # print "expected: ", expt_seq_num
        log(header, False)
        if header[0] == DATA_PACKET_TYPE:
            payload = struct.unpack('>{0}s'.format(header[1] - 12), data[12:header[1]])
            # print "recvd:\n", payload
            if header[2] == expt_seq_num:
                # print "got expected seq"
                file_to_write.write(payload[0])
                ack_packet = struct.pack('>III', ACK_PACKET_TYPE, 12, expt_seq_num)
                receiver_socket.sendto(ack_packet, (addr[0], addr[1]))
                log((ACK_PACKET_TYPE, 12, expt_seq_num), True)
                expt_seq_num += 1
            elif header[2] < expt_seq_num:  # sender did not recv ack
                # print "resending ack"
                ack_packet = struct.pack('>III', ACK_PACKET_TYPE, 12, header[2])
                receiver_socket.sendto(ack_packet, (addr[0], addr[1]))
                log((ACK_PACKET_TYPE, 12, header[2]), True)
            elif header[2] > expt_seq_num:
                # print "wrong order, header2 = ", header[2]
                ack_packet = struct.pack('>III', ACK_PACKET_TYPE, 12, expt_seq_num-1)
                receiver_socket.sendto(ack_packet, (addr[0], addr[1]))
                log((ACK_PACKET_TYPE, 12, expt_seq_num-1), True)
        elif header[0] == EOT_PACKET_TYPE:
            eot_packet = struct.pack('>III', EOT_PACKET_TYPE, 12, 0)
            receiver_socket.sendto(eot_packet, (addr[0], addr[1]))
            log((EOT_PACKET_TYPE, 12, 0), True)
            file_to_write.close()
            sys.exit()


def receive_selective_repeat(filename):
    rcv_base = 1
    window = {}
    receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver_socket.bind((DUMMY_IP, DUMMY_PORT))

    with open(RECEIVER_INFO_FILE, 'w') as f:
        f.write("{0} {1}\n".format(receiver_socket.getsockname()[0], receiver_socket.getsockname()[1]))
    # print "RECEIVER: ", receiver_socket.getsockname()

    file_to_write = open(filename, 'ab')
    while True:
        print "blocking while waiting for incoming packet"
        readers, _, _ = select.select([receiver_socket], [], [])
        data, addr = readers[0].recvfrom(512)
        header = struct.unpack('>III', data[:12])
        log(header, False)

        # print "window: ", window
        # print "header: ", header
        # print "base: ", rcv_base
        if header[0] == DATA_PACKET_TYPE and header[2] < rcv_base + WINDOW_SIZE:
            payload = struct.unpack('>{0}s'.format(header[1] - 12), data[12:header[1]])
            if header[2] == rcv_base:
                # print "if"
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
                log((ACK_PACKET_TYPE, 12, header[2]), True)

        elif header[0] == EOT_PACKET_TYPE:
            eot_packet = struct.pack('>III', EOT_PACKET_TYPE, 12, 0)
            receiver_socket.sendto(eot_packet, (addr[0], addr[1]))
            log((EOT_PACKET_TYPE, 12, 0), True)
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
