import logging
import os
import sys

import platformdirs
import yaml
from atproto import Client


class ConfigManager:
    def __init__(self, handle: str, logger: logging.Logger | None = None):
        self.handle = handle
        self.logger = logger or logging.getLogger(__name__)
        self.file_path = platformdirs.user_config_path(appname="mdfb")
        self.file = os.path.join(self.file_path, "mdfb.yaml")

    def existance_check(self):
        if not os.path.isfile(self.file):
            msg = f"There is no config yaml at: {self.file}. Need to login using `mdfb login`"
            self.logger.error(msg)
            raise ValueError(msg)
        self.logger.info("Config yaml found")

    def get_authed_client(self) -> Client:
        try:
            client = Client()
            client.login(self.handle, self._fetch_app_password())
            return client
        except Exception:
            msg = "There is an error logging in. App password may be expired or deleted. Please log in again via `mdfb login`"
            self.logger.error(msg)
            raise ValueError(msg)

    def write_credentials(self, app_password: str):
        def write_config(file: str, config: dict):
            with open(file, "w", encoding="utf-8") as stream:
                yaml.safe_dump(config, stream, sort_keys=False)

        file = os.path.join(self.file_path, "mdfb.yaml")

        with open(file, encoding="utf-8") as stream:
            config = yaml.safe_load(stream) or {}

        if self.handle not in config:
            # Create handle as top-level key with app_password nested under it
            config[self.handle] = {"app_password": app_password}
            write_config(file, config)
            self.logger.info(f"Wrote app_password to config for handle: {self.handle}.")
        elif "app_password" not in config[self.handle] or self._overwrite():
            config[self.handle]["app_password"] = app_password
            write_config(file, config)
            self.logger.info(f"Wrote app_password to config for handle: {self.handle}.")
        else:
            self.logger.info(f"Kept existing app_password for handle: {self.handle}.")

    def _fetch_app_password(self) -> str:
        file_path = platformdirs.user_config_path(appname="mdfb")
        file = os.path.join(file_path, "mdfb.yaml")
        with open(file) as f:
            config = yaml.safe_load(f)
        self.logger.info(f"Successfully loaded config yaml {file}")

        if self.handle not in config:
            msg = f"There is no entry for handle: {self.handle} in the config yaml, need to use `mdfb login` to add an entry."
            self.logger.error(msg)
            raise ValueError(msg)
        return config[self.handle]["app_password"]

    def _ensure_exists(self):
        if not os.path.isdir(self.file_path):
            self.logger.info(f"mdfb config directory does not exist [{self.file_path}], creating...")
            platformdirs.user_config_path(appname="mdfb", ensure_exists=True)
        if os.path.isdir(self.file_path) and not os.path.isfile(self.file):
            self.logger.info(f"mdfb config yaml does not exist [{self.file}], creating...")
            open(self.file, "a").close()

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

        formatter = logging.Formatter(fmt="[%(asctime)s] %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p")
        handler.setFormatter(formatter)

        logger.addHandler(handler)

        return logger
