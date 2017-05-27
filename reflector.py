from __future__ import print_function
from reflector import Mirror, Config


def main():
    config = Config()
    mirror = Mirror(
        config.remote_url,
        config.remote_json_api,
        config.local_url,
        config.local_json_api,
        config.package_storage_path,
        config.local_api_key,
        config.dotnet_path,
        config.hash_verify_downloads,
        config.hash_verify_uploaded,
        config.hash_verify_cache,
    )
    mirror.sync_packages()


if __name__ == "__main__":
    main()
