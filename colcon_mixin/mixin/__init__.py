# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from collections import defaultdict
import os
from pathlib import Path

from colcon_core.location import get_config_path
from colcon_core.logging import colcon_logger
import yaml

logger = colcon_logger.getChild(__name__)

mixins_by_verb = None


def get_mixin_path():
    """
    Get the path where mixin is stored.

    :rtype: Path
    """
    return get_config_path() / 'mixin'


def get_mixin_files(path=None):
    """
    Get the paths of all mixin files.

    The mixin path is recursively being crawled for files ending in `.mixin`.
    Directories starting with a dot (`.`) are being ignored.

    :rtype: list
    """
    mixin_path = path or get_mixin_path()
    if not mixin_path.is_dir():
        return []

    files = []
    for dirpath, dirnames, filenames in os.walk(
        str(mixin_path), followlinks=True
    ):
        # skip subdirectories starting with a dot
        dirnames[:] = filter(lambda d: not d.startswith('.'), dirnames)
        dirnames.sort()

        for filename in sorted(filenames):
            if not filename.endswith('.mixin'):
                continue
            path = os.path.join(dirpath, filename)
            files.append(path)
    return files


def get_mixins():
    """
    Get the mixins from all files.

    The result is being cached and return on repeated calls.

    :rtype: dict
    """
    global mixins_by_verb
    if mixins_by_verb is None:
        mixins_by_verb = defaultdict(dict)
        for path in get_mixin_files():
            _get_mixins(Path(path), mixins_by_verb)
    return mixins_by_verb


def _get_mixins(mixin_path, mixins_by_verb):
    content = mixin_path.read_text()
    try:
        data = yaml.load(content)
    except Exception as e:
        logger.warning(
            "Skipping mixin file '%s' since it failed to parse: %s" %
            (mixin_path.absolute(), e))
        return

    if data is None:
        logger.info("Empty mixin file '%s'" % mixin_path.absolute())
        return
    if not isinstance(data, dict):
        logger.warning(
            "Skipping mixin file '%s' since it doesn't contain a dict" %
            mixin_path.absolute())
        return

    logger.info(
        "Using mixins from '%s'" % mixin_path.absolute())
    for verb, mixins in data.items():
        verb_key = tuple(verb.split('.'))
        for name, args in mixins.items():
            if name in mixins_by_verb[verb_key]:
                logger.warning(
                    "Mixin '%s' from file '%s' is overwriting another mixin "
                    'with the same name' %
                    (name, mixin_path.absolute()))
            mixins_by_verb[verb_key][name] = args
