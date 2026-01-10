import queue
import threading

from rich.live import Live
from rich.progress import Progress, TimeElapsedColumn, TimeRemainingColumn

# 创建打印队列和专用打印线程
print_queue = queue.Queue()
print_done = threading.Event()


def printer_thread():
    while not print_done.is_set() or not print_queue.empty():
        try:
            msg = print_queue.get(timeout=0.1)
            print(f"{msg}")
            print_queue.task_done()
        except queue.Empty:
            continue


def safe_print(message):
    print_queue.put(message)


class ProgressBar:
    def __init__(self) -> None:
        self.bar = Progress(
            *(
                col
                for col in Progress.get_default_columns()
                if not isinstance(col, TimeRemainingColumn)
            ),
            TimeElapsedColumn(),
        )
        self.live_bar = Live(
            self.bar,
            refresh_per_second=1,
            vertical_overflow="crop",
            screen=False,
            transient=False,
        )
