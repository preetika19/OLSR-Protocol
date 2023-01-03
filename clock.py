from threading import RLock
class Clock(object):
    sample = None
    def __new__(ticks):
        if Clock.sample is None:
            Clock.sample = object.__new__(ticks)
            Clock.sample.val = int()
            Clock.sample.lock = RLock()
        return Clock.sample

    def tick(self):
        self.lock.acquire()
        try:
            self.val += 1
        finally:
            self.lock.release()
        return self

    def reset(self):
        self.lock.acquire()
        try:
            self.val = 0
        finally:
            self.lock.release()
        return self

    @property
    def time(self):
        self.lock.acquire()
        try:
            return self.val
        finally:
            self.lock.release()