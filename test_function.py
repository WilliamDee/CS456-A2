#!/usr/bin/python

import struct


DATA_PACKET_TYPE = 0
ACK_PACKET_TYPE = 1
EOT_PACKET_TYPE = 2

WINDOW_SIZE = 10


def log(pkt, was_sent):
    header = struct.unpack('>III', pkt[:12])
    if was_sent:
        sent_or_recv = 'SEND'
    else:
        sent_or_recv = 'RECV'

    if header[0] == DATA_PACKET_TYPE:
        pkt_type = 'DAT'
    elif header[0] == ACK_PACKET_TYPE:
        pkt_type = 'ACK'
    else:
        pkt_type = 'EOT'

    print 'PKT {0} {1} {2} {3}'.format(sent_or_recv, pkt_type, header[1], header[2])
