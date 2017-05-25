from __future__ import print_function
from yaml import load


class Config(object):
    def __init__(self):
        with open('config/config.yaml') as data_file:
            c = load(data_file)
            self.remote_url = c['remote']['url'].rstrip('/')
            self.local_url = c['local']['url'].rstrip('/')
            self.local_api_key = c['local']['api_key']
            self.package_storage_path = c['local']['package_storage_path'].rstrip('/').rstrip('\\')
