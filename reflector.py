from __future__ import print_function
from MelonSmasher.Helpers import Config
from MelonSmasher.Reflect import Mirror


def main():
    config = Config()
    mirror = Mirror(config.remote_url, config.local_url, config.package_storage_path, config.local_api_key)
    mirror.sync_packages()


if __name__ == "__main__":
    main()
