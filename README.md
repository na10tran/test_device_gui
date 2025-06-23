Device Test GUI — Build & Run Instructions
Rocket Lab Production Automation Coding Test – Test Devices
Created by Nathan Tran
==========================================

OVERVIEW

This program provides a graphical interface to discover, monitor, and run tests on network-connected devices.
Users can:
- Start and stop tests
- View live voltage vs. time plots
- Save test logs and plots
- Manage multiple devices in parallel

==========================================

PREREQUISITES

• OS: Linux (tested on Ubuntu 20.04+)
• Python Version: 3.7 or higher
• Required Python Packages:
- PyQt5
- matplotlib

==========================================

INSTALLATION

Step 1 — Install Python and pip:
sudo apt update
sudo apt install python3 python3-pip

Step 2 — Install required Python packages:
pip3 install PyQt5 matplotlib

==========================================

RUNNING THE PROGRAM FROM SOURCE

Clone or download the repository:

git clone <repository-url>
cd <repository-directory>

Run the main program:

python3 main_window.py

This will open the Device Test GUI window.

==========================================

OPTIONAL — BUILDING A STANDALONE EXECUTABLE

You can package the GUI into a standalone binary using PyInstaller so the user doesn’t need to install Python or dependencies.

Step 1 — Install PyInstaller:
pip3 install pyinstaller

Step 2 — Build the executable:
pyinstaller --onefile --add-data "style.qss:." main_window.py

Step 3 — Locate and run the executable:
cd dist
./main_window

==========================================

TROUBLESHOOTING

• No Devices Discovered:
Ensure devices are created and running

• Graph or Logs Not Appearing:

Make sure a device is selected

Ensure valid duration and rate are set before starting the test

==========================================
