import logging
import platformdirs
import os
import yaml

from atproto import Client


class FetchFeedDetails():
    def __init__(self, handle: str, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self.handle = handle
        self._existance_check()
        self.client = Client()
        self._login()    

    def _existance_check(self):
        file_path = platformdirs.user_config_path(appname="mdfb")
        file = os.path.join(file_path, "mdfb.yaml")

        if not os.path.isfile(file):
            msg = f"There is no config yaml at: {file}. Need to login using `mdfb login`"
            self.logger.error(msg)
            print(msg)
            raise

    def _fetch_app_password(self) -> str:
        file_path = platformdirs.user_config_path(appname="mdfb")
        file = os.path.join(file_path, "mdfb.yaml")
        config = yaml.safe_load(open(file))
        self.logger.debug(f"Successfully loaded config yaml [{file}]")
        return config["app_password"]
    
    def _login(self):
        try:
            self.client.login(self.handle, self._fetch_app_password())
        except:
            self.logger.error("There is an error logging in. App password may be expired or deleted. Please log in again via `mdfb login`")
            raise
