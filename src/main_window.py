import sys
import socket
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QHBoxLayout, QTextEdit, QSizePolicy, QFileDialog, QLineEdit,
    QFormLayout, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from device_worker import DeviceWorker
import constants
from device import Device
from device_manager import DeviceManager

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Device Test GUI")
        self.resize(1200, 900)

        self.manager = DeviceManager()

        main_layout = QVBoxLayout(self)

        discover_layout = QHBoxLayout()
        self.discover_button = QPushButton("Discover Devices")
        self.discover_button.clicked.connect(self.on_discover)
        discover_layout.addWidget(self.discover_button)
        main_layout.addLayout(discover_layout)

        self.device_table = QTableWidget(0, 4)
        self.device_table.setHorizontalHeaderLabels(["Model", "Serial", "IP", "Port"])
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.device_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.device_table.setSelectionMode(QTableWidget.SingleSelection)
        self.device_table.itemSelectionChanged.connect(self.on_discovered_selection_changed)
        self.device_table.setMinimumHeight(150)  # Increase as needed

        main_layout.addWidget(QLabel("Discovered Devices:"))
        main_layout.addWidget(self.device_table)

        device_action_layout = QHBoxLayout()
        self.add_running_button = QPushButton("Add to Testing Devices")
        self.add_running_button.setEnabled(False)
        self.add_running_button.clicked.connect(self.add_to_running_tests)
        self.remove_running_button = QPushButton("Remove from Testing Devices")
        self.remove_running_button.clicked.connect(self.remove_from_running_tests)
        device_action_layout.addWidget(self.add_running_button)
        device_action_layout.addWidget(self.remove_running_button)
        main_layout.addLayout(device_action_layout)

        self.running_table = QTableWidget(0, 5)
        self.running_table.setHorizontalHeaderLabels(["Model", "Serial", "IP", "Port", "Status"])
        self.running_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.running_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.running_table.setSelectionMode(QTableWidget.SingleSelection)
        self.running_table.itemSelectionChanged.connect(self.on_running_selection_changed)

        main_layout.addWidget(QLabel("Devices Testing:"))
        self.running_table.setMinimumHeight(150)  # Adjust based on preference
        main_layout.addWidget(self.running_table)

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

        splitter = QSplitter(Qt.Vertical)

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

        graph_btn_layout = QHBoxLayout()
        self.save_graph_button = QPushButton("Save Graph")
        self.clear_graph_button = QPushButton("Clear Graph")
        graph_btn_layout.addWidget(self.save_graph_button)
        graph_btn_layout.addWidget(self.clear_graph_button)
        plot_layout.addLayout(graph_btn_layout)
        plot_container.setMinimumHeight(300)  # or any height you prefer

        splitter.addWidget(plot_container)

        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        log_layout.addWidget(self.log_output)
        self.save_log_button = QPushButton("Save Log")
        log_layout.addWidget(self.save_log_button)

        splitter.addWidget(log_container)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

        self.setLayout(main_layout)

        self.start_button.clicked.connect(self.on_start)
        self.stop_button.clicked.connect(self.on_stop)
        self.save_log_button.clicked.connect(self.save_log)
        self.clear_graph_button.clicked.connect(self.clear_graph)
        self.save_graph_button.clicked.connect(self.save_graph)

        self.set_controls_enabled(False)
        self.clear_graph_button.setEnabled(False)

    def on_discover(self):
        self.manager.clear_devices()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(2)
        message = b"ID;"
        sock.sendto(message, (constants.MULTICAST_ADDR, constants.MULTICAST_PORT))
        try:
            while True:
                data, (ip, port) = sock.recvfrom(1024)
                decoded = data.decode('latin-1')
                parts = decoded.split(';')
                model = parts[1].split('=')[1]
                serial = parts[2].split('=')[1]
                self.manager.add_device(Device(ip, port, model, serial))
        except socket.timeout:
            pass
        sock.close()

        self.device_table.setRowCount(0)
        for device in self.manager.devices:
            row = self.device_table.rowCount()
            self.device_table.insertRow(row)
            self.device_table.setItem(row, 0, QTableWidgetItem(device.model))
            self.device_table.setItem(row, 1, QTableWidgetItem(device.serial))
            self.device_table.setItem(row, 2, QTableWidgetItem(device.ip))
            self.device_table.setItem(row, 3, QTableWidgetItem(str(device.port)))

        self.add_running_button.setEnabled(False)
        if not self.manager.devices:
            self.status_label.setText("🔍 No devices found.")
        else:
            self.status_label.setText(f"✅ {len(self.manager.devices)} device(s) discovered.")

    def on_discovered_selection_changed(self):
        self.add_running_button.setEnabled(bool(self.device_table.selectedItems()))

    def add_to_running_tests(self):
        selected_rows = self.device_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        device = self.manager.devices[row]

        if any(d.serial == device.serial for d in self.manager.running_devices):
            QMessageBox.information(self, "Info", f"Device {device.serial} already added.")
            return

        self.manager.add_running_device(device)

        # Add to GUI table
        row_pos = self.running_table.rowCount()
        self.running_table.insertRow(row_pos)
        self.running_table.setItem(row_pos, 0, QTableWidgetItem(device.model))
        self.running_table.setItem(row_pos, 1, QTableWidgetItem(device.serial))
        self.running_table.setItem(row_pos, 2, QTableWidgetItem(device.ip))
        self.running_table.setItem(row_pos, 3, QTableWidgetItem(str(device.port)))
        self.running_table.setItem(row_pos, 4, QTableWidgetItem(self.manager.get_status(device.serial)))


    def remove_from_running_tests(self):
        selected_rows = self.running_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Device Selected", "Please select a device to remove from the 'Devices Testing' table.")
            return

        row = selected_rows[0].row()

        if row < 0 or row >= len(self.manager.running_devices):
            QMessageBox.warning(self, "Invalid Selection", "The selected device no longer exists in the test list.")
            return

        device = self.manager.running_devices.pop(row)
        self.running_table.removeRow(row)

        self.manager.remove_running_device(device.serial)

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
        device = self.manager.running_devices[row]
        self.status_label.setText(f"Selected device: {device}")

        #self.update_buttons_state(device.serial)

        # Update log output
        self.log_output.clear()
        for line in self.manager.get_log(device.serial):
            self.log_output.append(line)

        # Update plot
        self.update_plot_for_serial(device.serial)

        # ✅ Enable clear graph button only if test is not running
        self.clear_graph_button.setEnabled(not self.manager.is_running(device.serial))

    def update_log(self, serial):
        self.log_output.clear()
        for line in self.manager.get_log(serial):
            self.log_output.append(line)

    def update_plot(self, serial):
        self.ax.clear()
        self.ax.set_title(f"Live Test Data for {serial}")
        self.ax.set_xlabel("Time (ms)")
        self.ax.set_ylabel("mV")
        points = self.manager.get_plot_data(serial)
        if points:
            x, y = zip(*points)
            self.ax.plot(x, y, 'bo-')
        self.canvas.draw()

    def set_controls_enabled(self, enabled):
        self.start_button.setEnabled(enabled)
        self.stop_button.setEnabled(enabled)
        self.save_log_button.setEnabled(enabled)
        self.save_graph_button.setEnabled(enabled)
        self.duration_input.setEnabled(enabled)
        self.rate_input.setEnabled(enabled)

    def get_selected_running_serial(self):
        selected_rows = self.running_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        device = self.manager.running_devices[row]
        return device.serial

    def clear_graph(self):
        serial = self.get_selected_running_serial()
        if not serial:
            self.status_label.setText("⚠️ Select a running test device to clear its graph.")
            return

        # Only allow clearing if test is NOT running
        if self.manager.is_running(serial):
            self.status_label.setText("Cannot clear graph while test is running.")
            return

        self.manager.clear_plot(serial)
        self.update_plot_for_serial(serial)

        self.manager.append_log(serial, "🧹 Graph cleared.")
        if self.get_selected_running_serial() == serial:
            self.log_output.append("🧹 Graph cleared.")


    def save_log(self):
        selected = self.running_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        serial = self.running_table.item(row, 1).text()
        lines = self.manager.get_log(serial)
        if not lines:
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save Log", f"log_{serial}.txt")
        if path:
            with open(path, 'w') as f:
                f.write('\n'.join(lines))

    def save_graph(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Graph", "graph.png")
        if path:
            self.figure.savefig(path)

    def on_start(self):
        selected = self.running_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        serial = self.running_table.item(row, 1).text()
        device = next((d for d in self.manager.running_devices if d.serial == serial), None)
        if not device:
            return
        try:
            duration = int(self.duration_input.text())
            rate = int(self.rate_input.text())
        except ValueError:
            return

        self.manager.clear_plot(serial)
        self.manager.append_log(serial, f"▶️ Start Test: {duration}s @ {rate}ms")
        self.update_log(serial)

        worker = DeviceWorker(device, duration=duration, rate=rate)
        worker.status_signal.connect(lambda msg: self.on_status(serial, msg))
        worker.data_signal.connect(lambda t, mv: self.on_data(serial, t, mv))
        worker.finished_signal.connect(lambda: self.on_finished(serial))

        thread = threading.Thread(target=worker.start_test)
        thread.start()

        self.manager.set_worker(serial, worker, thread)

    def on_stop(self):
        selected = self.running_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        serial = self.running_table.item(row, 1).text()
        worker = self.manager.workers.get(serial)
        if worker:
            worker.stop_test()
            self.manager.append_log(serial, "⏹️ Stop Test")
            self.update_log(serial)

    def on_status(self, serial, msg):
        self.manager.append_log(serial, msg)
        self.update_log(serial)

    def on_data(self, serial, t, mv):
        self.manager.append_plot_data(serial, t, mv)
        self.update_plot(serial)

    def on_finished(self, serial):
        self.manager.append_log(serial, "✅ Test Finished")
        self.manager.clear_worker(serial)
        self.update_log(serial)
        self.set_controls_enabled(True)

    def update_plot_for_serial(self, serial):
        """Redraws the plot for a specific device based on its collected test data."""
        points = self.manager.get_plot_data(serial)
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
        else:
            self.ax.text(0.5, 0.5, "No data", transform=self.ax.transAxes,
                        ha='center', va='center', fontsize=12, color='gray')

        self.canvas.draw()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
