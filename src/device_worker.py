from PyQt5.QtCore import pyqtSignal, QObject
import socket
import os
from device import Device

class DeviceWorker(QObject):
    status_signal = pyqtSignal(str)
    data_signal = pyqtSignal(int, float)
    finished_signal = pyqtSignal()
    save_signal = pyqtSignal(list)  # New signal to save plot data

    def __init__(self, device, duration, rate):
        super().__init__()
        self.device = device
        self.duration = duration
        self.rate = rate
        self.running = False
        self.collected_data = []  # Store time/mV pairs for saving later

    def start_test(self):
        self.running = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)

        msg = f"TEST;CMD=START;DURATION={self.duration};RATE={self.rate};".encode('latin-1')
        sock.sendto(msg, (self.device.ip, self.device.port))

        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                if addr[0] == self.device.ip:
                    message = data.decode('latin-1')
                    self.status_signal.emit(message)

                    if message.startswith("STATUS;"):
                        parts = message.split(';')
                        time_ms = None
                        mv = None
                        for part in parts:
                            if part.startswith("TIME="):
                                time_ms = int(part.split('=')[1])
                            elif part.startswith("MV="):
                                mv = float(part.split('=')[1])

                        if time_ms is not None and mv is not None:
                            self.data_signal.emit(time_ms, mv)
                            self.collected_data.append((time_ms, mv))

                    if "STATE=IDLE" in message:
                        break
            except socket.timeout:
                continue

        sock.close()
        self.save_signal.emit(self.collected_data)
        self.finished_signal.emit()

    def stop_test(self):
        self.running = False
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)

        stop_msg = "TEST;CMD=STOP;".encode('latin-1')
        sock.sendto(stop_msg, (self.device.ip, self.device.port))

        try:
            data, addr = sock.recvfrom(1024)
            if addr[0] == self.device.ip:
                message = data.decode('latin-1')
                print(f"Stop response: {message}")
                self.status_signal.emit(message)
        except socket.timeout:
            print("⚠️ No response received for STOP command.")

        sock.close()

    def clear_data(self):
        self.collected_data = []
