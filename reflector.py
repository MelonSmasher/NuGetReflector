#!/usr/bin/env python

from __future__ import print_function
from reflector import Mirror, Config
import argparse


def main():
    parser = argparse.ArgumentParser(description='Synchronize an NuGet mirror from a target repository.')
    parser.add_argument('-d', '--delta', action='store_true',
                        help='Sync the latest packages from the feed url.')
    parser.add_argument('-f', '--full', action='store_true',
                        help='Reconcile the entire local mirror against the remote repo.')
    args = parser.parse_args()

    config = Config()
    mirror = Mirror(
        config.remote_url,
        config.update_feed,
        config.remote_json_api,
        config.local_url,
        config.local_json_api,
        config.package_storage_path,
        config.local_api_key,
        config.dotnet_path,
        config.hash_verify_downloads,
        config.hash_verify_uploaded
    )

    if args.delta:
        print('Starting a delta sync')
        mirror.delta_sync()

    if args.full:
        print('Starting a full sync')
        mirror.sync_packages()


if __name__ == "__main__":
    main()
