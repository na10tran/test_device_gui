import socket
import constants
from device import Device

class DeviceManager:
    """
        Manages the state, communication, and data tracking for devices under test.

        This class is responsible for discovering devices, tracking which devices are running,
        managing their worker threads, collecting log and plot data, and maintaining test statuses.

        :attribute devices (list of Device) ist of all discovered devices.

        :attribute drunning_devices (list of Device) List of devices that are currently added to the testing set.

        :attribute dworkers (dict of str -> DeviceWorker) Mapping of device serial numbers to their corresponding test workers.

        :attribute dthreads (dict of str -> threading.Thread) Mapping of device serial numbers to their active testing threads.

        :attribute dplot_data (dict of str -> list of (int, float)) Mapping of device serial numbers to their time-series test data

        :attribute dlog_lines (dict of str -> list of str) Mapping of device serial numbers to their log messages.

        :attribute dstatuses (dict of str -> str) Mapping of device serial numbers to their current test status.
    """

    def __init__(self):
        self.devices = []
        self.running_devices = []
        self.workers = {}
        self.threads = {}
        self.plot_data = {}
        self.log_lines = {}
        self.statuses = {}
         
    def discover_devices(self, timeout=2):
        """
            Discovers devices on the network by broadcasting a UDP message and listening for responses.

            :param timeout (int, optional) Time in seconds to wait for device responses

        """

        self.clear_devices()
        # Create a UDP socket for multicast communication
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(timeout)
        message = b"ID;"
        sock.sendto(message, (constants.MULTICAST_ADDR, constants.MULTICAST_PORT))

        try:
            while True:
                # Listen for responses from devices
                data, (ip, port) = sock.recvfrom(constants.BUFFER_SIZE)
                decoded = data.decode('latin-1')    # decode message

                parts = decoded.split(';')
                model = parts[1].split('=')[1]
                serial = parts[2].split('=')[1]

                self.add_device(Device(ip, port, model, serial))
        except socket.timeout:
            pass
        finally:
            sock.close()

        return self.devices
    
    def add_device(self, device):
        """
            Adds a discovered device to the internal device list.

            :param device (Device) The Device object to add.

        """

        self.devices.append(device)

    def clear_devices(self):
        """
            Clears the current list of discovered devices.

        """

        self.devices.clear()

    def add_running_device(self, device):
        """
            Adds a device to the list of running test devices if it's not already included.

            ----------
            :param device (Device) The Device object to start tracking as actively under test.

        """

        if device.serial not in [d.serial for d in self.running_devices]:
            self.running_devices.append(device)
            self.log_lines[device.serial] = []
            self.plot_data[device.serial] = []
            self.statuses[device.serial] = "Idle"

    def remove_running_device(self, serial):
        """
            Remove a device from the list of running devices and clean up associated data.

            :param serial (string) Serial number of the device

        """

        self.running_devices = [d for d in self.running_devices if d.serial != serial]
        self.workers.pop(serial, None)
        self.threads.pop(serial, None)
        self.plot_data.pop(serial, None)
        self.log_lines.pop(serial, None)
        self.statuses.pop(serial, None)

    def is_running(self, serial):
        """
            Check if a device is currently running a test.

            :param serial (string) Serial number of the device.

        """

        return serial in self.workers

    def set_worker(self, serial, worker, thread):
        """
            Register a worker and its corresponding thread for a device.

            :param serial (string) Serial number of the device.
            :param worker (DeviceWorker) Worker object handling the test.
            :param thread (threading.Thread) Thread in which the worker runs.

        """

        self.workers[serial] = worker
        self.threads[serial] = thread

    def clear_worker(self, serial):
        """
            Remove the worker and thread associated with a device.

            :param serial (string) Serial number of the device.

        """

        self.workers.pop(serial, None)
        self.threads.pop(serial, None)

    def get_log(self, serial):
        """
            Retrieve the log lines for a device.

            :param serial (string) Serial number of the device.

        """

        return self.log_lines.get(serial, [])

    def append_log(self, serial, line):
        """
            Append a new entry to a device's log.

            :param serial (string) Serial number of the device.
            :param line (string) Log entry to append.

        """

        self.log_lines.setdefault(serial, []).append(line)

    def get_plot_data(self, serial):
        """
            Get all stored plot data points for a device.

            :param serial (string) Serial number of the device.

        """

        return self.plot_data.get(serial, [])

    def append_plot_data(self, serial, time_ms, mv):
        """
            Append a new (time, voltage) data point for plotting.

            :param serial (string) Serial number of the device.
            :param time_ms (int) Time in milliseconds.
            :param mv (float) Voltage in millivolts.

        """

        self.plot_data.setdefault(serial, []).append((time_ms, mv))

    def update_status(self, serial, status):
        """
            Update the status string of a device.

            :param serial (string) Serial number of the device.
            :param status (string) New status string (e.g., "Testing", "Completed").

        """

        self.statuses[serial] = status

    def get_status(self, serial):
        """
            Get the current status of a device.

            :param serial (string) Serial number of the device.

        """

        return self.statuses.get(serial, "Unknown")

    def clear_plot(self, serial):
        """
            Clear all plot data for a specific device.

            :param serial (string) Serial number of the device.

        """
        if serial in self.plot_data:
            self.plot_data[serial] = []
