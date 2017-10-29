#!/usr/bin/python2.7

from test_function import go_back_n
import sys

if len(sys.argv) != 4:
    sys.exit("Error: Expected 3 arguments")

protocol_selector = int(sys.argv[1])
timeout = int(sys.argv[2])
filename = sys.argv[3]

WINDOW_SIZE = 10

go_back_n(filename, timeout, WINDOW_SIZE)


