import datetime
import logging
import os
import psutil
import time
import threading

def setup_logging(directory: str):
    log_name = datetime.datetime.now().strftime("mdfb_%d%m%Y_%H%M%S.log")
    logging.basicConfig(
        filename=os.path.join(directory, log_name), 
        encoding='utf-8', 
        level=logging.INFO,
        format='[%(asctime)s] %(message)s', 
        datefmt='%m/%d/%Y %I:%M:%S %p',
    )

def _monitor_resources(directory: str, interval: int = 5):
    resource_logger = logging.getLogger("resource")
    resource_logger.setLevel(logging.INFO)
    resource_handler = logging.FileHandler(os.path.join(directory, "resource_monitor.log"))
    resource_formatter = logging.Formatter('%(asctime)s - %(message)s')
    resource_handler.setFormatter(resource_formatter)
    resource_logger.addHandler(resource_handler)
    resource_logger.propagate = False  
    process = psutil.Process()

    while True:
        mem = process.memory_info().rss / (1024 * 1024)  
        cpu = process.cpu_percent(interval=1)  
        resource_logger.info(f"Memory Usage: {mem:.2f} MB, CPU Usage: {cpu:.2f}%")
        time.sleep(interval)

def setup_resource_monitoring(directory: str):
    monitor_thread = threading.Thread(target=_monitor_resources, args=(directory, ), daemon=True)
    monitor_thread.start()