class Device:
    def __init__(self, ip, port, model, serial):
        self.ip = ip
        self.port = port
        self.model = model
        self.serial = serial
    def __str__(self):
        return f"{self.model}:{self.serial} @ {self.ip}:{self.port}"