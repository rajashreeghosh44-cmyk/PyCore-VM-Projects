# Classes and objects running on the VM.
class Counter(object):
    def __init__(self):
        self.value = 0

    def add(self, amount):
        self.value = self.value + amount
        return self.value

c = Counter()
c.add(5)
c.add(10)
print("Counter value:", c.value)
