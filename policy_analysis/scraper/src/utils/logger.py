# Logger
from datetime import datetime

class Logger:

    @staticmethod
    def log(message: str) -> None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'[{timestamp}] {message}')
