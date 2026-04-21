from src.utils import JsonManager
from src.config import Config

class BaseScraper:
    def __init__(self, driver):
        self.driver = driver
        self.json_manager = JsonManager(Config.FILES['output_file'])