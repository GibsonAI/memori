class UnitTestX:
    def __init__(self):
        self.a = 1
        self.b = 2


class UnitTestY:
    def __init__(self):
        self.c = 3
        self.d = UnitTestX()
