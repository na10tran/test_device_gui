import sys
import socket
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QHBoxLayout, QTextEdit, QSizePolicy, QFileDialog, QLineEdit,
    QFormLayout, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QSplitter
)
from PyQt5.QtCore import pyqtSignal, QObject, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from device_worker import DeviceWorker
import constants
from device import Device

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Device Test GUI")
        self.resize(1200, 900)

        main_layout = QVBoxLayout(self)

        # Top Discover Button
        discover_layout = QHBoxLayout()
        self.discover_button = QPushButton("Discover Devices")
        self.discover_button.clicked.connect(self.on_discover)
        discover_layout.addWidget(self.discover_button)
        main_layout.addLayout(discover_layout)

        # Discovered Devices Table
        self.device_table = QTableWidget(0, 4)
        self.device_table.setHorizontalHeaderLabels(["Model", "Serial", "IP", "Port"])
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.device_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.device_table.setSelectionMode(QTableWidget.SingleSelection)
        self.device_table.itemSelectionChanged.connect(self.on_discovered_selection_changed)

        main_layout.addWidget(QLabel("Discovered Devices:"))
        main_layout.addWidget(self.device_table)

        # Add/Remove Buttons
        device_action_layout = QHBoxLayout()
        self.add_running_button = QPushButton("Add to Testing Devices")
        self.add_running_button.setEnabled(False)
        self.add_running_button.clicked.connect(self.add_to_running_tests)
        self.remove_running_button = QPushButton("Remove from Testing Devices")
        self.remove_running_button.clicked.connect(self.remove_from_running_tests)
        device_action_layout.addWidget(self.add_running_button)
        device_action_layout.addWidget(self.remove_running_button)
        main_layout.addLayout(device_action_layout)

        # Devices Testing Table
        self.running_table = QTableWidget(0, 5)
        self.running_table.setHorizontalHeaderLabels(["Model", "Serial", "IP", "Port", "Status"])
        self.running_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.running_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.running_table.setSelectionMode(QTableWidget.SingleSelection)
        self.running_table.itemSelectionChanged.connect(self.on_running_selection_changed)

        main_layout.addWidget(QLabel("Devices Testing:"))
        main_layout.addWidget(self.running_table)

        # Control Area
        self.status_label = QLabel("Status: Idle")
        main_layout.addWidget(self.status_label)

        control_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Test")
        self.stop_button = QPushButton("Stop Test")
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)

        form_layout = QFormLayout()
        self.duration_input = QLineEdit("10")
        self.rate_input = QLineEdit("1000")
        form_layout.addRow("Test Duration (s):", self.duration_input)
        form_layout.addRow("Status Rate (ms):", self.rate_input)

        control_container = QVBoxLayout()
        control_container.addLayout(control_layout)
        control_container.addLayout(form_layout)
        main_layout.addLayout(control_container)

        # Plot and Log Area in a Splitter
        splitter = QSplitter(Qt.Vertical)

        # Plot Area
        plot_container = QWidget()
        plot_layout = QVBoxLayout(plot_container)
        self.figure = Figure(figsize=(8, 5), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Live Test Data")
        self.ax.set_xlabel("Time (ms)")
        self.ax.set_ylabel("mV")
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)

        # Graph Buttons
        graph_btn_layout = QHBoxLayout()
        self.save_graph_button = QPushButton("Save Graph")
        self.clear_graph_button = QPushButton("Clear Graph")
        graph_btn_layout.addWidget(self.save_graph_button)
        graph_btn_layout.addWidget(self.clear_graph_button)
        plot_layout.addLayout(graph_btn_layout)

        plot_container.setLayout(plot_layout)
        splitter.addWidget(plot_container)

        # Log Area
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        log_layout.addWidget(self.log_output)
        self.save_log_button = QPushButton("Save Log")
        log_layout.addWidget(self.save_log_button)
        log_container.setLayout(log_layout)
        splitter.addWidget(log_container)

        # Allow splitter to expand properly
        splitter.setStretchFactor(0, 2)  # Plot takes more space
        splitter.setStretchFactor(1, 1)  # Log takes less space

        main_layout.addWidget(splitter)

        # Finalize
        self.setLayout(main_layout)

        # Internal data & connections (preserved from previous version)
        self.devices = []
        self.running_devices = []
        self.workers = {}
        self.threads = {}
        self.plot_data = {}
        self.log_lines = {}
        self.statuses = {}

        self.start_button.clicked.connect(self.on_start)
        self.stop_button.clicked.connect(self.on_stop)
        self.save_log_button.clicked.connect(self.save_log)
        self.clear_graph_button.clicked.connect(self.clear_graph)
        self.save_graph_button.clicked.connect(self.save_graph)

        self.set_controls_enabled(False)
        self.clear_graph_button.setEnabled(False)

    def set_controls_enabled(self, enabled):
        self.start_button.setEnabled(enabled)
        self.stop_button.setEnabled(enabled)
        self.save_log_button.setEnabled(enabled)
        # Don't enable clear graph here, control separately based on test state
        self.save_graph_button.setEnabled(enabled)
        self.duration_input.setEnabled(enabled)
        self.rate_input.setEnabled(enabled)

    def update_buttons_state(self, serial):
        """Enable/disable buttons based on whether a test is running on device with serial."""
        running = serial in self.workers
        # Disable clear graph if running, enable otherwise
        self.clear_graph_button.setEnabled(not running)

        # Control start/stop buttons accordingly
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)

        # Disable duration/rate inputs while running
        self.duration_input.setEnabled(not running)
        self.rate_input.setEnabled(not running)

    def on_discovered_selection_changed(self):
        selected_rows = self.device_table.selectionModel().selectedRows()
        self.add_running_button.setEnabled(len(selected_rows) > 0)

    def add_to_running_tests(self):
        selected_rows = self.device_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        device = self.devices[row]

        if device.serial in [d.serial for d in self.running_devices]:
            QMessageBox.information(self, "Info", f"Device {device.serial} already added.")
            return

        self.running_devices.append(device)
        self.log_lines[device.serial] = []
        self.plot_data[device.serial] = []
        self.statuses[device.serial] = "Idle"

        row_pos = self.running_table.rowCount()
        self.running_table.insertRow(row_pos)
        self.running_table.setItem(row_pos, 0, QTableWidgetItem(device.model))
        self.running_table.setItem(row_pos, 1, QTableWidgetItem(device.serial))
        self.running_table.setItem(row_pos, 2, QTableWidgetItem(device.ip))
        self.running_table.setItem(row_pos, 3, QTableWidgetItem(str(device.port)))
        self.running_table.setItem(row_pos, 4, QTableWidgetItem(self.statuses[device.serial]))

    def on_running_selection_changed(self):
        selected_rows = self.running_table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_label.setText("Select a running test device to view.")
            self.log_output.clear()
            self.clear_graph()
            self.set_controls_enabled(False)
            self.clear_graph_button.setEnabled(False)
            return

        self.set_controls_enabled(True)
        row = selected_rows[0].row()
        device = self.running_devices[row]
        self.status_label.setText(f"Selected device: {device}")

        # Update buttons state based on running status
        self.update_buttons_state(device.serial)

        # Update log output
        self.log_output.clear()
        for line in self.log_lines.get(device.serial, []):
            self.log_output.append(line)

        # Update plot
        self.ax.clear()
        self.ax.set_title(f"Live Test Data for {device.serial}")
        self.ax.set_xlabel("Time (ms)")
        self.ax.set_ylabel("mV")
        points = self.plot_data.get(device.serial, [])
        if points:
            x, y = zip(*points)
            self.ax.plot(x, y, 'bo-')
        self.canvas.draw()

    def discover_devices(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(2)
        message = b"ID;"
        sock.sendto(message, (constants.MULTICAST_ADDR, constants.MULTICAST_PORT))

        devices = []
        try:
            while True:
                data, (ip, port) = sock.recvfrom(1024)
                decoded = data.decode('latin-1')
                parts = decoded.split(';')
                model = parts[1].split('=')[1]
                serial = parts[2].split('=')[1]
                devices.append(Device(ip, port, model, serial))
        except socket.timeout:
            pass
        sock.close()
        return devices

    def on_discover(self):
        self.devices = self.discover_devices()
        self.device_table.setRowCount(0)
        for device in self.devices:
            row_pos = self.device_table.rowCount()
            self.device_table.insertRow(row_pos)
            self.device_table.setItem(row_pos, 0, QTableWidgetItem(device.model))
            self.device_table.setItem(row_pos, 1, QTableWidgetItem(device.serial))
            self.device_table.setItem(row_pos, 2, QTableWidgetItem(device.ip))
            self.device_table.setItem(row_pos, 3, QTableWidgetItem(str(device.port)))

        self.add_running_button.setEnabled(False)
        if not self.devices:
            self.status_label.setText("🔍 No devices found.")
        else:
            self.status_label.setText(f"✅ {len(self.devices)} device(s) discovered.")

    def on_start(self):
        selected_rows = self.running_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Device Selected", "Please select a device from the 'Devices Testing' table before starting a test.")
            return

        row = selected_rows[0].row()
        device = self.running_devices[row]

        if device.serial in self.workers:
            self.status_label.setText("⚠️ Test already running on selected device.")
            return

        try:
            duration = int(self.duration_input.text())
            rate = int(self.rate_input.text())
        except ValueError:
            self.status_label.setText("❌ Invalid duration or rate input.")
            return

        # Clear previous data
        self.plot_data[device.serial] = []
        self.log_lines[device.serial].append(f"▶️ Sent start test command (Duration: {duration}s, Rate: {rate}ms)")
        self.update_log(device.serial)
        self.clear_graph(device.serial)
        self.update_status_in_running_table(device.serial, "Running")

        worker = DeviceWorker(device, duration=duration, rate=rate)
        worker.status_signal.connect(self.create_status_handler(device.serial))
        worker.data_signal.connect(self.create_data_handler(device.serial))
        worker.finished_signal.connect(self.create_finished_handler(device.serial))

        thread = threading.Thread(target=worker.start_test)
        self.workers[device.serial] = worker
        self.threads[device.serial] = thread

        thread.start()

        # Update buttons state (disable clear graph etc)
        self.update_buttons_state(device.serial)

    def remove_from_running_tests(self):
        selected_rows = self.running_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Device Selected", "Please select a device to remove from the 'Devices Testing' table.")
            return

        row = selected_rows[0].row()
        device = self.running_devices.pop(row)
        self.running_table.removeRow(row)
        self.statuses.pop(device.serial, None)
        self.plot_data.pop(device.serial, None)
        self.log_lines.pop(device.serial, None)
        self.workers.pop(device.serial, None)
        self.threads.pop(device.serial, None)

    def on_stop(self):
        selected_rows = self.running_table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_label.setText("❌ Select a running test device first.")
            return

        row = selected_rows[0].row()
        device = self.running_devices[row]
        worker = self.workers.get(device.serial)
        if worker:
            worker.stop_test()
            self.log_lines[device.serial].append(f"⏹️ Sent stop command to device.")
            self.update_log(device.serial)
            self.update_status_in_running_table(device.serial, "Stopping")
            # Buttons state might remain running until finished signal
            self.update_buttons_state(device.serial)
        else:
            self.status_label.setText("⚠️ No running test for selected device.")

    # Handlers factory for device-specific slots
    def create_status_handler(self, serial):
        def handle_status(msg):
            self.log_lines[serial].append(msg)
            self.update_status_in_running_table(serial, "Running")
            # Update UI only if this device is currently selected
            if self.get_selected_running_serial() == serial:
                self.status_label.setText(f"Status: {msg}")
                self.log_output.append(msg)
        return handle_status

    def create_data_handler(self, serial):
        def handle_data(time_ms, mv):
            self.plot_data[serial].append((time_ms, mv))
            # Update plot only if this device is currently selected
            if self.get_selected_running_serial() == serial:
                self.update_plot_for_serial(serial)
        return handle_data

    def create_finished_handler(self, serial):
        def handle_finished():
            finish_msg = f"✅ Test finished on {serial}"
            self.log_lines[serial].append(finish_msg)
            self.update_status_in_running_table(serial, "Idle")

            if self.get_selected_running_serial() == serial:
                self.status_label.setText(finish_msg)
                self.log_output.append(finish_msg)

            self.workers.pop(serial, None)
            self.threads.pop(serial, None)

            self.update_buttons_state(serial)  # ✅ Re-enable buttons like Clear Graph
        return handle_finished


    def update_plot_for_serial(self, serial):
        points = self.plot_data.get(serial, [])
        self.ax.clear()
        self.ax.set_title(f"Live Test Data for {serial}")
        self.ax.set_xlabel("Time (ms)")
        self.ax.set_ylabel("mV")
        if points:
            x, y = zip(*points)
            if len(x) > 100:
                self.ax.plot(x, y, 'bo-', markersize=2, linewidth=0.5)
            else:
                self.ax.plot(x, y, 'bo-')
        self.canvas.draw()

    def update_log(self, serial):
        self.log_output.clear()
        for line in self.log_lines.get(serial, []):
            self.log_output.append(line)

    def get_selected_running_serial(self):
        selected_rows = self.running_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        return self.running_devices[row].serial

    def clear_graph(self, serial=None):
        if serial is None:
            serial = self.get_selected_running_serial()
        if not serial:
            return
        # Only allow clearing if test NOT running for this device
        if serial in self.workers:
            self.status_label.setText("⚠️ Cannot clear graph while test is running.")
            return

        self.plot_data[serial] = []
        self.update_plot_for_serial(serial)  # ✅ Redraw the cleared graph

        if serial in self.log_lines:
            self.log_lines[serial].append("🧹 Graph cleared.")
        if self.get_selected_running_serial() == serial:
            self.log_output.append("🧹 Graph cleared.")


    def save_log(self):
        serial = self.get_selected_running_serial()
        if serial is None:
            self.status_label.setText("⚠️ Select a running test device to save log.")
            return

        lines = self.log_lines.get(serial, [])
        if not lines:
            self.status_label.setText("⚠️ No log data to save.")
            return

        options = QFileDialog.Options()
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Log File", "", "Text Files (*.txt);;All Files (*)", options=options)
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    for line in lines:
                        f.write(line + "\n")
                self.status_label.setText(f"💾 Log saved to {filepath}")
            except Exception as e:
                self.status_label.setText(f"❌ Failed to save log: {e}")

    def save_graph(self):
        serial = self.get_selected_running_serial()
        if serial is None:
            self.status_label.setText("⚠️ Select a running test device to save graph.")
            return

        options = QFileDialog.Options()
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Graph Image", "", "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)", options=options)
        if filepath:
            try:
                self.figure.savefig(filepath)
                self.status_label.setText(f"💾 Graph saved to {filepath}")
                self.log_lines[serial].append(f"💾 Graph saved to {filepath}")
                self.log_output.append(f"💾 Graph saved to {filepath}")
            except Exception as e:
                self.status_label.setText(f"❌ Failed to save graph: {e}")

    def update_status_in_running_table(self, serial, status):
        # Update the status column for device with serial in running table
        try:
            idx = next(i for i, d in enumerate(self.running_devices) if d.serial == serial)
            self.statuses[serial] = status
            self.running_table.setItem(idx, 4, QTableWidgetItem(status))
        except StopIteration:
            pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
