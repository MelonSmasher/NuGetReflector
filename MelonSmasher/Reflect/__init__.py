from __future__ import print_function

from lxml import objectify
from time import sleep
from requests import put, get
import os.path
import sys

NAME_SCHEME_META = '{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}'
NAME_SCHEME_DATA = '{http://schemas.microsoft.com/ado/2007/08/dataservices}'
KEY_PROPERTIES = ''.join([NAME_SCHEME_META, 'properties'])
KEY_VERSION = ''.join([NAME_SCHEME_DATA, 'Version'])
KEY_TITLE = 'title'
KEY_CONTENT = 'content'
KEY_SRC = 'src'
KEY_REL = 'rel'
KEY_HREF = 'href'
VALUE_NEXT = 'next'


class Mirror(object):
    def __init__(self, remote_url, local_url, package_storage_path, local_api_key):
        """
        :param remote_url: str
        :param local_url: str
        :param package_storage_path: str
        :param local_api_key: str
        """
        self.remote_api_url = '/'.join([remote_url, 'api/v2'])
        self.remote_packages_url = '/'.join([self.remote_api_url, 'Packages'])
        self.local_api_url = '/'.join([local_url, 'api/v2'])
        self.local_api_upload_url = '/'.join([self.local_api_url, 'package'])
        self.local_packages_url = '/'.join([self.local_api_url, 'Packages'])
        self.package_storage_path = package_storage_path
        self.local_api_key = local_api_key

    @staticmethod
    def _get(url):
        """
        :param url: str
        :return: objectify.ObjectifiedElement | bool
        """
        response = get(url)
        if response.status_code == 200:
            response.objectified = objectify.fromstring(response.content)
            return response
        else:
            return response

    def local_package(self, title, version):
        """
        :param title: str
        :param version: str
        :return: objectify.ObjectifiedElement | bool
        """
        url = ''.join([self.local_packages_url, '(Id=\'', title, '\',Version=\'', version, '\')'])
        return self._get(url)

    def remote_package(self, title, version):
        """
        :param title: str
        :param version: str
        :return: objectify.ObjectifiedElement | bool
        """
        url = ''.join([self.remote_packages_url, '(Id=\'', title, '\',Version=\'', version, '\')'])
        return self._get(url)

    def local_packages(self, url=None):
        """
        :param url: str 
        :return: 
        """
        if url is None: url = self.local_packages_url
        return self._get(url)

    def remote_packages(self, url=None):
        """
        :param url: str
        :return: 
        """
        if url is None: url = self.remote_packages_url
        return self._get(url)

    @staticmethod
    def _download_package(content_url, local_path):
        """
        :param content_url: 
        :param local_path: 
        :return: 
        """
        if not os.path.isfile(local_path):
            count = 0
            sys.stdout.write('Downloading package.')
            sys.stdout.flush()
            # Get the file and stream it to the disk
            r = get(content_url, stream=True)
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        # Count the chunks
                        count = count + 1
                        if count >= 10000:
                            # Write a dot every 10000 chunks
                            sys.stdout.write('.')
                            sys.stdout.flush()
                        # Write to the file when the chunk gets to 1024
                        f.write(chunk)
                        f.flush()
            print('')
            if os.path.isfile(local_path):
                return {'file_exists': True, 'message': 'Package cached!'}
            else:
                return {'file_exists': False, 'message': 'Problem caching package!'}
        else:
            return {'file_exists': True, 'message': 'Package already cached...'}

    def _upload_package(self, local_path, title, version):
        """
        :param local_path: 
        :param title: 
        :param version: 
        :return: 
        """
        local_response = self.local_package(title, version)
        if local_response.status_code == 404:
            print('Uploading package...')

            f = open(local_path, mode='rb')
            files = {'package': ('package', f, 'application/octet-stream')}
            headers = {'X-NuGet-ApiKey': self.local_api_key}
            put_result = put(self.local_api_upload_url, files=files, headers=headers)

            print(''.join(['Response Code: ', str(put_result.status_code)]))
            if put_result.status_code == 200:
                return {'success': True, 'message': 'Package mirrored!', 'response': put_result}
            else:
                return {'success': False, 'message': 'Failed to mirror package!', 'response': put_result}
        elif local_response.status_code == 200:
            return {'success': True, 'message': 'Package already mirrored...'}
        else:
            return {'success': False,
                    'message': ''.join(['Local API returned HTTP code: ', str(local_response.status_code)])}

    def sync_packages(self):
        """        
        :return: 
        """
        done = False
        url = self.remote_packages_url
        while not done:
            # print(''.join(['Requesting packages from: ', url]))
            response = self.remote_packages(url)
            if response.status_code == 200:
                page = response.objectified
                # print(''.join(['Remote API returned: ', str(len(page.entry)), ' packages!']))
                # Whats the size of the entry list
                if len(page.entry) > 0:
                    for package in page.entry:

                        # Extract the info that we need from the entry
                        title = str(package[KEY_TITLE])
                        version = str(package[KEY_PROPERTIES][KEY_VERSION])
                        package_name = '.'.join([title, version])
                        content_url = package[KEY_CONTENT].get(KEY_SRC)
                        local_path = os.path.join(self.package_storage_path, '.'.join([package_name, 'nupkg']))

                        # Begin package sync
                        print('')
                        print(''.join(['########## ', package_name, ' ##########']))
                        dl_status = self._download_package(content_url, local_path)
                        print(dl_status['message'])
                        if dl_status['file_exists']:
                            up_status = self._upload_package(local_path, title, version)
                            if response in up_status:
                                print(''.join(['Response Body: ', up_status['response'].text]))
                            else:
                                print(''.join(['Message: ', up_status['message']]))
                        print('')

                # Get the last link on the page
                link = page.link[0] if 0 > (len(page.link) - 1) else page.link[(len(page.link) - 1)]
                # If the last link is the next link set it's url as the target url for the next iteration
                if link.get(KEY_REL) == VALUE_NEXT:
                    url = link.get(KEY_HREF)
                else:
                    # Break out
                    done = True
            else:
                print('Received bad http code from remote API. Sleeping for 10 and trying again. Response Code: ' + str(
                    response.status_code))
                sleep(10)
        return True
