#! decorator function to time other functions
from time import perf_counter_ns

def calcTime(func):
    def inner1(*args, **kwargs):
        print(f"{func.__name__}({args, kwargs})")
        begin = perf_counter_ns()
        func(*args, **kwargs)
        end = perf_counter_ns()
        time = end-begin
        return time
    return inner1