from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import logging

logger = logging.getLogger(__name__)
chrome_driver = None

async def init_chrome_driver():
    global chrome_driver
    if chrome_driver is None:
        logger.info("Starting ChromeDriver...")
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=800,800")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-features=VizDisplayCompositor")
        
        try:
            # Try to use webdriver_manager to automatically download ChromeDriver
            service = Service(ChromeDriverManager().install())
            chrome_driver = webdriver.Chrome(service=service, options=options)
            logger.info("ChromeDriver started successfully with webdriver_manager")
        except Exception as e:
            logger.warning(f"webdriver_manager failed: {e}")
            try:
                # Fallback to system ChromeDriver
                chrome_driver = webdriver.Chrome(options=options)
                logger.info("ChromeDriver started successfully with system driver")
            except Exception as e2:
                logger.error(f"Failed to start ChromeDriver: {e2}")
                logger.error("Please ensure Chrome is installed and ChromeDriver is available in PATH")
                logger.error("You can install ChromeDriver manually or use: pip install webdriver-manager")
                raise RuntimeError(f"ChromeDriver initialization failed: {e2}")
    return chrome_driver

def get_chrome_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=800,800")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-features=VizDisplayCompositor")
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        logger.info("ChromeDriver started successfully with webdriver_manager")
        return driver
    except Exception as e:
        logger.warning(f"webdriver_manager failed: {e}")
        try:
            driver = webdriver.Chrome(options=options)
            logger.info("ChromeDriver started successfully with system driver")
            return driver
        except Exception as e2:
            logger.error(f"Failed to start ChromeDriver: {e2}")
            raise RuntimeError(f"ChromeDriver initialization failed: {e2}")

def shutdown_chrome_driver():
    global chrome_driver
    if chrome_driver:
        logger.info("Shutting down ChromeDriver...")
        chrome_driver.quit()
        chrome_driver = None
