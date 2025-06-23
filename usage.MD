# 📘 Device Test GUI — Usage Guide

This program provides a graphical interface to scan, monitor, and run tests on network-connected devices. Users can configure test duration and frequency, observe real-time voltage/ampere data, and save logs and graphs.

---

## Using the GUI

### 1. Scan for Devices
- Click the **"Scan Devices"** button.
- Discovered devices will appear in the left table labeled **"Discovered Devices"**.

### 2. Add Device to Testing
- Select a device in the discovered list.
- Click **"Add to Testing"**.
- The device will be listed in the right table under **"Devices in Test"**.

### 3. ▶Start a Test
- Select a device from the **"Devices in Test"** table.
- Input:
  - **Test Duration** (in seconds)
  - **Status Rate** (in milliseconds)
- Click **"Start Test"**.
- Live voltage-vs-time graph and test logs will appear.

### 4. Stop a Test
- Click **"Stop Test"** to end a running test early.

### 5.  View & Save Logs and Graphs
- Real-time data and logs are displayed in the lower section.
- Click **"Save Graph"** to export the current plot.
- Click **"Save Log"** to export the log file for the selected device.

### 6. Remove Device from Testing
- Select a device from the right table.
- Click **"Remove from Testing"** to clear it from the test list.

---

## Notes and Behaviors
- The graph is automatically cleared when a new test begins.
- The graph cannot be cleared while a test is running.
- Log and plot data are tied to the device’s serial number.
- Controls are disabled when no device is selected to prevent invalid operations.

---

## Output Files
- **Log File:** `log_<serial>.txt`
- **Graph Image:** `graph.png`
- You choose the filename and location when saving.

---

## Dependencies
The program uses the following third-party libraries:
- **PyQt5** — GUI framework
- **matplotlib** — for graph plotting


---

