from lxml import objectify
from requests import get
import hashlib
import base64
import sys


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
        print(' Pass!')
        return True
    else:
        print(' Fail!')
        print('Hash 1: ' + hash_1)
        print('Hash 2: ' + hash_2)
        return False


def verify_hash(file_path, target_hash, message='Verifying package hash...', hash_method='sha512'):
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
        local_hash = sha512sum(file_path)
    elif hash_method == 'sha256':
        local_hash = sha256sum(file_path)
    elif hash_method == 'sha1':
        local_hash = sha1sum(file_path)
    else:
        local_hash = sha512sum(file_path)

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
