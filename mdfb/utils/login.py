import logging
import platformdirs
import os
import yaml

class Login():
    def __init__(self, handle: str, app_password: str, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self.handle = handle
        self.app_password = app_password
        self.file_path = platformdirs.user_config_path(appname="mdfb")
        self._ensure_exists()
    
    def login(self):
        file = os.path.join(self.file_path, "mdfb.yaml")
        # read current config (safe if file empty)
        with open(file, "r", encoding="utf-8") as stream:
            config = yaml.safe_load(stream) or {}

        # decide whether to write/overwrite
        if "app_password" not in config or self._overwrite():
            config["app_password"] = self.app_password
            # open in "w" to overwrite whole file
            with open(file, "w", encoding="utf-8") as stream:
                yaml.safe_dump(config, stream, sort_keys=False)
            self.logger.info("Wrote app_password to config.")
        else:
            self.logger.info("Kept existing app_password.")
    
    def _ensure_exists(self):
        file = os.path.join(self.file_path, "mdfb.yaml")

        if not os.path.isdir(self.file_path):
            self.logger.debug(f"mdfb config directory does not exist [{self.file_path}], creating...")
            platformdirs.user_config_path(appname="mdfb", ensure_exists=True)
        if os.path.isdir(self.file_path) and not os.path.isfile(file):
            self.logger.debug(f"mdfb config yaml does not exist [{file}], creating...")
            open(file, "a").close()
    
    def _overwrite(self) -> bool:
        answer = input("Do you wish to overwrite the app password? (y/n): ").strip().lower()
        if answer == "y":
            return True
        return False            

            
