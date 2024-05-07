class ServerConnectionException(Exception):
    def __init__(self, message="Program exception"):
        self.message = message
        super().__init__(self.message)


class ChainException(Exception):
    def __init__(self, message="Program exception"):
        self.message = message
        super().__init__(self.message)