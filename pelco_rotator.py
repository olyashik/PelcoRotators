#!env python3

from pelco_rotator_interface import PelcoRotator
import logging
from socketserver import *
from threading import Thread
import sys
import signal
import argparse

tcp_host = '0.0.0.0'
tcp_port = 4533
tcp_addr = (tcp_host, tcp_port)

logging.basicConfig(level=logging.INFO, format='%(asctime)s.%(msecs)03d - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

global rotator

tcp_server = None
tcp_thread = None


class HAMLibTCPHandler(StreamRequestHandler):
    """
    A class used to process incoming TCP connections
    """

    def __init__(self, *args, **kwargs):
        self.rotator = rotator
        StreamRequestHandler.__init__(self, *args, **kwargs)

    def setup(self):
        """

        :return:
        """
        StreamRequestHandler.setup(self)
        logging.info('{}:{} connected'.format(*self.client_address))

    def handle(self):
        """
        Handle incoming TCP connections
        This handler implements hamlib rotator control protocol in it's simplest
        Only p (position reporting) and P (position setting) commands supported
        """
        try:
            while True:
                data = self.rfile.readline().strip().decode("utf-8")
                if not data:
                    break
                logging.debug('client -> server: ' + data)
                if data == 'p' or data == '\\get_pos':
                    self.send_response_string("{azimuth:.2f}\n{elevation:.2f}"
                                              .format(azimuth=self.rotator.get_azimuth(),
                                                      elevation=self.rotator.get_elevation()))
                elif data == 'K' or data == '\\park':
                    self.rotator.zero()
                    self.send_response_string("RPRT 0")
                elif data == 'R' or data == '\\reset':
                    self.rotator.zero()
                    self.send_response_string("RPRT 0")
                elif data == '_' or data == '\\get_info':
                    self.send_response_string("pirotator az={0} el={1} azoverlap=0,0".format(
                        self.rotator.get_azimuth(), self.rotator.get_elevation()).lower())
                elif data == '?' or data == '\\dump_state':
                    response_string = "rotctld Protocol Ver: 1\n"
                    response_string += "Rotor Model: 2\n"
                    response_string += "Minimum Azimuth: 0.000000\n"
                    response_string += "Maximum Azimuth: 360.000000\n"
                    response_string += "Minimum Elevation: 0.000000\n"
                    response_string += "Maximum Elevation: 90.000000\n"
                    response_string += "South Zero: 0\n"
                    response_string += "rot_type=AzEl\n"
                    response_string += "done"
                    self.send_response_string(response_string)
                elif data.startswith("P ") or data.startswith("\\set_pos "):
                    cmd = data.split(" ")
                    if len(cmd) == 3:
                        new_azimuth = float(cmd[1].replace(",", "."))
                        new_elevation = float(cmd[2].replace(",", "."))
                        self.rotator.set_azimuth(new_azimuth)
                        if new_elevation >= 45:
                            new_elevation = -new_elevation
                        self.rotator.set_elevation(new_elevation)
                        self.send_response_string("RPRT 0")
                    else:
                        self.send_response_string("RPRT -4")
                else:
                    self.send_response_string("RPRT -4")
        except Exception as e:
            logging.error('{}:{} {}'.format(*self.client_address, e))

    def finish(self):
        logging.info('{}:{} disconnected'.format(*self.client_address))

    def send_response_string(self, response_string):
        logging.debug("server -> client: " + response_string.replace("\n", "\\n"))
        self.wfile.write((response_string + "\n").encode('utf-8'))


def signal_handler(signal, frame):
    rotator.stop()
    if tcp_server is not None:
        tcp_server.shutdown()
    logging.info('pelco_rotator shutting down')
    sys.exit(0)


def tcp_handler():
    tcp_server = TCPServer(tcp_addr, HAMLibTCPHandler)
    logging.info('starting hamlib rotctl server')
    tcp_server.serve_forever()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    parser = argparse.ArgumentParser(
        prog='pelco_rotator',
        description='A rotctl to pelco-d bridge',
        epilog='https://github.com/belovictor/pelco_d_rotator.git')
    parser.add_argument('-p', '--port', help='Serial port device name', required=True, type=str)
    parser.add_argument('-b', '--baud', help='Serial port baudrate, default 9600', default=9600, type=int)
    parser.add_argument('-i', '--pelcoid', help='PELCO-D device id, default 1', default=1, type=int)
    arguments = vars(parser.parse_args())
    print(arguments)
    rotator = PelcoRotator(port_name=arguments['port'], port_speed=arguments['baud'], pelco_id=arguments['pelcoid'])
    logging.info('pelco_rotator starting')
    tcp_thread = Thread(name="tcpthread", target=tcp_handler, daemon=True)
    tcp_thread.start()
    tcp_thread.join()
