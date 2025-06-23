from PyQt5.QtCore import pyqtSignal, QObject
import socket

import constants

class DeviceWorker(QObject):
    """
        Worker class for executing a test on a device in a background thread.

        This class handles UDP communication with a specified device to start and stop
        tests, listen for responses, collect time-voltage data, and emit signals to update
        the GUI in real time.

        :signal status_signal (pyqtSignal(str)) Emitted when a status message is received from the device.
        
        :signal data_signal (pyqtSignal(int, float)) Emitted for each received data point, as (time in ms, voltage in mV).
        
        :signal finished_signal (pyqtSignal()) Emitted when the device test ends (e.g., enters IDLE state).
        
        :signal save_signal (pyqtSignal(list)) Emitted at the end of a test, containing a list of collected (time, mV) tuples.

        :attributes device (Device) The target device instance on which the test is run.

        :attributes duration (int) Duration of the test in seconds.

        :attributes rate (int) Rate at which the device should send data updates, in milliseconds.

        :attributes running (bool) Flag indicating whether the test is currently running.

        :attributes collected_data (list of tuple[int, float]) List of (time, mV) data points collected during the test.
        
    """

    status_signal = pyqtSignal(str)
    data_signal = pyqtSignal(int, float)
    finished_signal = pyqtSignal()
    save_signal = pyqtSignal(list) 

    def __init__(self, device, duration, rate):
        super().__init__()
        self.device = device
        self.duration = duration
        self.rate = rate
        self.running = False
        self.collected_data = [] 

    def start_test(self):
        """
            Starts the test by sending a START command to the device over UDP.
            This method listens for incoming status updates while the test is running.
            It parses incoming messages for time and voltage data, emits corresponding signals,
            and collects the data.

        """

        self.running = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)

        msg = f"TEST;CMD=START;DURATION={self.duration};RATE={self.rate};".encode('latin-1')
        sock.sendto(msg, (self.device.ip, self.device.port))

        while self.running:
            try:
                data, addr = sock.recvfrom(constants.BUFFER_SIZE)
                if addr[0] == self.device.ip:
                    message = data.decode('latin-1')
                    self.status_signal.emit(message)

                    if message.startswith("STATUS;"):
                        parts = message.split(';')
                        time_ms = None
                        mv = None
                        ma = None
                        for part in parts:
                            if part.startswith("TIME="):
                                time_ms = int(part.split('=')[1])
                            elif part.startswith("MV="):
                                mv = float(part.split('=')[1])
                            elif part.startswith("MA="):
                                ma = float(part.split('=')[1])

                        if time_ms is not None and mv is not None and ma is not None:
                            # You might want to emit a new signal with both MV and MA
                            # Or for now, append them together in collected_data
                            self.data_signal.emit(time_ms, mv)  # keep current mv signal if you want
                            # Example: You can add a new signal for MA, or change data_signal to include ma
                            # For now, let's just store both together:
                            self.collected_data.append((time_ms, mv, ma))

                    if "STATE=IDLE" in message:
                        break
            except socket.timeout:
                continue

        sock.close()
        self.save_signal.emit(self.collected_data)
        self.finished_signal.emit()

    def stop_test(self):
        """
            Stops the currently running test by sending a STOP command to the device over UDP.

        """

        self.running = False
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)

        stop_msg = "TEST;CMD=STOP;".encode('latin-1')
        sock.sendto(stop_msg, (self.device.ip, self.device.port))

        try:
            data, addr = sock.recvfrom(constants.BUFFER_SIZE)
            if addr[0] == self.device.ip:
                message = data.decode('latin-1')
                print(f"Stop response: {message}")
                self.status_signal.emit(message)
        except socket.timeout:
            print("⚠️ No response received for STOP command.")

        sock.close()

    def clear_data(self):
        """
            Clears all collected test data for the device

        """

        self.collected_data = []
