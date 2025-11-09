import logging
import platformdirs
import os
import yaml
import sys

class Login():
    def __init__(self, handle: str, app_password: str):
        self.logger = self._setup_logger()
        self.handle = handle
        self.app_password = app_password
        self.file_path = platformdirs.user_config_path(appname="mdfb")
        self._ensure_exists()
    
    def login(self):
        def write_config(file: str, config: dict):
            with open(file, "w", encoding="utf-8") as stream:
                yaml.safe_dump(config, stream, sort_keys=False)

        file = os.path.join(self.file_path, "mdfb.yaml")

        with open(file, "r", encoding="utf-8") as stream:
            config = yaml.safe_load(stream) or {}

        if self.handle not in config:
            # Create handle as top-level key with app_password nested under it
            config[self.handle] = {
                "app_password": self.app_password
            }
            write_config(file, config)
            self.logger.info(f"Wrote app_password to config for handle: {self.handle}.")
        else:
            if "app_password" not in config[self.handle] or self._overwrite():
                config[self.handle]["app_password"] = self.app_password
                write_config(file, config)
                self.logger.info(f"Wrote app_password to config for handle: {self.handle}.")
            else:
                self.logger.info(f"Kept existing app_password for handle: {self.handle}.")    

    def _ensure_exists(self):
        file = os.path.join(self.file_path, "mdfb.yaml")

        if not os.path.isdir(self.file_path):
            self.logger.info(f"mdfb config directory does not exist [{self.file_path}], creating...")
            platformdirs.user_config_path(appname="mdfb", ensure_exists=True)
        if os.path.isdir(self.file_path) and not os.path.isfile(file):
            self.logger.info(f"mdfb config yaml does not exist [{file}], creating...")
            open(file, "a").close()
    
    def _overwrite(self) -> bool:
        answer = input("Do you wish to overwrite the app password? (y/n): ").strip().lower()
        if answer == "y":
            return True
        return False        

    def _setup_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        logger.propagate = False
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            fmt='[%(asctime)s] %(message)s',
            datefmt='%m/%d/%Y %I:%M:%S %p'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        
        return logger