# device_manager.py

class DeviceManager:
    def __init__(self):
        self.devices = []
        self.running_devices = []
        self.workers = {}
        self.threads = {}
        self.plot_data = {}
        self.log_lines = {}
        self.statuses = {}

    def add_device(self, device):
        self.devices.append(device)

    def clear_devices(self):
        self.devices.clear()

    def add_running_device(self, device):
        if device.serial not in [d.serial for d in self.running_devices]:
            self.running_devices.append(device)
            self.log_lines[device.serial] = []
            self.plot_data[device.serial] = []
            self.statuses[device.serial] = "Idle"

    def remove_running_device(self, serial):
        self.running_devices = [d for d in self.running_devices if d.serial != serial]
        self.workers.pop(serial, None)
        self.threads.pop(serial, None)
        self.plot_data.pop(serial, None)
        self.log_lines.pop(serial, None)
        self.statuses.pop(serial, None)

    def is_running(self, serial):
        return serial in self.workers

    def set_worker(self, serial, worker, thread):
        self.workers[serial] = worker
        self.threads[serial] = thread

    def clear_worker(self, serial):
        self.workers.pop(serial, None)
        self.threads.pop(serial, None)

    def get_log(self, serial):
        return self.log_lines.get(serial, [])

    def append_log(self, serial, line):
        self.log_lines.setdefault(serial, []).append(line)

    def get_plot_data(self, serial):
        return self.plot_data.get(serial, [])

    def append_plot_data(self, serial, time_ms, mv):
        self.plot_data.setdefault(serial, []).append((time_ms, mv))

    def update_status(self, serial, status):
        self.statuses[serial] = status

    def get_status(self, serial):
        return self.statuses.get(serial, "Unknown")

    def clear_plot(self, serial):
        if serial in self.plot_data:
            self.plot_data[serial] = []
