# A program with a runtime error: the VM shows where it happened.
def divide(x, y):
    return x / y

def calculate():
    return divide(10, 0)

print("Starting...")
calculate()
print("This line is never reached")
