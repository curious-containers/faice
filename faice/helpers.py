import os
import sys
import requests
import socket
import textwrap
from traceback import format_exc


def graceful_exception(error_text):
    """function decorator"""
    def dec(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except:
                print(file=sys.stderr)
                print(format_exc(), file=sys.stderr)
                print_user_text([
                    'ERROR: {} For detailed information examine the exception output above.'.format(error_text)
                ], error=True)
                exit(1)
        return wrapper
    return dec


@graceful_exception('Could not load experiment file.')
def load_local(file_path):
    with open(os.path.expanduser(file_path)) as f:
        return f.read()


@graceful_exception('Could not load experiment file from URL.')
def load_url(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.text


# https://stackoverflow.com/a/2838309
@graceful_exception('Could not find a free network port.')
def find_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def print_user_text(blocks, error=False):
    if error:
        for block in blocks:
            print(textwrap.fill(block), file=sys.stderr)
    else:
        for block in blocks:
            print(textwrap.fill(block))
