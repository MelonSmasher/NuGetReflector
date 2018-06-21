from __future__ import print_function
from os.path import isfile, exists
from os import mknod, remove
from time import sleep
from yaml import load
from reflector.util import *
from multiprocessing.dummy import Pool as ThreadPool
from tqdm import tqdm

KEY_TITLE = {'xml': 'title', 'json': 'Id'}
KEY_CONTENT = 'content'
KEY_SRC = 'src'
KEY_REL = 'rel'
KEY_HREF = 'href'
VALUE_NEXT = {'xml': 'next', 'json': '__next'}
PBAR = tqdm(total=len([]))


class Config(object):
    def __init__(self):
        with open('config/config.yaml') as data_file:
            c = load(data_file)
            self.remote_url = c['remote']['url'].rstrip('/')
            self.update_feed = c['remote']['update_feed']
            self.remote_json_api = c['remote']['json_api']
            self.local_url = c['local']['url'].rstrip('/')
            self.local_json_api = c['local']['json_api']
            self.local_api_key = c['local']['api_key']
            self.package_storage_path = c['local']['package_storage_path'].rstrip('/').rstrip('\\')
            self.hash_verify_downloads = c['hash']['verify_downloads']
            self.hash_verify_uploaded = c['hash']['verify_uploaded']
            self.dotnet_path = c['local']['dotnet_path']
            if not self.dotnet_path or not isfile(self.dotnet_path):
                raise EnvironmentError('DotNot CLI executable is not configured or the path specified does not exist!')


class Mirror(object):
    def __init__(self,
                 remote_url,
                 update_feed,
                 remote_json_api,
                 local_url,
                 local_json_api,
                 package_storage_path,
                 local_api_key,
                 dotnet_path,
                 verify_downloads=True,
                 verify_uploaded=True
                 ):
        """
        :param remote_url:
        :param update_feed:
        :param remote_json_api:
        :param local_url:
        :param local_json_api:
        :param package_storage_path:
        :param local_api_key:
        :param dotnet_path:
        :param verify_downloads:
        :param verify_uploaded:
        """
        self.remote_api_url = '/'.join([remote_url, 'api/v2'])
        self.update_feed = update_feed
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

    def __sync(self, content_url, save_to, package_name, version,
               source_hash=None,
               source_hash_method=None,
               dl_reties=0,
               up_retries=0,
               force_dl=False,
               force_up=False,
               multi=True
               ):
        """
        :param content_url: 
        :param save_to: 
        :param package_name: 
        :param version: 
        :param source_hash: 
        :param source_hash_method: 
        :param dl_reties:
        :param up_retries:
        :param force_dl:
        :param force_up:
        :param multi:
        :return: 
        """
        # Is the package already uploaded? Pull it from the target API
        pull_request = pull_package(package_name, version, self.local_packages_url, self.local_json_api)

        if not pull_request.status_code:
            if not multi:
                print('Unable to sync package.')
            return False

        # What did the target api return
        if pull_request.status_code == 404 or pull_request.status_code == 200 or force_dl or not isfile(save_to):
            # Download the file if we are forcing or it was not already uploaded or cached
            if pull_request.status_code == 404 or not isfile(save_to) or force_dl:
                if not download_file(content_url, save_to):
                    if not multi:
                        print('Package does not exists after download!?!')
                    return False

            # Did we get a source hash when this was called
            if source_hash is not None and self.verify_downloads:
                # Verify the cached package hash
                hash_verified = verify_hash(save_to, source_hash, hash_method=source_hash_method, multi=multi)
                # If the hash is not verified and we have retired less than 3 times
                if not hash_verified and dl_reties < 3:
                    # Count a retry
                    dl_reties += 1
                    if not multi:
                        print('Cache hash does not match source hash... retying download...')
                    # Run another sync
                    return self.__sync(
                        content_url,
                        save_to,
                        package_name,
                        version,
                        source_hash=source_hash,
                        source_hash_method=source_hash_method,
                        dl_reties=dl_reties,
                        up_retries=up_retries,
                        force_dl=True,
                        force_up=force_up
                    )
                elif not hash_verified and dl_reties >= 3:
                    # Reached max retries
                    if not multi:
                        print('Retried to download the package 3 times. Skipping :( ')
                    return False
            else:
                if not multi:
                    print('Skipping cache hash verification...')
        else:
            # API Error
            if not multi:
                print(''.join(['API error! Code: ', str(pull_request.status_code)]))
            return False

        # Made it here? Cache hash either verified or skipped verification
        if pull_request.status_code == 404 or pull_request.status_code == 200 or force_up:
            if pull_request.status_code == 404 or force_up:
                # Send the package up using the dotnet binary
                return_code = push_package_dotnet(
                    save_to,
                    self.local_api_upload_url,
                    self.local_api_key,
                    self.dotnet_path
                )

                if return_code is not 0:
                    if not multi:
                        print('Push failed, retying with native library.')
                        print('Uploading package...')
                    # If the dotnet binary does not return 0 try to use a python library
                    push_response = push_package_native(
                        save_to,
                        self.local_api_upload_url,
                        self.local_api_key
                    )
                    if not multi:
                        print(''.join(['Response code: ', str(push_response.status_code)]))
                        if push_response.status_code is not 200:
                            print('Upload failed... :-(')
                            print(''.join(['Response message: ', str(push_response.content)]))

        else:
            # API Error
            # This should never happen. It should get caught above
            if not multi:
                print(''.join(['API error! Code: ', str(pull_request.status_code)]))
            return False

        # If we have a source hash Start verifying it
        if source_hash is not None and self.verify_uploaded:
            use_target_json = self.local_json_api
            # Pull the package after uploading it
            pull_request = pull_package(package_name, version, self.local_packages_url, use_target_json)
            # Did we find the package
            if pull_request.status_code == 200:
                # Get the hash
                if use_target_json:
                    # If we are using a json api get it this way
                    target_hash = pull_request.json()['d']['PackageHash']
                else:
                    # If we use the XML api get it this way
                    target_hash = pull_request.objectified.properties.PackageHash.text

                # Does the source hash match the target repo hash?
                if hashes_match(target_hash, source_hash):
                    if not multi:
                        print('Package synced and verified!')
                    return True
                else:
                    if not multi:
                        print('Package synced but checksum do not match!')
                    return False

            elif up_retries <= 3:
                up_retries += 1
                if not multi:
                    print(''.join(['API error! Code: ', str(pull_request.status_code)]))
                    print('Package not synced retrying...')
                return self.__sync(
                    content_url,
                    save_to,
                    package_name,
                    version,
                    source_hash=source_hash,
                    source_hash_method=source_hash_method,
                    dl_reties=dl_reties,
                    up_retries=up_retries,
                    force_dl=False,
                    force_up=True
                )

            elif up_retries >= 3:
                if not multi:
                    print('Max upload retries reached. Skipping :-( ')
                    print(''.join(['API error! Code: ', str(pull_request.status_code)]))
                return False

            else:
                if not multi:
                    # API Error
                    print(''.join(['API error! Code: ', str(pull_request.status_code)]))
                return False
        else:
            if not multi:
                print('Package synced!')
            return True

    def sync_package(self, package, multi=True):
        """
        :param package:
        :param multi:
        :return: 
        """
        # Extract the info that we need from the package entry
        # Dict keys vary depending if the page was pulled in XML or JSON
        use_remote_json = self.remote_json_api
        package_name = str(package[KEY_TITLE['json']]) if use_remote_json else str(package.title.text)
        version = str(package['Version']) if use_remote_json else str(package.properties.Version.text)
        metadata = package['__metadata'] if use_remote_json else {}
        content_url = metadata['media_src'] if use_remote_json else package.content['src']
        package_n_v = '.'.join([package_name, version])
        save_to = os.path.join(self.package_storage_path, '.'.join([package_n_v, 'nupkg']))
        if use_remote_json:
            remote_hash = str(package['PackageHash'])
            remote_hash_method = str(package['PackageHashAlgorithm']).lower()
        else:
            remote_hash = str(package.properties.PackageHash.text)
            remote_hash_method = str(package.properties.PackageHashAlgorithm.text).lower()

        # Begin package sync
        if not multi:
            print('')
            print(''.join(['########## ', package_n_v, ' ##########']))

        sync = self.__sync(content_url, save_to, package_name, version, source_hash=remote_hash,
                           source_hash_method=remote_hash_method)
        if not multi:
            print('Done!')
        else:
            PBAR.update(1)
        return sync

    def delta_sync(self):
        url = self.update_feed
        previous_delta = read_delta()
        new_delta = None
        lock_file = '/tmp/reflector_full.lock'
        delta_lock_file = '/tmp/reflector_delta.lock'
        if not exists(lock_file) and not exists(delta_lock_file):
            # Create the lock file
            mknod(delta_lock_file)

            if previous_delta is not None:
                print(' '.join(['Syncing packages since:', previous_delta]))
                previous_delta = utc_to_epoch(previous_delta)
            else:
                print('No previous delta syncs. Syncing all updates!')
                previous_delta = first_epoch()

            # Grab the update feed
            response = pull_updates(url)
            # Did the request go well?
            if response.status_code == 200:
                # Get the page
                page = response.objectified
                # Get all items
                items = page.find_all('item')
                # Loop over the items
                for item in items:
                    # Get when this was updated
                    updated = utc_to_epoch(item.updated.text)
                    # Get the new delta on the first package
                    if new_delta is None:
                        new_delta = item.updated.text
                    # determine if it has been updated since the last run
                    if updated > previous_delta:
                        # Grab the package info
                        parts = str(item.origLink.text).split('/')
                        version = parts[-1]
                        title = parts[-2]
                        # Sync the package
                        pull_response = pull_package(title, version, self.remote_packages_url, self.remote_json_api)
                        if pull_response.status_code == 200:
                            package = pull_response.json() if self.remote_json_api else pull_response.objectified
                            self.sync_package(package, False)
                        else:
                            print('Received bad http code from remote API when pulling package. Response Code: ' + str(
                                pull_response.status_code))

                # If the new delta is still not set. Set it to the previous one
                if new_delta is None:
                    new_delta = epoch_to_utc(previous_delta)
                # write epoch to the delta file
                store_delta(new_delta)
                # remove the lock file
                remove(delta_lock_file)
            else:
                print('Received bad http code from remote API. Response Code: ' + str(response.status_code))
                return False
        else:
            print('Lock file exists, is there a sync session running?')
        return True

    def sync_packages_xthread(self):
        """
        :return:
        """
        done = False
        url = self.remote_packages_url
        use_remote_json = self.remote_json_api
        lock_file = '/tmp/reflector_full.lock'
        packages = []

        if not exists(lock_file):
            # Create the lock file
            mknod(lock_file)
            while not done:
                print('Pulling packages from: ' + url)
                response = pull_packages(url, json=use_remote_json)
                if response:
                    # was the response good?
                    if response.status_code == 200:
                        if use_remote_json:
                            # Handle JSON pages
                            page = response.json()
                            # data object
                            data = page['d']
                            # Grab the results add append them to the packages
                            packages = packages + (data['results'] if 'results' in data else [])
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
                            packages = packages + page.find_all('entry')
                            # Whats the size of the entry list
                            # Find all links
                            links = page.find_all('link')
                            # Get the last link on the page
                            link = links[0] if 0 > (len(links) - 1) else links[(len(links) - 1)]
                            # If the last link is the next link set it's url as the target url for the next iteration
                            if link[KEY_REL] == VALUE_NEXT['xml']:
                                url = str(link['href'])
                            else:
                                print(' ')
                                print('Done!')
                                # Remove the lock file
                                remove(lock_file)
                                # Break out
                                done = True
                    else:
                        print(
                            'Received bad http code from remote API. Sleeping for 10 and trying again. Response Code: ' + str(
                                response.status_code))
                        sleep(10)
                else:
                    print('Timed out when pulling package list... sleeping for 25 then trying again.')
                    sleep(25)

            # Sync the packages
            global PBAR
            PBAR = tqdm(total=len(packages))
            pool = ThreadPool(8)
            pool.map_async(self.sync_package, packages)
            pool.close()
            pool.join()

        else:
            print('Lock file exists, is there a sync session running?')
            return True

    def sync_packages(self):
        """        
        :return: 
        """
        done = False
        cool_down_counter = 250
        url = self.remote_packages_url
        use_remote_json = self.remote_json_api
        lock_file = '/tmp/reflector_full.lock'

        if not exists(lock_file):
            # Create the lock file
            mknod(lock_file)
            while not done:
                print('Pulling packages from: ' + url)
                # pull packages from the remote api
                response = pull_packages(url, json=use_remote_json)
                if response:
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
                                self.sync_package(package, False)
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
                            entries = page.find_all('entry')
                            # Whats the size of the entry list
                            if len(entries) > 0:
                                for package in entries:
                                    # sync it!
                                    self.sync_package(package, False)

                            links = page.find_all('link')
                            # Get the last link on the page
                            link = links[0] if 0 > (len(links) - 1) else links[(len(links) - 1)]
                            # If the last link is the next link set it's url as the target url for the next iteration
                            if link[KEY_REL] == VALUE_NEXT['xml']:
                                url = str(link['href'])
                                print(' ')
                                cool_down_counter -= 1
                                if cool_down_counter == 1:
                                    # Cool down for 5 seconds every 250 pages...
                                    print('Cooling down for 30 seconds...')
                                    print(' ')
                                    sleep(30)
                                    cool_down_counter = 250
                            else:
                                print(' ')
                                print('Done!')
                                # Remove the lock file
                                remove(lock_file)
                                # Break out
                                done = True
                    else:
                        print(
                            'Received bad http code from remote API. Sleeping for 10 and trying again. Response Code: ' + str(
                                response.status_code))
                        sleep(10)
                else:
                    print('Timed out when pulling package list... sleeping for 25 then trying again.')
                    sleep(25)
        else:
            print('Lock file exists, is there a sync session running?')
        return True
