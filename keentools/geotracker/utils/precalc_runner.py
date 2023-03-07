# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022 KeenTools

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

import numpy as np
import threading
import queue
import typing

from ...blender_independent_packages.pykeentools_loader import module as pkt_module


__all__ = ['PrecalcRunner']


class _RedirectingCalculationClient(pkt_module().precalc.CalculationClient):
    def __init__(self, precalc_runner):
        super().__init__()
        self.precalc_runner = precalc_runner

    def on_progress(self, progress, progress_message):
        return self.precalc_runner._on_progress(progress, progress_message)

    def load_image_at(self, frame):
        return self.precalc_runner._load_image_at(frame)


class PrecalcRunner:
    """
    Starts precalc calculation in a separate thread and provides
    methods to get current progress/cancel and supply a requested image
    """
    def __init__(self,
                 file_name,
                 format_width, format_height,
                 frame_from, frame_to,
                 license_manager, use_gpu_if_available):

        self._lock = threading.Lock()
        self._canceled = False
        self._progress = 0.0
        self._progress_message = 'Not started yet'
        self._exception = None
        self._finished = False
        self._frame_to_load_image = None
        self._loaded_frames_queue = queue.SimpleQueue()
        self._execution_thread = threading.Thread(target=self._run_calculate, args=(
            file_name,
            format_width, format_height,
            frame_from, frame_to,
            _RedirectingCalculationClient(self),
            license_manager, use_gpu_if_available))
        self._execution_thread.start()

    def cancel(self) -> None:
        with self._lock:
            self._canceled = True

    def is_finished(self) -> bool:
        with self._lock:
            return self._finished

    def exception(self) -> typing.Optional[Exception]:
        with self._lock:
            return self._exception

    def current_progress(self) -> (float, str):
        with self._lock:
            return self._progress, self._progress_message

    def is_loading_frame_requested(self) -> typing.Optional[int]:
        """
        :return: None if no frame loading requested or a frame number
        """
        with self._lock:
            return self._frame_to_load_image

    def fulfill_loading_request(self, loaded_image: np.array):
        """
        :param loaded_image: loaded image from frame returned by get_loading_frame_request as a byte array
                             shape should match format_width, format_height from constructor
        """
        with self._lock:
            assert(self._frame_to_load_image is not None)
            self._frame_to_load_image = None
        self._loaded_frames_queue.put(loaded_image)

    def _on_progress(self, progress, progress_message):
        with self._lock:
            self._progress = progress
            self._progress_message = progress_message
            return not self._canceled

    def _load_image_at(self, frame):
        with self._lock:
            self._frame_to_load_image = frame
        while True:
            try:
                return self._loaded_frames_queue.get(block=True, timeout=0.2)
            except queue.Empty:
                with self._lock:
                    if self._canceled:
                        return None

    def _run_calculate(self, *args):
        try:
            pkt_module().precalc.calculate_srgb_input(*args)
        except Exception as e:
            with self._lock:
                self._canceled = True
                self._exception = e
        with self._lock:
            self._finished = True


def _run_test():
    import time

    test_w = 100
    test_h = 200
    frame_from = 5
    frame_to = 8
    runner = PrecalcRunner(
        'tmp.precalc', test_w, test_h, frame_from, frame_to, pkt_module().GeoTracker.license_manager(), True)

    while not runner.is_finished():
        print(runner.current_progress())
        maybe_frame = runner.is_loading_frame_requested()
        if maybe_frame is not None:
            loaded_image = np.random.randint(low=0, high=255, size=(test_h, test_w), dtype=np.uint8)
            runner.fulfill_loading_request(loaded_image)
        # runner.cancel() - can be used to cancel at any point
        time.sleep(0.1)
    assert(runner.exception() is None)  # will contain exception if finished with exception


if __name__ == '__main__':
    _run_test()
