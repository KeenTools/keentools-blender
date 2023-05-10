# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019  KeenTools

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# ##### END GPL LICENSE BLOCK #####

import time


# --------------
# FPSMeter usage:
# fps = FPSMeter()
# fps.tick()
# print(fps.update_indicator())
class FPSMeter:
    def __init__(self, buf_length=5):
        self.start_time = time.time()
        self.indicator = "None"
        self.counter = 0
        self.buffer = [self.start_time for _ in range(buf_length)]
        self.head = 0
        self.buf_length = len(self.buffer)

    def prev_index(self, ind):
        prev_ind = ind - 1
        if prev_ind < 0:
            prev_ind = self.buf_length
        return prev_ind

    def next_index(self, ind):
        next_ind = ind + 1
        if next_ind >= self.buf_length:
            next_ind = 0
        return next_ind

    def update_indicator(self):
        new_time = self.buffer[self.head]
        old_time = self.buffer[self.next_index(self.head)]
        delta = new_time - old_time
        d = 0.0
        if delta > 0.00001:
            d = (self.buf_length - 1) / delta
        self.indicator = "{0:.2f}".format(d)
        return self.indicator

    def tick(self):
        self.head = self.next_index(self.head)
        self.buffer[self.head] = time.time()
        self.counter += 1
