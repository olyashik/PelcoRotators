import logging
from threading import Thread
from threading import Lock
import serial
import pelco_d


class PelcoRotator:
    """
    A class used to control PELCO-D rotator
    """

    def __init__(self, port_name='/dev/cu.usbserial-FT1GLXM1', port_speed=9600, port_timeout=1, pelco_id=2):
        logging.info("Initializing rotator")
        self._port_name = port_name
        self._port_speed = port_speed
        self._port_timeout = port_timeout
        self._pelco_id = pelco_id
        self._com = serial.Serial(self._port_name, self._port_speed, timeout=self._port_timeout)
        self._is_running = True
        self._serial_lock = Lock()
        self._azimuth = 0.0
        self._elevation = 0.0
        self._target_azimuth = 0.0
        self._target_elevation = 0.0
        self._azimuth_tolerance = 1.0
        self._elevation_tolerance = 1.0
        self._pan_speed = 0x20
        self._tilt_speed = 0x3F

        self._runner_thread = Thread(name="rotator runner", target=self.rotator_runner, daemon=True)
        self._runner_thread.start()

    def rotator_runner(self):
        while self._is_running:
            command, parser = pelco_d.get(pelco_d.Query_Pan_Position, self._pelco_id)
            self._serial_lock.acquire()
            self._com.write(command)
            # response = self._com.read(7)
            response = self.read_response()
            self._serial_lock.release()
            if response is not None and len(response) == 7:
                result = parser(response, command[-1])
                data = result[1]
                pan = (data[1] << 8) | data[2]
                self._azimuth = pan / 100
            command, parser = pelco_d.get(pelco_d.Query_Tilt_Position, self._pelco_id)
            self._serial_lock.acquire()
            self._com.write(command)
            response = self.read_response()
            self._serial_lock.release()
            if response is not None and len(response) == 7:
                result = parser(response, command[-1])
                data = result[1]
                tilt = (data[1] << 8) | data[2]
                self._elevation = tilt / 100
            # logging.info(f"Azimuth: {self._azimuth}, Elevation: {self._elevation}")
            if self.should_pan_right() and self.should_tilt_up():
                self.pan_right_tilt_up()
            elif self.should_pan_right() and self.should_tilt_down():
                self.pan_right_tilt_down()
            elif self.should_pan_left() and self.should_tilt_up():
                self.pan_left_tilt_up()
            elif self.should_pan_left() and self.should_tilt_down():
                self.pan_left_tilt_down()
            elif self.should_pan_right():
                self.pan_right()
            elif self.should_pan_left():
                self.pan_left()
            elif self.should_tilt_up():
                self.tilt_up()
            elif self.should_tilt_down():
                self.tilt_down()
            else:
                self.stop_pan()

    def read_response(self):
        return self._com.read(self._com.in_waiting) if self._com.in_waiting else None

    def set_azimuth(self, azimuth=None):
        if azimuth is not None:
            self._target_azimuth = azimuth

    def set_elevation(self, elevation=None):
        if elevation is not None:
            self._target_elevation = elevation

    def get_azimuth(self):
        return self._azimuth

    def get_elevation(self):
        return self._elevation

    def zero(self):
        self._target_azimuth = 0.0
        self._target_elevation = 0.0

    def should_pan_right(self):
        return self._target_azimuth > self._azimuth and abs(
            self._azimuth - self._target_azimuth) > self._azimuth_tolerance

    def should_pan_left(self):
        return self._target_azimuth < self._azimuth and abs(
            self._azimuth - self._target_azimuth) > self._azimuth_tolerance

    def should_tilt_up(self):
        return self._target_elevation > self._elevation and abs(
            self._elevation - self._target_elevation) > self._elevation_tolerance

    def should_tilt_down(self):
        return self._target_elevation < self._elevation and abs(
            self._elevation - self._target_elevation) > self._elevation_tolerance

    def pan_right(self):
        command, parser = pelco_d.get(pelco_d.Pan_Right, self._pelco_id, self._pan_speed)
        self._serial_lock.acquire()
        self._com.write(command)
        self._serial_lock.release()

    def pan_left(self):
        command, parser = pelco_d.get(pelco_d.Pan_Left, self._pelco_id, self._pan_speed)
        self._serial_lock.acquire()
        self._com.write(command)
        self._serial_lock.release()

    def pan_right_tilt_up(self):
        command, parser = pelco_d.get(pelco_d.Pan_Right_Tilt_Up, self._pelco_id, self._pan_speed, self._tilt_speed)
        self._serial_lock.acquire()
        self._com.write(command)
        self._serial_lock.release()

    def pan_right_tilt_down(self):
        command, parser = pelco_d.get(pelco_d.Pan_Right_Tilt_Down, self._pelco_id, self._pan_speed, self._tilt_speed)
        self._serial_lock.acquire()
        self._com.write(command)
        self._serial_lock.release()

    def pan_left_tilt_up(self):
        command, parser = pelco_d.get(pelco_d.Pan_Left_Tilt_Up, self._pelco_id, self._pan_speed, self._tilt_speed)
        self._serial_lock.acquire()
        self._com.write(command)
        self._serial_lock.release()

    def pan_left_tilt_down(self):
        command, parser = pelco_d.get(pelco_d.Pan_Left_Tilt_Down, self._pelco_id, self._pan_speed, self._tilt_speed)
        self._serial_lock.acquire()
        self._com.write(command)
        self._serial_lock.release()

    def tilt_up(self):
        command, parser = pelco_d.get(pelco_d.Tilt_Up, self._pelco_id, self._tilt_speed)
        self._serial_lock.acquire()
        self._com.write(command)
        self._serial_lock.release()

    def tilt_down(self):
        command, parser = pelco_d.get(pelco_d.Tilt_Down, self._pelco_id, self._tilt_speed)
        self._serial_lock.acquire()
        self._com.write(command)
        self._serial_lock.release()

    def stop_pan(self):
        command, parser = pelco_d.get(pelco_d.Pan_Stop, self._pelco_id)
        self._serial_lock.acquire()
        self._com.write(command)
        self._serial_lock.release()

    def stop_tilt(self):
        command, parser = pelco_d.get(pelco_d.Tilt_Stop, self._pelco_id)
        self._serial_lock.acquire()
        self._com.write(command)
        self._serial_lock.release()

    def stop(self):
        self.stop_pan()
        self.stop_tilt()
