import sys
import os
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QHBoxLayout, QTextEdit, QSizePolicy, QFileDialog, QLineEdit,
    QFormLayout, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QGroupBox, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from device_worker import DeviceWorker
from device_manager import DeviceManager

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Device Test GUI")
        self.resize(1200, 900)

        # Container widget for entire UI content
        container = QWidget()
        container_layout = QVBoxLayout(container)

        self.manager = DeviceManager()

        # === Discover Devices ===
        discover_layout = QHBoxLayout()
        self.discover_button = QPushButton("Scan Devices")
        self.discover_button.setMaximumWidth(200)
        self.discover_button.clicked.connect(self.on_discover)
        discover_layout.addWidget(self.discover_button)
        discover_layout.addStretch()
        container_layout.addLayout(discover_layout)

        # === Discovered & Running Tables ===
        self.device_table = QTableWidget(0, 4)
        self.device_table.setHorizontalHeaderLabels(["Model", "Serial", "IP", "Port"])
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.device_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.device_table.setSelectionMode(QTableWidget.SingleSelection)
        self.device_table.setMinimumHeight(100)
        self.device_table.setMaximumHeight(120)
        self.device_table.itemSelectionChanged.connect(self.on_discovered_selection_changed)

        self.running_table = QTableWidget(0, 5)
        self.running_table.setHorizontalHeaderLabels(["Model", "Serial", "IP", "Port", "Status"])
        self.running_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.running_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.running_table.setSelectionMode(QTableWidget.SingleSelection)
        self.running_table.setMinimumHeight(100)
        self.running_table.setMaximumHeight(120)
        self.running_table.itemSelectionChanged.connect(self.on_running_selection_changed)

        discovered_layout = QVBoxLayout()
        discovered_label = QLabel("Discovered Devices:")
        discovered_layout.addWidget(discovered_label)
        discovered_layout.addWidget(self.device_table)

        running_layout = QVBoxLayout()
        running_label = QLabel("Devices in Test:")
        running_layout.addWidget(running_label)
        running_layout.addWidget(self.running_table)

        tables_layout = QHBoxLayout()
        tables_layout.addLayout(discovered_layout)
        tables_layout.addLayout(running_layout)
        tables_layout.setStretch(0, 1)
        tables_layout.setStretch(1, 1)
        tables_layout.setSpacing(20)

        container_layout.addLayout(tables_layout)

        # === Add/Remove Buttons ===
        device_action_layout = QHBoxLayout()
        self.add_running_button = QPushButton("Add to Testing")
        self.add_running_button.setEnabled(False)
        self.add_running_button.clicked.connect(self.add_to_running_tests)
        self.remove_running_button = QPushButton("Remove from Testing")
        self.remove_running_button.setEnabled(False)
        self.remove_running_button.clicked.connect(self.remove_from_running_tests)
        device_action_layout.addWidget(self.add_running_button)
        device_action_layout.addWidget(self.remove_running_button)
        container_layout.addLayout(device_action_layout)

        # === Status Display ===
        status_group = QGroupBox("Current Device Status")
        status_group_layout = QVBoxLayout()
        self.status_label = QLabel("Status: Idle")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        status_group_layout.addWidget(self.status_label)
        status_group.setLayout(status_group_layout)
        container_layout.addWidget(status_group)

        # === Test Control Section ===
        test_control_group = QGroupBox("Test Controls")
        test_control_layout = QVBoxLayout()
        control_btn_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Test")
        self.stop_button = QPushButton("Stop Test")
        control_btn_layout.addWidget(self.start_button)
        control_btn_layout.addWidget(self.stop_button)

        form_layout = QFormLayout()
        self.duration_input = QLineEdit("10")
        self.rate_input = QLineEdit("1000")
        form_layout.addRow("Test Duration (s):", self.duration_input)
        form_layout.addRow("Status Rate (ms):", self.rate_input)

        test_control_layout.addLayout(control_btn_layout)
        test_control_layout.addLayout(form_layout)
        test_control_group.setLayout(test_control_layout)
        container_layout.addWidget(test_control_group)

        # === Output Display Section ===
        output_group = QGroupBox("Device Output Display")
        output_group_layout = QVBoxLayout()

        # Selected device label
        self.selected_device_label = QLabel("Displaying Data for Selected Device: None")
        self.selected_device_label.setWordWrap(True)
        self.selected_device_label.setObjectName("statusLabel")
        output_group_layout.addWidget(self.selected_device_label)

        # Splitter (Plot + Log)
        splitter = QSplitter(Qt.Vertical)

        # Plot container
        plot_container = QWidget()
        plot_layout = QVBoxLayout(plot_container)

        self.figure = Figure(figsize=(6, 2.2), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Main axis for voltage (mV)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Live Test Data")
        self.ax.set_xlabel("Time (ms)")
        self.ax.set_ylabel("mV", color='b')
        self.ax.tick_params(axis='y', colors='b')

        # Twin axis for current (mA)
        self.ax2 = self.ax.twinx()
        self.ax2.set_ylabel("mA", color='r')
        self.ax2.tick_params(axis='y', colors='r')
        self.canvas.setMaximumHeight(300)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)

        graph_btn_layout = QHBoxLayout()
        self.save_graph_button = QPushButton("Save Graph")
        self.clear_graph_button = QPushButton("Clear Graph")
        graph_btn_layout.addWidget(self.save_graph_button)
        graph_btn_layout.addWidget(self.clear_graph_button)
        plot_layout.addLayout(graph_btn_layout)

        plot_container.setMinimumHeight(140)
        splitter.addWidget(plot_container)

        # Log container
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(100)
        log_layout.addWidget(self.log_output)

        self.save_log_button = QPushButton("Save Log")
        log_layout.addWidget(self.save_log_button)
        splitter.addWidget(log_container)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        output_group_layout.addWidget(splitter)
        output_group.setLayout(output_group_layout)
        container_layout.addWidget(output_group)

        # === Connect signals ===
        self.start_button.clicked.connect(self.on_start)
        self.stop_button.clicked.connect(self.on_stop)
        self.save_log_button.clicked.connect(self.save_log)
        self.clear_graph_button.clicked.connect(self.clear_graph)
        self.save_graph_button.clicked.connect(self.save_graph)

        self.set_controls_enabled(False)
        self.clear_graph_button.setEnabled(False)

        # === Scroll Area wrapping container ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)

        # Set scroll as the only widget of this window
        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(scroll)

# ------------------------- ON METHPDS -------------------------
    def on_discover(self):
        """
            Scans the network for available devices using the discover device command. 
            Devices are discovered over the network via a multicast UDP request handled inside the DeviceManager.

        """

        devices = self.manager.discover_devices()    # finds devices via UDP

        self.device_table.setRowCount(0)
        for device in devices:    # adds each device found
            row = self.device_table.rowCount()
            self.device_table.insertRow(row)
            self.device_table.setItem(row, 0, self.create_readonly_item(device.model))
            self.device_table.setItem(row, 1, self.create_readonly_item(device.serial))
            self.device_table.setItem(row, 2, self.create_readonly_item(device.ip))
            self.device_table.setItem(row, 3, self.create_readonly_item(str(device.port)))

        self.add_running_button.setEnabled(False)   

        if not devices:
            self.status_label.setText("No devices found.")
        else:
            self.status_label.setText(f"{len(devices)} device(s) discovered.")
            self.add_running_button.setEnabled(False)

    def on_start(self):
        """
            Starts the test for the selected device. It uses the input fields and starts a 
            DeviceWorker in a new thread to perform the test. The UI is updated accordingly.

        """

        selected = self.running_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        serial = self.running_table.item(row, 1).text()    # Get device serial from table
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
        self.update_log(serial)    #update log display box

        worker = DeviceWorker(device, duration=duration, rate=rate)    # create a worker for the test
        # Connect signals to handle status updates, data points, and test completion
        worker.status_signal.connect(lambda msg: self.on_status(serial, msg))
        worker.data_signal.connect(lambda t, mv, ma: self.on_data(serial, t, mv, ma))
        worker.finished_signal.connect(lambda: self.on_finished(serial))

        thread = threading.Thread(target=worker.start_test)    # Run worker in a background thread
        thread.start()

        self.manager.set_worker(serial, worker, thread)    # Save worker and thread references
        self.update_status_column(serial, "Testing")  

    def on_stop(self):
        """
            Stops the currently selected running device's test and updates the log.

        """

        selected = self.running_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        serial = self.running_table.item(row, 1).text()
        worker = self.manager.workers.get(serial)

        # stops the worker test and logs action
        if worker:
            worker.stop_test()
            self.manager.append_log(serial, "Stop Test")
            self.update_log(serial)
    
    def on_data(self, serial, t, mv, ma):
        """
            Handles incoming data point from a running test device. Appends data point to plot
            and updates plot UI

            :param serial (string) The serial number of the device
            :param t (int) The timestamp (in milliseconds) of the data point.
            :param mv (float) The measured voltage value in millivolts.
            :param ma (float) The measured amp value in milliamps.

        """

        self.manager.append_plot_data(serial, t, mv, ma)

        # Only update the plot if this device is currently selected
        current_serial = self.get_selected_running_serial()
        if current_serial == serial:
            self.update_plot(serial)

    def on_finished(self, serial):
        """
            Handles the completion of a test for a specific device. Triggered when DeviceWorker
            signals that the test is finished.

            :param serial (string) The serial number of the device

        """

        self.manager.append_log(serial, "Test Finished")
        self.manager.clear_worker(serial)
        self.update_log(serial)
        self.set_controls_enabled(True)
        self.update_status_column(serial, "Completed")

    def on_status(self, serial, msg):
        """
            Handles incoming status messages during a running test. This method logs the status message, 
            updates the log view and test status in the UI

            :param serial (string) The serial number of the device
            :param msg (string) The status message received from the device.

        """

        self.manager.append_log(serial, msg)
        self.update_log(serial)
        self.update_status_column(serial, "Testing")  # Update to Testing

        # Find row for the device's serial
        for row in range(self.running_table.rowCount()):
            if self.running_table.item(row, 1).text() == serial:
                # update status cell with current status from manager 
                self.running_table.setItem(row, 4, QTableWidgetItem(self.manager.get_status(serial)))
                break

    def on_discovered_selection_changed(self):
        """
            Enables "Add to Testing" button only if a device is selected
            in the discovered devices table. Prevents users from adding
            devices to testing when none are selected.
        """

        self.add_running_button.setEnabled(bool(self.device_table.selectedItems()))

    def on_running_selection_changed(self):
        """
            Handles the event when the selection in the devices in test table changes.
            The graph, log, status labels, and controls are updated accordingly.
        """
        
        selected_rows = self.running_table.selectionModel().selectedRows()

        if not selected_rows:
            self.selected_device_label.setText("Displaying Data for Selected Device: None")  # Clear label when none selected
            self.log_output.clear()
            self.clear_graph()
            self.set_controls_enabled(False)
            self.clear_graph_button.setEnabled(False)
            self.remove_running_button.setEnabled(False)    # disables remove from testing button
            return

        self.set_controls_enabled(True)    # enables input fields and controls
        self.remove_running_button.setEnabled(True)    # enables remove from testing button

        row = selected_rows[0].row()
        device = self.manager.running_devices[row]

        device_info = f"{device.model} (S/N: {device.serial})" 
        self.selected_device_label.setText(f"Displaying Data for Selected Device: {device_info}")
        self.status_label.setText(f"Selected device: {device_info}")

        # Updates log output
        self.log_output.clear()
        for line in self.manager.get_log(device.serial):
            self.log_output.append(line)

        # Update graph plot
        self.update_plot(device.serial)

        # Enable clear graph button only if test is not running
        self.clear_graph_button.setEnabled(not self.manager.is_running(device.serial))

# ------------------------- ON METHPDS -------------------------
    def add_to_running_tests(self):
        """
            Adds a selected device from the discovered devices table to the "Devices in Test" table
            and updates the internal manager to track the device as running(idle state)

        """

        selected_rows = self.device_table.selectionModel().selectedRows()    # grabs selected row in discovered devices
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        device = self.manager.devices[row]

        if any(d.serial == device.serial for d in self.manager.running_devices):
            QMessageBox.information(self, "Info", f"Device {device.serial} already added.")
            return

        self.manager.add_running_device(device)

        # Add to devices in test table
        row_pos = self.running_table.rowCount()
        self.running_table.insertRow(row_pos)
        self.running_table.setItem(row_pos, 0, self.create_readonly_item(device.model))
        self.running_table.setItem(row_pos, 1, self.create_readonly_item(device.serial))
        self.running_table.setItem(row_pos, 2, self.create_readonly_item(device.ip))
        self.running_table.setItem(row_pos, 3, self.create_readonly_item(str(device.port)))
        self.running_table.setItem(row_pos, 4, self.create_readonly_item(self.manager.get_status(device.serial)))

        self.running_table.setItem(row_pos, 4, QTableWidgetItem("Idle"))
        self.apply_row_style(row_pos, "Idle")

    def remove_from_running_tests(self):
        """
            Removes the selected device(s) from devices in test table and updates the GUI. 
            The graph and log display is cleared if no devices remain and the control buttons
            are also disabled.
        """

        selected_rows = self.running_table.selectionModel().selectedRows()    # gets selected row(s)
        if not selected_rows:
            return

        for selected in selected_rows:
            row = selected.row()
            device = self.manager.running_devices[row]
            self.running_table.blockSignals(True)
            self.manager.remove_running_device(device.serial)    # remove device from device manager 
            self.running_table.removeRow(row)    # removes row from devices in test
            self.running_table.blockSignals(False)

        if self.running_table.rowCount() == 0:    # clears graph, log, and disables controls
            self.running_table.clearSelection()
            self.running_table.setCurrentCell(-1, -1)
            self.remove_running_button.setEnabled(False)
            self.status_label.setText("Status: Idle")
            self.selected_device_label.setText("Displaying Data for Selected Device: None")
            self.log_output.clear()
            self.clear_graph()            
            self.update_plot(serial=None)
            self.set_controls_enabled(False)
            self.clear_graph_button.setEnabled(False)

    def set_controls_enabled(self, enabled):
        """
            Enable or disable test device control UI elements.

            :param enabled (bool) boolean to determine if control input and buttons are to be disabled
        """

        self.start_button.setEnabled(enabled)
        self.stop_button.setEnabled(enabled)
        self.save_log_button.setEnabled(enabled)
        self.save_graph_button.setEnabled(enabled)
        self.duration_input.setEnabled(enabled)
        self.rate_input.setEnabled(enabled)

    def update_status_column(self, serial, status):
        """
            Updates the status column in the running devices table for a specific device.

            :param serial (string) The serial number of the device
            :param status (string) The new status to display (e.g: "Testing", "Completed")

        """

        for row in range(self.running_table.rowCount()):
            item = self.running_table.item(row, 1)    # gets serial number (col 1)
            if item and item.text() == serial:
                status_item = QTableWidgetItem(status)
                status_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)    # Make it read-only
                self.running_table.setItem(row, 4, status_item)
                self.running_table.viewport().update()

                break

    def get_selected_running_serial(self):
        """
            Get the serial number of the currently selected device in the devices in test table.

        """

        selected_rows = self.running_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        device = self.manager.running_devices[row]
        return device.serial
 
 # ------------------------- DEVICE DATA METHPDS -------------------------   
    def update_plot(self, serial=None):
        """
            Updates the plot area with test data for a given device serial number or displays no data if no device.

            :param serial (string or None) The serial number of the device.
        """

        self.ax.clear()
        self.ax2.clear()
        self.ax.set_title("Live Test Data" if serial is None else f"Live Test Data for {serial}")
        self.ax.set_xlabel("Time (ms)")
        self.ax.set_ylabel("mV")
        self.ax2.set_ylabel("mA")
        self.ax2.yaxis.set_label_position('right')

        if serial is None:
            points = []
        else:
            points = self.manager.get_plot_data(serial)  # expecting list of (time_ms, mv, ma)

        if points:
            time_ms, mv_vals, ma_vals = zip(*points)

            mv_min, mv_max = min(mv_vals), max(mv_vals)
            ma_min, ma_max = min(ma_vals), max(ma_vals)

            # Ensure min < max for both
            if mv_min > mv_max:
                mv_min, mv_max = mv_max, mv_min

            if ma_min > ma_max:
                ma_min, ma_max = ma_max, ma_min

            # Add padding
            mv_range = mv_max - mv_min
            ma_range = ma_max - ma_min

            self.ax.set_ylim(mv_min - 0.1 * mv_range, mv_max + 0.1 * mv_range)
            #self.ax2.set_ylim(ma_min - 0.1 * ma_range, ma_max + 0.1 * ma_range)
            self.ax2.set_ylim(-500, 500)

            # Plot mV on primary y-axis
            if len(time_ms) > 100:
                self.ax.plot(time_ms, mv_vals, 'bo-', label='Voltage (mV)', linewidth=1.5, markersize=5)
            else:
                self.ax.plot(time_ms, mv_vals, 'bo-', label='Voltage (mV)', linewidth=1.5, markersize=5)

            # Create twin y-axis for current (mA)
            if len(time_ms) > 100:
                self.ax2.plot(time_ms, ma_vals, 'r^-', label='Current (mA)', linewidth=1, markersize=5)
            else:
                self.ax2.plot(time_ms, ma_vals, 'r^-', label='Current (mA)', linewidth=1, markersize=5)

            # Optional: color the tick labels to match line colors
            self.ax.tick_params(axis='y', colors='b')
            self.ax2.tick_params(axis='y', colors='r')
            self.ax2.yaxis.set_ticks_position('right')

            # Optionally add legends (on primary axis)
            self.ax.legend(loc='upper left')
            self.ax2.legend(loc='upper right')

        else:
            self.ax.text(
                0.5, 0.5, "No data",
                transform=self.ax.transAxes,
                ha='center', va='center',
                fontsize=12, color='gray'
            )
        self.canvas.draw()

    def clear_graph(self):
        """
            Clears the plotted graph for the currently selected running test device,
            if a device is selected and its test is not actively running.

        """

        serial = self.get_selected_running_serial()
        if not serial:
            self.status_label.setText("Select a running test device to clear its graph.")
            return

        # Only allow clearing if test is not running
        if self.manager.is_running(serial):
            self.status_label.setText("Cannot clear graph while test is running.")
            return

        # clears stored data for device and refreshes graph
        self.manager.clear_plot(serial)    
        self.update_plot(serial)

        # Log and show message if the cleared device is currently selected
        self.manager.append_log(serial, "Graph cleared.")
        if self.get_selected_running_serial() == serial:
            self.log_output.append("Graph cleared.")

    def save_graph(self):
        """
            Saves the current graph as an image file.

        """

        # opens save file dialog to save graph image
        path, _ = QFileDialog.getSaveFileName(self, "Save Graph", "graph.png")
        if path:
            self.figure.savefig(path)

    def update_log(self, serial):
        """
            Updates the log display with messages for the specified device.

            :param serial (string) serial number of the device whose log messages should be displayed.
        """

        self.log_output.clear()
        for line in self.manager.get_log(serial):
            self.log_output.append(line)

    def save_log(self):
        """
            Saves the log of the currently selected running device to a user-specified txt file.

        """

        selected = self.running_table.selectedItems()

        if not selected:
            return
        
        # grabs log data from selected device
        row = selected[0].row()
        serial = self.running_table.item(row, 1).text()
        lines = self.manager.get_log(serial)
        if not lines:
            return

        # opens save file dialog to save log
        path, _ = QFileDialog.getSaveFileName(self, "Save Log", f"log_{serial}.txt")
        if path:
            with open(path, 'w') as f:
                f.write('\n'.join(lines))

 # ------------------------- UI EDITING METHODS -------------------------   
    def create_readonly_item(self, text):
        """
            Creates a non-editable QTableWidgetItem with the given text string.

            :param text (string) text to display in the table cell
        """

        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def apply_row_style(self, row, status):
        """
            Applies background color styling to a row in the running devices table
            based on the test status of the device.

            :param row: (int) Row index to apply the style.
            :param status: (str) The current status string of the device
        """

        color = QColor()
        if "running" in status.lower():
            color = QColor(255, 255, 204)    # Light yellow
        elif "finished" in status.lower() or "complete" in status.lower():
            color = QColor(204, 255, 204)    # Light green
        else:
            return  

        for col in range(self.running_table.columnCount()):    # changes all columns in row
            self.running_table.item(row, col).setBackground(color)


def resource_path(relative_path):
    """
        Get the absolute path to a resource

        :param relative_path (string)The relative path to the resource file.

    """

    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Load and apply stylesheet
    style_path = resource_path("style.qss")
    with open(style_path, "r") as f:
        app.setStyleSheet(f.read())

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

