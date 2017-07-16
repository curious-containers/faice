import os
import socket
import requests


def load_local(file_path):
    with open(os.path.expanduser(file_path)) as f:
        return f.read()


def load_url(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.text


# https://stackoverflow.com/a/2838309
def find_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port
