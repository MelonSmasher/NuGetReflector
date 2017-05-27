from __future__ import print_function
from yaml import load
from os.path import isfile


class Config(object):
    def __init__(self):
        with open('config/config.yaml') as data_file:
            c = load(data_file)
            self.remote_url = c['remote']['url'].rstrip('/')
            self.remote_json_api = c['remote']['json_api']
            self.local_url = c['local']['url'].rstrip('/')
            self.local_json_api = c['local']['json_api']
            self.local_api_key = c['local']['api_key']
            self.package_storage_path = c['local']['package_storage_path'].rstrip('/').rstrip('\\')
            self.hash_verify_downloads = c['hash']['verify_downloads']
            self.hash_verify_uploaded = c['hash']['verify_uploaded']
            self.hash_verify_cache = c['hash']['verify_cache']
            self.dotnet_path = c['local']['dotnet_path']
            if not self.dotnet_path or not isfile(self.dotnet_path):
                raise EnvironmentError('DotNot CLI executable is not configured or the path specified does not exist!')
