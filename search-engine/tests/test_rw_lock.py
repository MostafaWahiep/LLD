import sys
from pathlib import Path


PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))
    
from search_engine.rw_lock import ReadWriteLock

import unittest
import time
from threading import Event, Thread, Lock, Barrier

class TestReadWriteLock(unittest.TestCase):
    def setUp(self):
        self.rw_lock = ReadWriteLock()

    def test_write_waits_for_reads(self):
        read_acquired = Event()
        release_read = Event()
        write_acquired = Event()

        def read():
            self.rw_lock.read_lock()
            read_acquired.set()

            release_read.wait()
            self.rw_lock.read_release()

        def write():
            self.rw_lock.write_lock()
            write_acquired.set()
            self.rw_lock.write_release()

        read_thread = Thread(target=read)
        write_thread = Thread(target=write)

        read_thread.start()
        self.assertTrue(read_acquired.wait(timeout=1))
        write_thread.start()
        self.assertFalse(write_acquired.wait(timeout=0.05))

        release_read.set()
        self.assertTrue(write_acquired.wait(timeout=1))

        read_thread.join(timeout=1)
        write_thread.join(timeout=1)

        self.assertFalse(read_thread.is_alive())
        self.assertFalse(write_thread.is_alive())

    def test_multiple_reads(self):
        read_acquired = Event()
        release_read = Event()
        read_count = 0

        def read():
            nonlocal read_count
            self.rw_lock.read_lock()
            read_count += 1
            if read_count == 3:
                read_acquired.set()

            release_read.wait()
            self.rw_lock.read_release()

        read_thread1 = Thread(target=read)
        read_thread2 = Thread(target=read)
        read_thread3 = Thread(target=read)

        read_thread1.start()
        read_thread2.start()
        read_thread3.start()

        self.assertTrue(read_acquired.wait(timeout=1))

        release_read.set()

        read_thread1.join(timeout=1)
        read_thread2.join(timeout=1)
        read_thread3.join(timeout=1)

        self.assertFalse(read_thread1.is_alive())
        self.assertFalse(read_thread2.is_alive())
        self.assertFalse(read_thread3.is_alive())
        self.assertEqual(self.rw_lock._active_readers, 0)

    def test_multiple_read_wait_for_write(self):
        write_acquired = Event()
        release_write = Event()
        read_acquired = Event()
        self.read_count = 0
        self.read_counter_lock = Lock()

        def write():
            self.rw_lock.write_lock()
            write_acquired.set()

            release_write.wait()
            self.rw_lock.write_release()

        def read():
            self.rw_lock.read_lock()

            with self.read_counter_lock:
                self.read_count += 1
                if self.read_count == 2:
                    read_acquired.set()

            self.rw_lock.read_release()

        write_thread = Thread(target=write)
        read_thread1 = Thread(target=read)
        read_thread2 = Thread(target=read)


        write_thread.start()
        self.assertTrue(write_acquired.wait(timeout=1))
        read_thread1.start()
        read_thread2.start()
        self.assertFalse(read_acquired.wait(timeout=0.05))

        release_write.set()
        self.assertTrue(read_acquired.wait(timeout=1))

        write_thread.join(timeout=1)
        read_thread1.join(timeout=1)
        read_thread2.join(timeout=1)

        self.assertFalse(write_thread.is_alive())
        self.assertFalse(read_thread1.is_alive())
        self.assertFalse(read_thread2.is_alive())
        self.assertEqual(self.rw_lock._active_readers, 0)

    def test_writer_does_not_starve(self):
        read1_acquired = Event()
        release_read1 = Event()

        write_acquired = Event()
        write_released = Event()

        read2_acquired = Event()

        def read1():
            self.rw_lock.read_lock()
            read1_acquired.set()

            release_read1.wait()

            self.rw_lock.read_release()

        def write():
            self.rw_lock.write_lock()
            write_acquired.set()

            self.rw_lock.write_release()
            write_released.set()

        def read2():
            self.rw_lock.read_lock()
            read2_acquired.set()

            self.rw_lock.read_release()

        read_thread1 = Thread(target=read1)
        write_thread = Thread(target=write)
        read_thread2 = Thread(target=read2)

        read_thread1.start()
        self.assertTrue(read1_acquired.wait(timeout=1))

        write_thread.start()
        self.assertFalse(write_acquired.wait(timeout=0.05))

        read_thread2.start()
        self.assertFalse(read2_acquired.wait(timeout=0.05))

        release_read1.set()

        self.assertTrue(write_acquired.wait(timeout=1))
        self.assertTrue(write_released.wait(timeout=1))

        self.assertTrue(read2_acquired.wait(timeout=1))

        read_thread1.join(timeout=1)
        write_thread.join(timeout=1)
        read_thread2.join(timeout=1)

        self.assertFalse(read_thread1.is_alive())
        self.assertFalse(write_thread.is_alive())
        self.assertFalse(read_thread2.is_alive())
        self.assertEqual(self.rw_lock._active_readers, 0)

    def test_readers_get_chance_between_writers(self):
        order = []
        order_lock = Lock()

        r1_acquired = Event()
        release_r1 = Event()

        writers_ready = Barrier(3)  # W1, W2, main thread
        writer_acquired = Event()
        release_first_writer = Event()

        r2_acquired = Event()
        release_r2 = Event()

        def record(name):
            with order_lock:
                order.append(name)

        def reader1():
            self.rw_lock.read_lock()
            record("R1")
            r1_acquired.set()

            release_r1.wait()

            self.rw_lock.read_release()

        def writer(name):
            # Make sure both writers are ready to contend
            writers_ready.wait()

            self.rw_lock.write_lock()
            record(name)

            # Only the first writer blocks here.
            # By the time the second gets the lock, this event
            # will already be set.
            if not writer_acquired.is_set():
                writer_acquired.set()
                release_first_writer.wait()

            self.rw_lock.write_release()

        def reader2():
            self.rw_lock.read_lock()
            record("R2")
            r2_acquired.set()

            release_r2.wait()

            self.rw_lock.read_release()

        r1 = Thread(target=reader1)
        w1 = Thread(target=writer, args=("W1",))
        w2 = Thread(target=writer, args=("W2",))
        r2 = Thread(target=reader2)

        # R1 acquires first.
        r1.start()
        self.assertTrue(r1_acquired.wait(timeout=1))

        # Both writers become ready while R1 is holding the read lock.
        w1.start()
        w2.start()
        writers_ready.wait(timeout=1)

        # R2 arrives while writers are waiting.
        r2.start()

        # R2 should not be able to skip the waiting writers.
        self.assertFalse(r2_acquired.wait(timeout=0.05))

        # Let R1 finish.
        release_r1.set()

        # Exactly one of W1/W2 should acquire next.
        self.assertTrue(writer_acquired.wait(timeout=1))

        # R2 still cannot enter while that writer is active.
        self.assertFalse(r2_acquired.is_set())

        # Let the first writer finish.
        release_first_writer.set()

        # Now R2 should get a turn before the other writer.
        self.assertTrue(r2_acquired.wait(timeout=1))

        with order_lock:
            self.assertEqual(order[0], "R1")
            self.assertIn(order[1], ("W1", "W2"))
            self.assertEqual(order[2], "R2")

        # Let R2 finish so the remaining writer can proceed.
        release_r2.set()

        for thread in (r1, w1, w2, r2):
            thread.join(timeout=1)

        for thread in (r1, w1, w2, r2):
            self.assertFalse(thread.is_alive())

        # Final valid orders:
        #
        # R1, W1, R2, W2
        # OR
        # R1, W2, R2, W1
        self.assertEqual(order[0], "R1")
        self.assertEqual(order[2], "R2")
        self.assertEqual({order[1], order[3]}, {"W1", "W2"})
        
if __name__ == "__main__":
    unittest.main()