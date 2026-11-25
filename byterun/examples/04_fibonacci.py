# Fibonacci numbers using a loop and a list.
def fib_list(count):
    numbers = []
    a, b = 0, 1
    for _ in range(count):
        numbers.append(a)
        a, b = b, a + b
    return numbers

print(fib_list(12))
