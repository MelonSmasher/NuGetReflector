from bs4 import BeautifulSoup
from requests import get, put, exceptions
from subprocess import call
import hashlib
import base64
import sys
import os
import time
import datetime


def _pull(url, json=False):
    """
    :param url: 
    :param json: 
    :return: 
    """
    tries = 0
    while tries < 3:
        response = False
        if json:
            try:
                response = get(url, headers={'Accept': 'application/json'}, timeout=5.501)
                if response.status_code == 200:
                    return response
                elif response.status_code == 404:
                    print('Received a NOT FOUND response')
                    print(str(response.status_code) + ' / ' + response.reason)
                    print(url)
                    return response
            except exceptions.Timeout:
                print('Timed out when trying to pull...')
            except exceptions.ConnectionError:
                print('Timed out when trying to pull...')
            except Exception as e:
                print('Ran into a general error when trying to pull...')
                print(e.message)
                print(e)
        else:
            try:
                response = get(url, timeout=5.501)
                if response.status_code == 200:
                    response.objectified = BeautifulSoup(response.content, 'xml')
                    return response
                elif response.status_code == 404:
                    print('Received a NOT FOUND response')
                    print(str(response.status_code) + ' / ' + response.reason)
                    print(url)
                    return response
            except exceptions.Timeout:
                print('Timed out when trying to pull...')
            except exceptions.ConnectionError:
                print('Timed out when trying to pull...')
            except Exception as e:
                print('Ran into a general error when trying to pull...')
                print(e.message)
                print(e)
        print('Received an undefined response')
        if response:
            print(str(response.status_code) + ' / ' + response.reason)
        tries += 1
        print('Sleeping for 10 then trying again...')
        time.sleep(10)
    return False


def pull_package(title, version, url, json=False):
    """
    :param title: 
    :param version: 
    :param url: 
    :param json: 
    :return: 
    """
    return _pull(''.join([url, '(Id=\'', title, '\',Version=\'', version, '\')']), json=json)


def pull_packages(url, json=False):
    """
    :param url: 
    :param json: 
    :return: 
    """
    return _pull(url, json=json)


def pull_updates(url):
    """
    :param url:
    :return:
    """
    return _pull(url, json=False)


def push_package_dotnet(package_path, repo_url, api_key, dotnet):
    """
    :param package_path: 
    :param repo_url: 
    :param api_key: 
    :param dotnet: 
    :return: 
    """
    cmd = ' '.join([dotnet, 'nuget', 'push', package_path, '-s', repo_url, '-k', api_key])
    return call(cmd, shell=True)


def push_package_native(package_path, repo_url, api_key):
    """
    :param package_path: 
    :param repo_url: 
    :param api_key: 
    :return: 
    """
    f = open(package_path, mode='rb')
    files = {'package': ('package', f, 'application/octet-stream')}
    headers = {'X-NuGet-ApiKey': api_key}
    return put(repo_url, files=files, headers=headers)


def download_file(url, save_to):
    """
    :param url: 
    :param save_to: 
    :return: 
    """
    count = 0
    sys.stdout.write('Downloading.')
    sys.stdout.flush()
    # Does the file already exist?
    if os.path.isfile(save_to):
        # If the file exists remove it since we forced
        os.remove(save_to)
    # Get the file and stream it to the disk
    r = get(url, stream=True)
    with open(save_to, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                # Count the chunks
                count += 1
                if count >= 1024:
                    # Write a dot every 1024 chunks
                    sys.stdout.write('.')
                    sys.stdout.flush()
                    count = 0
                # Write to the file when the chunk gets to 1024
                f.write(chunk)
                f.flush()
    print(' Done!')
    return True if os.path.isfile(save_to) else False


def sha512sum(file_path, block_size=65536):
    """
    :param file_path: 
    :param block_size:
    :return: 
    """
    return base64.encodestring(
        __hash_byte_str_iter(__file_as_block_iter(open(file_path, 'rb'), block_size), hashlib.sha512(), False)
    ).replace("\n", '')


def sha256sum(file_path, block_size=65536):
    """
    :param file_path: 
    :param block_size: 
    :return: 
    """
    return base64.encodestring(
        __hash_byte_str_iter(__file_as_block_iter(open(file_path, 'rb'), block_size), hashlib.sha256(), False)
    ).replace("\n", '')


def sha1sum(file_path, block_size=65536):
    """
    :param file_path: 
    :param block_size: 
    :return: 
    """
    return base64.encodestring(
        __hash_byte_str_iter(__file_as_block_iter(open(file_path, 'rb'), block_size), hashlib.sha1, False)
    ).replace("\n", '')


def hashes_match(hash_1, hash_2):
    """
    :param hash_1: 
    :param hash_2: 
    :return: 
    """
    if str(hash_1) == str(hash_2):
        return True
    else:
        return False


def verify_hash(file_path, target_hash, message='Verifying package hash.', hash_method='sha512'):
    """
    :param file_path: 
    :param target_hash: 
    :param message: 
    :param hash_method: 
    :return: 
    """
    sys.stdout.write(message)
    sys.stdout.flush()
    hash_method.lower()

    if hash_method == 'sha512':
        sys.stdout.write('.')
        local_hash = sha512sum(file_path)
        sys.stdout.write('.')
    elif hash_method == 'sha256':
        local_hash = sha256sum(file_path)
        sys.stdout.write('.')
    elif hash_method == 'sha1':
        sys.stdout.write('.')
        local_hash = sha1sum(file_path)
    else:
        sys.stdout.write('.')
        local_hash = sha512sum(file_path)

    print('. Done!')
    return hashes_match(local_hash, target_hash)


def utc_to_epoch(time_stamp, time_format='%Y-%m-%dT%H:%M:%SZ'):
    """
    :param time_stamp:
    :param time_format:
    :return:
    """
    return int(time.mktime(time.strptime(time_stamp, time_format)))


def epoch_to_utc(epoch=0, time_format='%Y-%m-%dT%H:%M:%SZ'):
    """
    :param epoch:
    :param time_format:
    :return:
    """
    return time.strftime(time_format, time.gmtime(epoch))


def now_as_epoch():
    """
    :return:
    """
    return int(time.time())


def first_epoch():
    """
    :return:
    """
    return int(0)


def now_as_utc(time_format='%Y-%m-%dT%H:%M:%SZ'):
    """
    :param time_format:
    :return:
    """
    return datetime.datetime.now().strftime(time_format)


def touch(file_path):
    """
    :param file_path:
    :return:
    """
    with open(file_path, 'a'):
        os.utime(file_path, None)


def store_delta(delta, file_path='storage/sync.delta'):
    """
    :param delta:
    :param file_path:
    :return:
    """
    touch(file_path)
    with open(file_path, 'w') as f:
        f.write(''.join([delta, "\n"]))


def read_delta(file_path='storage/sync.delta'):
    """
    :param file_path:
    :return:
    """
    touch(file_path)
    try:
        with open(file_path, 'rb') as f:
            f.seek(-21, 2)
            return str(f.readlines()[-1].decode().rstrip("\n"))
    except IOError:
        return None


def __hash_byte_str_iter(bytes_iter, hasher, as_hex_str=False):
    """
    :param bytes_iter:
    :param hasher:
    :param as_hex_str:
    :return: 
    """
    for block in bytes_iter:
        hasher.update(block)
    return hasher.hexdigest() if as_hex_str else hasher.digest()


def __file_as_block_iter(f, block_size=65536):
    """
    :param f:
    :param block_size:
    :return: 
    """
    with f:
        block = f.read(block_size)
        while len(block) > 0:
            yield block
            block = f.read(block_size)
