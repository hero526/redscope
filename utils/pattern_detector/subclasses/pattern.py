from subutils import syscall_info
import logging


class Pattern:
    def __init__(self, pattern):
        self.pattern = pattern
        self.length = len(self.pattern)
        self.start_idx_tid = dict()

    def update_remain(self):
        self.remain = sum([len(indexes) for indexes in self.start_idx_tid.values()])

    def update_correlation(self, correlation):
        self.correlation = correlation

    def update_frequency(self, time):
        if time > 0:
            self.frequency = self.remain / time
        else:
            self.frequency = 0

    # For merge, deprecated now
    def __add__(self, pt_obj):
        self.remain = (self.remain + pt_obj.remain) /2
        self.correlation = (self.correlation + pt_obj.correlation) /2
        self.frequency = (self.frequency + pt_obj.frequency) /2


