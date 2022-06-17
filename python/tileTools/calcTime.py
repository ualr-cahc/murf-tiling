#! decorator function to time other functions
from time import perf_counter

def calcTime(func):
    def inner1(*args, **kwargs):
        begin = perf_counter()
        func(*args, **kwargs)
        end = perf_counter()
        time = end-begin
        print(func.__name__, f"time {time//60}m {round(time%60)}s")
    return inner1