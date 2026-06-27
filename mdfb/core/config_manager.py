import platformdirs
import os
import yaml
import logging

class ConfigManager:

    def __init__(self, handle: str, logger: logging.Logger | None = None):
        self.handle = handle
        self.logger = logger or logging.getLogger(__name__)

    def _existance_check(self):
        file_path = platformdirs.user_config_path(appname="mdfb")
        file = os.path.join(file_path, "mdfb.yaml")

        if not os.path.isfile(file):
            msg = f"There is no config yaml at: {file}. Need to login using `mdfb login`"
            self.logger.error(msg)
            raise ValueError(msg)

        self.logger.info("Config yaml found")

    def _fetch_app_password(self) -> str:
        file_path = platformdirs.user_config_path(appname="mdfb")
        file = os.path.join(file_path, "mdfb.yaml")
        config = yaml.safe_load(open(file))
        self.logger.info(f"Successfully loaded config yaml {file}")

        if self.handle not in config:
            msg = f"There is no entry for handle: {self.handle} in the config yaml, need to use `mdfb login` to add an entry."
            self.logger.error(msg)
            raise ValueError(msg)
        return config[self.handle]["app_password"]