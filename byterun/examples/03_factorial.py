# A recursive function: shows the call stack growing (call depth).
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print("5! =", factorial(5))
print("8! =", factorial(8))
