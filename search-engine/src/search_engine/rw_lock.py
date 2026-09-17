from threading import Condition

class ReadWriteLock:
    def __init__(self) -> None:
        self._condition = Condition()

        self._active_readers = 0
        self._writer_active = False

        self._waiting_readers = 0
        self._waiting_writers = 0

        self._prefer_writer = True

    def read_lock(self) -> None:
        with self._condition:
            self._waiting_readers += 1

            try:
                while (
                    self._writer_active
                    or (
                        self._prefer_writer
                        and self._waiting_writers > 0
                    )
                ):
                    self._condition.wait()

                self._active_readers += 1

            finally:
                self._waiting_readers -= 1

    def read_release(self) -> None:
        with self._condition:
            self._active_readers -= 1

            if self._active_readers == 0:
                self._prefer_writer = True
                self._condition.notify_all()

    def write_lock(self) -> None:
        with self._condition:
            self._waiting_writers += 1

            try:
                while (
                    self._writer_active
                    or self._active_readers > 0
                    or (
                        not self._prefer_writer
                        and self._waiting_readers > 0
                    )
                ):
                    self._condition.wait()

                self._writer_active = True

            finally:
                self._waiting_writers -= 1

    def write_release(self) -> None:
        with self._condition:
            self._writer_active = False

            if self._waiting_readers > 0:
                self._prefer_writer = False
            else:
                self._prefer_writer = True

            self._condition.notify_all()