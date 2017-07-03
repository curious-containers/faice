import os
import requests


def load_local(file_path):
    with open(os.path.expanduser(file_path)) as f:
        return f.read()


def load_url(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.text