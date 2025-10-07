# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from base64 import b64encode
import netrc
import os
import socket
import time
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen

from colcon_core.location import get_config_path
from colcon_core.logging import colcon_logger
from colcon_mixin.mixin import get_mixin_files
from colcon_mixin.mixin import get_mixin_path
import yaml

logger = colcon_logger.getChild(__name__)

"""The path of the yaml file describing the mixin repositories."""
mixin_repositories_file = get_config_path() / 'mixin_repositories.yaml'

NETRC = '\0NETRC\0'


def get_repositories():
    """
    Get the registered repositories.

    :rtype: dict
    """
    if not mixin_repositories_file.exists():
        return {}
    if mixin_repositories_file.is_dir():
        raise IsADirectoryError()
    content = mixin_repositories_file.read_text()
    data = yaml.safe_load(content)
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


def load_url(url, retry=2, retry_period=1, timeout=10, auth=NETRC):
    """
    Load a URL.

    :param int retry: The number of retries in case the request fails
    :param int retry_period: The period to wait before the first retry. Every
      subsequent retry will double the period.
    :param int timeout: The timeout for each request
    :param str auth: Optional value to use for Authorization header. Default
      behavior is to search for entries in the user's netrc file.

    :rtype: str
    """
    request = Request(url)
    if auth is NETRC:
        auth = None
        try:
            entry = netrc.netrc().authenticators(request.origin_req_host)
        except netrc.NetrcParseError:
            logger.exception('Failed to parse netrc file, skipping...')
        else:
            if entry and (entry[0] or entry[2]):
                credentials = f'{entry[0]}:{entry[2]}'
                auth = 'Basic ' + b64encode(credentials.encode()).decode()
                logger.debug(f"Using netrc for '{request.origin_req_host}'")
    if auth:
        request.add_header('Authorization', auth)
    try:
        h = urlopen(request, timeout=timeout)
    except HTTPError as e:
        if e.code == 503 and retry:
            time.sleep(retry_period)
            return load_url(
                url, retry=retry - 1, retry_period=retry_period * 2,
                timeout=timeout, auth=auth)
        e.msg += ' (%s)' % url
        raise
    except URLError as e:
        if isinstance(e.reason, socket.timeout) and retry:
            time.sleep(retry_period)
            return load_url(
                url, retry=retry - 1, retry_period=retry_period * 2,
                timeout=timeout, auth=auth)
        raise URLError(str(e) + ' (%s)' % url)
    except socket.timeout as e:
        if retry:
            time.sleep(retry_period)
            return load_url(
                url, retry=retry - 1, retry_period=retry_period * 2,
                timeout=timeout, auth=auth)
        raise socket.timeout(str(e) + ' (%s)' % url)
    content = h.read()
    return content.decode('utf-8')
