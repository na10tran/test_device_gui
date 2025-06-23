class Device:
    """
        Represents a network device with identifying and connection information.

        :attribute ip (str) IP address of the device.
        :attribute port (int) Port number used to communicate with the device.
        :attribute model (str) Model identifier of the device.
        :attribute serial (str) Serial number of the device.

    """
    
    def __init__(self, ip, port, model, serial):
        self.ip = ip
        self.port = port
        self.model = model
        self.serial = serial

    def __str__(self):
        return f"{self.model}:{self.serial} @ {self.ip}:{self.port}"