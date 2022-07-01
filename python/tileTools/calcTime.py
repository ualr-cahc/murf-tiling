#! decorator function to time other functions
from time import perf_counter_ns
from types import FunctionType

def calcTime(func: FunctionType) -> tuple[int, any]:
    """Decorator function that returns the time taken by a function call
    in nanoseconds and the original return values of the decorated function"""
    def inner1(*args, **kwargs):
        begin = perf_counter_ns()
        func(*args, **kwargs)
        end = perf_counter_ns()
        time = end-begin
        return time
    return inner1