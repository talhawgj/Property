import asyncio
import logging
import shutil
import glob
import os
from typing import List
from fastapi.concurrency import asynccontextmanager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

class WebDriverPool:
    _instance = None
    
    def __init__(self, pool_size: int = 4, max_uses: int = 50):
        self.pool_size = pool_size
        self.max_uses = max_uses 
        self.drivers: asyncio.Queue = asyncio.Queue(maxsize=pool_size)
        self.usage_counts = {} 

    @classmethod
    async def initialize(cls, pool_size: int = 4):
        cls._cleanup_stale_temp_files()

        if cls._instance is None:
            cls._instance = cls(pool_size)
            await cls._instance._start_drivers()
        return cls._instance

    @staticmethod
    def _cleanup_stale_temp_files():
        """Aggressively remove old chromium temp files from /tmp to free space."""
        try:
            logger.info("Cleaning up stale Chromium temp files...")
            files = glob.glob("/tmp/.org.chromium.Chromium.*")
            for f in files:
                try:
                    if os.path.isdir(f):
                        shutil.rmtree(f)
                    else:
                        os.remove(f)
                except Exception as e:
                    logger.warning(f"Could not delete stale file {f}: {e}")
        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")

    @classmethod
    async def shutdown(cls):
        if cls._instance:
            await cls._instance._close_drivers()
            cls._instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            raise RuntimeError("WebDriverPool not initialized.")
        return cls._instance

    def _create_driver_options(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage") 
        options.add_argument("--disk-cache-size=1") # Limit cache to 1 byte (effectively disabled)
        options.add_argument("--media-cache-size=1")
        
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=800,600")
        options.add_argument("--disable-extensions")
        options.add_argument("--dns-prefetch-disable")
        options.page_load_strategy = 'eager'
        return options

    async def _create_new_driver(self):
        """Helper to create a single driver instance."""
        options = self._create_driver_options()
        driver_path = ChromeDriverManager().install()
        service = Service(driver_path)

        return await asyncio.to_thread(webdriver.Chrome, service=service, options=options)

    async def _start_drivers(self):
        logger.info(f"Initializing WebDriverPool with {self.pool_size} instances...")
        
        for i in range(self.pool_size):
            try:
                driver = await self._create_new_driver()
                self.usage_counts[id(driver)] = 0
                await self.drivers.put(driver)
            except Exception as e:
                logger.error(f"Failed to create driver {i}: {e}")
        
        logger.info(f"WebDriverPool ready with {self.drivers.qsize()} drivers.")

    async def _close_drivers(self):
        logger.info("Shutting down WebDriverPool...")
        while not self.drivers.empty():
            try:
                driver = await self.drivers.get()
                await asyncio.to_thread(driver.quit)
            except Exception:
                pass
    @asynccontextmanager
    async def acquire(self):
        driver = await self.drivers.get()
        driver_id = id(driver)
        
        try:
            yield driver
            self.usage_counts[driver_id] += 1
        finally:
            if self.usage_counts.get(driver_id, 0) >= self.max_uses:
                logger.info(f"Recycling driver {driver_id} after {self.max_uses} uses.")
                try:
                    await asyncio.to_thread(driver.quit) # Cleanly deletes /tmp folder
                except Exception:
                    pass
                try:
                    new_driver = await self._create_new_driver()
                    self.usage_counts[id(new_driver)] = 0
                    await self.drivers.put(new_driver)
                except Exception as e:
                    logger.error(f"Failed to replace recycled driver: {e}")
            else:
                try:
                    await asyncio.to_thread(driver.get, "about:blank")
                    await self.drivers.put(driver)
                except Exception:
                    await self._create_new_driver()