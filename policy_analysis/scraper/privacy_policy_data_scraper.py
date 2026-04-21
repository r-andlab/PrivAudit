from src.processors import WebsiteProcessor
from src.utils import Logger,WebDriverManager, FileManager
from src.config import Config

def main():
    """Main execution function with separated initial and deep scanning."""
    driver = None
    try:
        driver = WebDriverManager.create_driver()
        processor = WebsiteProcessor(driver)

        FileManager.clear_subfolders()
        
        # Process websites
        with open(Config.FILES['input_file'], 'r') as infile:
            for line in infile:
                website_url = line.strip()
                
                # Perform initial scan
                privacy_urls = processor.process_initial_scan(website_url)
                
                # # Perform deep scan on collected privacy URLs
                if privacy_urls:
                    Logger.log(f"main() -> Found privacy urls: {privacy_urls}")
                    # processor.process_deep_scan(privacy_urls)
                processor.json_manager.write_json(processor.result_dto.to_dict())
                    
    except Exception as e:
        Logger.log(f"main() -> Exception in main(): {str(e)}")
    finally:
        if driver:
            Logger.log("main() -> Closing WebDriver...")
            driver.quit()
            Logger.log("main() -> WebDriver closed.")

if __name__ == "__main__":
    main()