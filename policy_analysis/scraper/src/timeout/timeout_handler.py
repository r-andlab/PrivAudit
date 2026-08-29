# Timeout handler
from contextlib import contextmanager
import threading
import _thread
from typing import Generator, Any, Callable
from .timeout_exception import TimeoutException

class TimeoutHandler:

    @staticmethod
    @contextmanager
    def timeout(seconds: int, operation_name: str = "Operation") -> Generator[None, None, None]:
        def raise_timeout():
            thread_id = _thread.get_ident()
            for thread in threading.enumerate():
                if thread.ident == thread_id:
                    _thread.interrupt_main()
                    return

        timer = threading.Timer(seconds, raise_timeout)
        timer.start()
        try:
            yield
        except KeyboardInterrupt:
            raise TimeoutException(f"{operation_name} timed out after {seconds} seconds")
        finally:
            timer.cancel()

    @staticmethod
    def with_timeout(seconds: int, operation_name: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                with TimeoutHandler.timeout(seconds, operation_name):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
