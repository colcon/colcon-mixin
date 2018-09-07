# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
import socket
import time
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import urlopen

from colcon_core.location import get_config_path
from colcon_core.logging import colcon_logger
from colcon_mixin.mixin import get_mixin_files
from colcon_mixin.mixin import get_mixin_path
import yaml

logger = colcon_logger.getChild(__name__)

"""The path of the yaml file describing the mixin repositories."""
mixin_repositories_file = get_config_path() / 'mixin_repositories.yaml'


def get_repositories():
    """
    Get the registered repositories.

    :rtype: dict
    """
    global mixin_repositories_file
    if not mixin_repositories_file.exists():
        return {}
    if mixin_repositories_file.is_dir():
        raise IsADirectoryError()
    content = mixin_repositories_file.read_text()
    data = yaml.load(content)
    assert isinstance(data, dict), 'The content of the configuration file ' \
        "'%s' should be a dictionary" % mixin_repositories_file
    return data


def set_repositories(repositories):
    """
    Persist the passed repositories in the configuration file.

    :param dict repositories: The repositories
    """
    assert isinstance(repositories, dict), \
        'The passed repositories should be a dictionary'
    global mixin_repositories_file
    data = yaml.dump(repositories, default_flow_style=False)
    os.makedirs(str(mixin_repositories_file.parent), exist_ok=True)
    with mixin_repositories_file.open('w') as h:
        h.write(data)


def get_repository_mixin_files(*, repository_name):
    """
    Get the configuration files for a specific repository.

    :param str repository_name: The repository name
    :rtype: list
    """
    return get_mixin_files(get_mixin_path() / repository_name)


def load_url(url, retry=2, retry_period=1, timeout=10):
    """
    Load a URL.

    :param int retry: The number of retries in case the request fails
    :param int retry_period: The period to wait before the first retry. Every
      subsequent retry will double the period.
    :param int timeout: The timeout for each request

    :rtype: str
    """
    try:
        h = urlopen(url, timeout=timeout)
    except HTTPError as e:
        if e.code == 503 and retry:
            time.sleep(retry_period)
            return load_url(
                url, retry=retry - 1, retry_period=retry_period * 2,
                timeout=timeout)
        e.msg += ' (%s)' % url
        raise
    except URLError as e:
        if isinstance(e.reason, socket.timeout) and retry:
            time.sleep(retry_period)
            return load_url(
                url, retry=retry - 1, retry_period=retry_period * 2,
                timeout=timeout)
        raise URLError(str(e) + ' (%s)' % url)
    except socket.timeout as e:
        if retry:
            time.sleep(retry_period)
            return load_url(
                url, retry=retry - 1, retry_period=retry_period * 2,
                timeout=timeout)
        raise socket.timeout(str(e) + ' (%s)' % url)
    content = h.read()
    return content.decode('utf-8')
