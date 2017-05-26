from __future__ import print_function

from lxml import objectify
from time import sleep
from requests import put, get
import os.path
import sys
import hashlib
import base64

NAME_SCHEME_META = '{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}'
NAME_SCHEME_DATA = '{http://schemas.microsoft.com/ado/2007/08/dataservices}'
KEY_PROPERTIES = ''.join([NAME_SCHEME_META, 'properties'])
KEY_VERSION = ''.join([NAME_SCHEME_DATA, 'Version'])
KEY_HASH = ''.join([NAME_SCHEME_DATA, 'PackageHash'])
KEY_ALGORITHM = ''.join([NAME_SCHEME_DATA, 'PackageHashAlgorithm'])
KEY_TITLE = 'title'
KEY_CONTENT = 'content'
KEY_SRC = 'src'
KEY_REL = 'rel'
KEY_HREF = 'href'
VALUE_NEXT = 'next'
XML_SHIMS = [('&nbsp;', u'\u00a0'), ('&acirc;', u'\u00e2'), ('&amp;', u'\u0026')]


class Mirror(object):
    def __init__(self,
                 remote_url,
                 local_url,
                 package_storage_path,
                 local_api_key,
                 verify_downloads=True,
                 verify_uploaded=True,
                 verify_cache=False
                 ):
        """
        :param remote_url: 
        :param local_url: 
        :param package_storage_path: 
        :param local_api_key: 
        :param verify_downloads: 
        :param verify_cache: 
        """
        self.remote_api_url = '/'.join([remote_url, 'api/v2'])
        self.remote_packages_url = '/'.join([self.remote_api_url, 'Packages'])
        self.local_api_url = '/'.join([local_url, 'api/v2'])
        self.local_api_upload_url = '/'.join([self.local_api_url, 'package'])
        self.local_packages_url = '/'.join([self.local_api_url, 'Packages'])
        self.package_storage_path = package_storage_path
        self.local_api_key = local_api_key
        self.verify_downloads = verify_downloads
        self.verify_uploaded = verify_uploaded
        self.verify_cache = verify_cache

    @staticmethod
    def hash_bytestr_iter(bytesiter, hasher, ashexstr=False):
        for block in bytesiter:
            hasher.update(block)
        return hasher.hexdigest() if ashexstr else hasher.digest()

    @staticmethod
    def file_as_blockiter(file, blocksize=65536):
        with file:
            block = file.read(blocksize)
            while len(block) > 0:
                yield block
                block = file.read(blocksize)

    def sha512sum(self, file_path, blocksize=65536):
        """
        :param file_path: 
        :param blocksize: 
        :return: 
        """
        return base64.encodestring(
            self.hash_bytestr_iter(self.file_as_blockiter(open(file_path, 'rb')), hashlib.sha512(), False)).replace(
            "\n", '')

    def sha256sum(self, file_path, blocksize=65536):
        """
        :param file_path: 
        :param blocksize: 
        :return: 
        """
        return base64.encodestring(
            self.hash_bytestr_iter(self.file_as_blockiter(open(file_path, 'rb')), hashlib.sha256(), False)).replace(
            "\n", '')

    @staticmethod
    def hashes_match(hash_1, hash_2):
        """
        :param hash_1: 
        :param hash_2: 
        :return: 
        """
        if str(hash_1) == str(hash_2):
            print(' Pass!')
            return True
        else:
            print(' Fail!')
            print('Hash 1: ' + hash_1)
            print('Hash 2: ' + hash_2)
            return False

    def verify_package_hash(self, file_path, target_hash, message='Verifying package hash...'):
        """
        :param file_path: 
        :param target_hash: 
        :param message: 
        :return: 
        """
        sys.stdout.write(message)
        sys.stdout.flush()
        local_hash = self.sha512sum(file_path)
        return self.hashes_match(local_hash, target_hash)

    @staticmethod
    def _get(url):
        """
        :param url: str
        :return: objectify.ObjectifiedElement | bool
        """
        response = get(url)
        if response.status_code == 200:
            xml = response.content
            # pre process XML to remove bogus xml
            for before, after in XML_SHIMS:
                xml = xml.replace(before, after.encode('utf8'))
            response.objectified = objectify.fromstring(xml)
            return response
        else:
            return response

    def local_package(self, title, version):
        """
        :param title: 
        :param version: 
        :return: 
        """
        url = ''.join([self.local_packages_url, '(Id=\'', title, '\',Version=\'', version, '\')'])
        return self._get(url)

    def remote_package(self, title, version):
        """
        :param title: 
        :param version: 
        :return: 
        """
        url = ''.join([self.remote_packages_url, '(Id=\'', title, '\',Version=\'', version, '\')'])
        return self._get(url)

    def local_packages(self, url=None):
        """
        :param url: 
        :return: 
        """
        if url is None: url = self.local_packages_url
        return self._get(url)

    def remote_packages(self, url=None):
        """
        :param url: 
        :return: 
        """
        if url is None: url = self.remote_packages_url
        return self._get(url)

    def _download_package(self, content_url, local_path, remote_hash=None, reties=0, force=False):
        """
        :param content_url: 
        :param local_path: 
        :param remote_hash: 
        :param reties: 
        :param force: 
        :return: 
        """
        if not os.path.isfile(local_path) or force:
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
            if not remote_hash is None:
                hash_verified = self.verify_package_hash(local_path, remote_hash)
                if not hash_verified and reties < 3:
                    # Retry loop
                    reties += 1
                    print('Hashes do not match retrying download...')
                    return self._download_package(content_url, local_path, remote_hash, reties, True)
                elif not hash_verified and reties >= 3:
                    # Reached max retries
                    print('Retried to download the package 3 times, moving on... :-(')
                    return False
                else:
                    # Hash verified
                    return True
            else:
                # Skipping hash verification
                return True
        else:
            # File did not exists after DL
            return False

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
            print(''.join(['Upload response Code: ', str(put_result.status_code)]))
            upload_status = {
                'response': put_result,
                'mirrored': True,
                'uploaded': True
            }
        elif local_response.status_code == 200:
            print('Package already mirrored...')
            upload_status = {
                'response': local_response,
                'mirrored': True,
                'uploaded': False,
                'server_hash': local_response.objectified[KEY_PROPERTIES][KEY_HASH]
            }
        else:
            return {
                'response': local_response,
                'mirrored': False,
                'uploaded': False,
                'server_hash': False
            }

        if not 'server_hash' in upload_status and self.verify_uploaded:
            r = self.local_package(title, version)
            if r.status_code == 200:
                upload_status['server_hash'] = r.objectified[KEY_PROPERTIES][KEY_HASH]
            else:
                upload_status['server_hash'] = False

        return upload_status

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
                        remote_hash = str(package[KEY_PROPERTIES][KEY_HASH]) if self.verify_downloads else None
                        dl_status = False

                        # Begin package sync
                        print('')
                        print(''.join(['########## ', package_name, ' ##########']))

                        if not os.path.isfile(local_path):
                            dl_status = self._download_package(content_url, local_path, remote_hash)
                        else:
                            if self.verify_cache:
                                if not self.verify_package_hash(local_path, remote_hash):
                                    dl_status = self._download_package(content_url, remote_hash, True)
                                else:
                                    dl_status = True

                        if dl_status:
                            up_status = self._upload_package(local_path, title, version)
                            if up_status['mirrored']:
                                if self.verify_uploaded and up_status['server_hash']:
                                    sys.stdout.write('Verifying server hashes...')
                                    sys.stdout.flush()
                                    server_hashes_verified = self.hashes_match(remote_hash, up_status['server_hash'])
                                    if self.verify_cache and up_status['server_hash']:
                                        local_hashes_verified = self.verify_package_hash(local_path,
                                                                                         up_status['server_hash'],
                                                                                         'Verifying cache hash against mirror...')

                                if up_status['uploaded']:
                                    print('Package uploaded!')
                                    print(''.join(['Response Body: ', up_status['response'].text]))

                                if not up_status['uploaded']:
                                    print('Package already uploaded!')
                            else:
                                print(''.join(['Response Body: ', up_status['response'].text]))
                                print('Package not mirrored!')

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
