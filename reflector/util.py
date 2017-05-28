from lxml import objectify
from requests import get
from subprocess import call
import hashlib
import base64
import sys
import os


def _pull(url, json=False):
    """
    :param url: 
    :param json: 
    :return: 
    """
    if json:
        headers = {'Accept': 'application/json'}
        return get(url, headers=headers)
    else:
        response = get(url)
        if response.status_code == 200:
            xml = response.content
            try:
                response.objectified = objectify.fromstring(xml)
                return response
            except Exception as e:
                print(e.message)
                return False
        else:
            return response


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


def push_package(dotnet, package_path, repo_url, api_key):
    """
    :param dotnet: 
    :param package_path: 
    :param repo_url: 
    :param api_key: 
    :return: 
    """
    cmd = ' '.join([dotnet, 'nuget', 'push', package_path, '-s', repo_url, '-k', api_key])
    return call(cmd, shell=True)


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
