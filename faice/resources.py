import os
import socket
import requests
from urllib.parse import urlparse


def read_file(file_location):
    if urlparse(file_location).scheme != '':
        return read_url(file_location)
    return read_local(file_location)


def read_url(file_location):
    r = requests.get(file_location)
    r.raise_for_status()
    return r.text


def read_local(file_location):
    with open(os.path.expanduser(file_location)) as f:
        return f.read()


# https://stackoverflow.com/a/2838309
def find_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port
