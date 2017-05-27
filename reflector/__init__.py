from __future__ import print_function

import os.path
from subprocess import call
from time import sleep
from yaml import load
from reflector.util import *

NAME_SCHEME_META = '{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}'
NAME_SCHEME_DATA = '{http://schemas.microsoft.com/ado/2007/08/dataservices}'
KEY_PROPERTIES = ''.join([NAME_SCHEME_META, 'properties'])
KEY_VERSION = ''.join([NAME_SCHEME_DATA, 'Version'])
KEY_HASH = ''.join([NAME_SCHEME_DATA, 'PackageHash'])
KEY_ALGORITHM = ''.join([NAME_SCHEME_DATA, 'PackageHashAlgorithm'])
KEY_TITLE = 'Id'
KEY_CONTENT = 'content'
KEY_SRC = 'src'
KEY_REL = 'rel'
KEY_HREF = 'href'
VALUE_NEXT = {'xml': 'next', 'json': '__next'}


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
            if not self.dotnet_path or not os.path.isfile(self.dotnet_path):
                raise EnvironmentError('DotNot CLI executable is not configured or the path specified does not exist!')


class Mirror(object):
    def __init__(self,
                 remote_url,
                 remote_json_api,
                 local_url,
                 local_json_api,
                 package_storage_path,
                 local_api_key,
                 dotnet_path,
                 verify_downloads=True,
                 verify_uploaded=True,
                 verify_cache=False
                 ):
        """
        :param remote_url: 
        :param remote_json_api: 
        :param local_url: 
        :param local_json_api: 
        :param package_storage_path: 
        :param local_api_key: 
        :param dotnet_path: 
        :param verify_downloads: 
        :param verify_uploaded: 
        :param verify_cache: 
        """
        self.remote_api_url = '/'.join([remote_url, 'api/v2'])
        self.remote_json_api = remote_json_api
        self.remote_packages_url = '/'.join([self.remote_api_url, 'Packages'])
        self.local_api_url = '/'.join([local_url, 'api/v2'])
        self.local_json_api = local_json_api
        self.local_api_upload_url = '/'.join([self.local_api_url, 'package'])
        self.local_packages_url = '/'.join([self.local_api_url, 'Packages'])
        self.package_storage_path = package_storage_path
        self.local_api_key = local_api_key
        self.dotnet_path = dotnet_path
        self.verify_downloads = verify_downloads
        self.verify_uploaded = verify_uploaded
        self.verify_cache = verify_cache

    def __download_package(self, content_url, local_path, remote_hash=None, remote_hash_method=None, reties=0,
                           force=False):
        """
        :param content_url: 
        :param local_path: 
        :param remote_hash: 
        :param reties: 
        :param force: 
        :param remote_hash_method: 
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
            if remote_hash is not None:
                hash_verified = verify_hash(local_path, remote_hash, hash_method=remote_hash_method)
                if not hash_verified and reties < 3:
                    # Retry loop
                    reties += 1
                    print('Hashes do not match retrying download...')
                    return self.__download_package(
                        content_url,
                        local_path,
                        remote_hash=remote_hash,
                        remote_hash_method=remote_hash_method,
                        reties=reties,
                        force=True
                    )
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

    def __upload_package(self, local_path, package_id, version, force=False):
        """
        :param local_path: 
        :param package_id: 
        :param version: 
        :param force: 
        :return: 
        """
        use_local_json = self.local_json_api
        local_response = pull_package(package_id, version, self.local_packages_url, use_local_json)
        if local_response and (local_response.status_code == 404 or force):
            print('Uploading package...')
            cmd = ' '.join([self.dotnet_path, 'nuget', 'push', local_path, '-s', self.local_api_upload_url, '-k',
                            self.local_api_key])
            return_code = call(cmd, shell=True)
            upload_status = {
                'response': return_code,
                'mirrored': True,
                'uploaded': True
            }
        elif local_response and local_response.status_code == 200:
            print('Package already mirrored...')

            if use_local_json:
                data = local_response.json()['d']
                server_hash = data['PackageHash']
                hash_method = data['PackageHashAlgorithm']
            else:
                server_hash = local_response.objectified[KEY_PROPERTIES][KEY_HASH]
                hash_method = local_response.objectified[KEY_PROPERTIES][KEY_ALGORITHM]

            upload_status = {
                'response': local_response,
                'mirrored': True,
                'uploaded': False,
                'server_hash': server_hash,
                'server_hash_method': hash_method
            }
        else:
            return {
                'response': local_response,
                'mirrored': False,
                'uploaded': False,
                'server_hash': False,
                'server_hash_method': False
            }

        if 'server_hash' not in upload_status and self.verify_uploaded:
            r = pull_package(package_id, version, self.local_packages_url, use_local_json)
            if r.status_code == 200:

                if use_local_json:
                    data = r.json()['d']
                    server_hash = data['PackageHash']
                    hash_method = data['PackageHashAlgorithm']
                else:
                    server_hash = r.objectified[KEY_PROPERTIES][KEY_HASH]
                    hash_method = r.objectified[KEY_PROPERTIES][KEY_ALGORITHM]

                upload_status['server_hash'] = server_hash
                upload_status['server_hash_method'] = hash_method
            else:
                upload_status['server_hash'] = False
                upload_status['server_hash_method'] = False

        return upload_status

    def sync_and_verify_package(self, package, retry=0):
        """
        :param package: 
        :param retry: 
        :return: 
        """
        # Extract the info that we need from the package entry
        # Dict keys vary depending if the page was pulled in XML or JSON
        use_remote_json = self.remote_json_api
        package_id = str(package[KEY_TITLE])
        version = str(package['Version']) if use_remote_json else str(package[KEY_PROPERTIES][KEY_VERSION])
        metadata = package['__metadata'] if use_remote_json else {}
        package_name = '.'.join([package_id, version])
        content_url = metadata['media_src'] if use_remote_json else package[KEY_CONTENT].get(KEY_SRC)
        local_path = os.path.join(self.package_storage_path, '.'.join([package_name, 'nupkg']))
        if use_remote_json:
            remote_hash = str(package['PackageHash']) if self.verify_downloads else None
            remote_hash_method = str(package['PackageHashAlgorithm']).lower() if self.verify_downloads else None
        else:
            remote_hash = str(package[KEY_PROPERTIES][KEY_HASH]) if self.verify_downloads else None
            remote_hash_method = str(package[KEY_PROPERTIES][KEY_ALGORITHM]).lower() if self.verify_downloads else None
        dl_status = False
        # up_status = {}

        # Begin package sync
        print('')
        print(''.join(['########## ', package_name, ' ##########']))

        if not os.path.isfile(local_path):
            dl_status = self.__download_package(
                content_url,
                local_path,
                remote_hash=remote_hash,
                remote_hash_method=remote_hash_method
            )
        else:
            if self.verify_cache:
                if not verify_hash(local_path, remote_hash, hash_method=remote_hash_method):
                    os.remove(local_path)
                    dl_status = self.__download_package(
                        content_url,
                        local_path,
                        remote_hash=remote_hash,
                        remote_hash_method=remote_hash_method,
                        force=True
                    )
                else:
                    dl_status = True

        if dl_status:
            up_status = self.__upload_package(local_path, package_id, version)
            if up_status['mirrored']:
                if self.verify_uploaded and up_status['server_hash']:
                    sys.stdout.write('Verifying server hashes...')
                    sys.stdout.flush()
                    if not hashes_match(remote_hash, up_status['server_hash']):
                        print('Mirror and repo hashes do not match! Re-uploading...')
                        up_status = self.__upload_package(local_path, package_id, version, True)
                        if not hashes_match(remote_hash, up_status['server_hash']):
                            if retry < 3:
                                retry += 1
                                up_status = self.sync_and_verify_package(package, retry)
                            else:
                                print('Max sync retries reached! Moving on...')
                                return up_status

                if up_status['uploaded']:
                    print('Package uploaded!')

                if not up_status['uploaded']:
                    print('Package already uploaded!')
            else:
                # print(''.join(['Response Body: ', up_status['response'].text])) # @todo might want this for debug
                print('Package not mirrored!')
        else:
            up_status = {
                'response': None,
                'mirrored': False,
                'uploaded': False,
                'server_hash': False
            }
        print('')
        return up_status

    def sync_packages(self):
        """        
        :return: 
        """
        done = False
        url = self.remote_packages_url
        use_remote_json = self.remote_json_api
        while not done:
            # pull packages from the remote api
            response = pull_packages(url, json=use_remote_json)
            # was the response good?
            if response.status_code == 200:
                if use_remote_json:
                    # Handle JSON pages
                    page = response.json()
                    # data object
                    data = page['d']
                    # Grab the results
                    results = data['results'] if 'results' in data else []
                    # For each result
                    for package in results:
                        # sync it!
                        self.sync_and_verify_package(package)

                    # done = True  # @todo this is temporary

                    # If we have a next key continue to the next page
                    if VALUE_NEXT['json'] in data:
                        # Set the url
                        url = data[VALUE_NEXT['json']]
                    else:
                        # Break out
                        done = True
                else:
                    # Handle XML pages
                    page = response.objectified
                    # Whats the size of the entry list
                    if len(page.entry) > 0:
                        for package in page.entry:
                            # sync it!
                            self.sync_and_verify_package(package)
                    # Get the last link on the page
                    link = page.link[0] if 0 > (len(page.link) - 1) else page.link[(len(page.link) - 1)]
                    # If the last link is the next link set it's url as the target url for the next iteration
                    if link.get(KEY_REL) == VALUE_NEXT['xml']:
                        url = link.get(KEY_HREF)
                    else:
                        # Break out
                        done = True

            else:
                print('Received bad http code from remote API. Sleeping for 10 and trying again. Response Code: ' + str(
                    response.status_code))
                sleep(10)
        return True
