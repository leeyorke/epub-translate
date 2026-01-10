import queue
import threading
import time
from functools import wraps

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
from rich.console import Console
from rich.live import Live
from rich.progress import Progress, TimeElapsedColumn, TimeRemainingColumn

from .config import get_config
from .settings import (
    OUTPUT_MAX_TOKENS,
    TIMEOUT,
)

CONFIG = get_config()

# 创建打印队列和专用打印线程
print_queue = queue.Queue()
print_done = threading.Event()


def printer_thread():
    console = Console()
    while not print_done.is_set() or not print_queue.empty():
        try:
            msg = print_queue.get(timeout=0.1)
            console.print(f"{msg}")
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


def retry(max_retries=5, base_delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None

            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except (RateLimitError, APITimeoutError, APIConnectionError) as e:
                    last_error = e
                    safe_print(
                        f"(>_<): retryable error {type(e).__name__},\n"
                        f"(>_<): retry {attempt}/{max_retries}"
                    )
                    time.sleep(base_delay * (2 ** (attempt - 1)))

                except Exception:
                    raise
            raise last_error  # type: ignore

        return wrapper

    return decorator


@retry(max_retries=5, base_delay=2)
def call_ai(text: str, prompt: str):
    client = OpenAI(base_url=CONFIG.base_url, api_key=CONFIG.api_key)
    response = client.chat.completions.create(
        model=CONFIG.model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"{text}"},
        ],
        stream=False,
        temperature=0.0,
        max_tokens=OUTPUT_MAX_TOKENS,
        timeout=TIMEOUT,
    )

    content = (
        response
        and response.choices
        and response.choices[0].message
        and response.choices[0].message.content
    )

    if not content:
        raise ValueError("(>_<): Client response is empty!")
    return content
