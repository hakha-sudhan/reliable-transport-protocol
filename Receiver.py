#!/usr/bin/env python
import datetime
import signal
import socket
import sys
import util

if __name__ == '__main__':
    signal.signal(signal.SIGINT, util.shutdown)

    # Set command line args
    try:
        filename = sys.argv[1]
        listen_port = int(sys.argv[2])
        sender_ip = socket.gethostbyname(sys.argv[3])
        sender_port = int(sys.argv[4])
        log_filename = sys.argv[5]

    except IndexError, TypeError:
        exit("usage: ./receiver.py <filename> <listening_port> <sender_IP> <sender_port> <log_filename>")

    # Establish initial sockets
    try:
        # UDP socket for receiving file
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        recv_sock.bind(("", listen_port))

        # TCP socket for sending ACKs
        ack_sock = socket.socket()
        ack_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except socket.error:
        exit("Error creating socket.")

    # Open files for logging and writing
    recv_file = open(filename, 'w')
    if log_filename == "stdout":
        log_file = sys.stdout
    else:
        log_file = open(log_filename, 'w')

    next_acknum = 0

    # Receive first packet
    packet, addr = recv_sock.recvfrom(576)
    source_port, dest_port, seqnum, acknum, header_length, \
        ack, final, window_size, contents = util.unpack(packet)

    checksum = util.get_checksum(packet)
    packet_valid = checksum == 0 and next_acknum == acknum

    if packet_valid:
        recv_file.write(contents)
        next_acknum += 1

    recv_file.write(contents)
    log = str(datetime.datetime.now()) + " " + str(source_port) + " " + str(dest_port) + " " + str(seqnum) + " " + str(
        acknum)
    log_file.write(log + "\n")

    # Establish ack socket connection
    ack_sock.connect((sender_ip, sender_port))
    out_port = ack_sock.getsockname()[1]
    ack_segment = util.make_packet(out_port, sender_port,
                                   seqnum, acknum, packet_valid,
                                   False, 1, "")
    ack_sock.send(ack_segment)

    # At this point, we are connected so we can send ACKs
    while True:

        # Receive every other packet
        packet, addr = recv_sock.recvfrom(576)

        source_port, dest_port, seqnum, acknum, header_length, \
            ack, final, window_size, contents = util.unpack(packet)


        checksum = util.get_checksum(packet)

        log = str(datetime.datetime.now()) + " " + str(source_port) + " " + str(dest_port) + " " + str(
            seqnum) + " " + str(acknum)
        if final:
            log += " FIN"
        log_file.write(log + "\n")

        # ACK the packet if it's uncorrupted; otherwise send NAK.
        packet_valid = checksum == 0 and next_acknum == acknum

        if packet_valid:
            recv_file.write(contents)
            next_acknum += 1

        ack_segment = util.make_packet(out_port, sender_port,
                                        seqnum, acknum, packet_valid,
                                        final, 1, "")
        ack_sock.send(ack_segment)
        if final:
            break