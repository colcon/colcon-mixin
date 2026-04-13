# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from collections import defaultdict
import os
from pathlib import Path

from colcon_core.environment_variable import EnvironmentVariable
from colcon_core.location import get_config_path
from colcon_core.logging import colcon_logger
import yaml

logger = colcon_logger.getChild(__name__)

mixins_by_verb = None

"""Environment variable to read additional mixins from"""
COLCON_MIXIN_PATH = EnvironmentVariable(
    'COLCON_MIXIN_PATH',
    'Provide additional directories to look for mixin files. '
    'Separate individual directories with colons.')


def get_mixin_path():
    """
    Get the path where mixins are stored in the COLCON_HOME configuration.

    :rtype: Path
    """
    return get_config_path() / 'mixin'


def get_additional_mixin_paths():
    """
    Get the paths where additional mixins may be found.

    :rtype: list
    """
    # Read additional paths from the environment variable.
    env_var = os.environ.get(COLCON_MIXIN_PATH.name, '')
    return [Path(x) for x in env_var.split(os.pathsep) if x]


def get_mixin_files(path=None):
    """
    Get the paths of all mixin files in a certain path.

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
    mixin_locations = [get_mixin_path()] + get_additional_mixin_paths()
    if mixins_by_verb is None:
        mixins_by_verb = defaultdict(dict)
        for location in mixin_locations:
            for path in get_mixin_files(location):
                add_mixins(Path(path), mixins_by_verb)
    return mixins_by_verb


def add_mixins(mixin_path, mixins_by_verb):
    """
    Add the mixins from the file to the collection.

    :param Path mixin_path: The path of the mixin file
    :param dict mixins_by_verb: The nested dictionary of mixins grouped by the
      verb
    """
    content = mixin_path.read_text()
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
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


def _get_mixin_references(verb_key, mixin_name, mixin_def):
    """
    Validate and return the composed mixin references for a mixin.

    :param tuple verb_key: The verb tuple
    :param str mixin_name: The name of the mixin to inspect
    :param object mixin_def: The raw mixin definition
    :raises RuntimeError: On malformed mixin definitions
    :rtype: list
    """
    context = '.'.join(verb_key)
    if not isinstance(mixin_def, dict):
        raise RuntimeError(
            "Mixin '%s' for verb '%s' must define a dictionary of arguments" %
            (mixin_name, context))

    refs = mixin_def.get('mixin', [])
    if not isinstance(refs, list):
        raise RuntimeError(
            "Mixin '%s' for verb '%s' defines reserved key 'mixin' with "
            'invalid type, expected a list' % (mixin_name, context))

    for ref in refs:
        if not isinstance(ref, str):
            raise RuntimeError(
                "Mixin '%s' for verb '%s' defines reserved key 'mixin' "
                'with non-string entry %r' % (mixin_name, context, ref))

    return refs


def resolve_mixin(verb_key, mixin_name, mixins_by_verb, _resolving=None):
    """
    Resolve a mixin by flattening its composed references.

    Referenced mixins are resolved left-to-right, then the mixin's own
    arguments are merged on top. Precedence matches the CLI behavior of
    _update_args: lists use prepending order, first scalar wins between
    references, own scalars always override.

    :param tuple verb_key: The verb tuple
    :param str mixin_name: The name of the mixin to resolve
    :param dict mixins_by_verb: The full mixin collection
    :param set _resolving: Internal set for cycle detection
    :raises RuntimeError: On cycles or missing references
    :rtype: dict
    """
    if _resolving is None:
        _resolving = set()

    verb_mixins = mixins_by_verb.get(verb_key, {})
    if mixin_name not in verb_mixins:
        raise RuntimeError(
            "Mixin '%s' referenced in composition does not exist for "
            "verb '%s'" % (mixin_name, '.'.join(verb_key)))

    if mixin_name in _resolving:
        raise RuntimeError(
            'Cycle detected in mixin composition: %s' % mixin_name)

    mixin_def = verb_mixins[mixin_name]
    refs = _get_mixin_references(verb_key, mixin_name, mixin_def)

    _resolving.add(mixin_name)
    try:
        resolved = {}
        for ref in refs:
            ref_args = resolve_mixin(verb_key, ref, mixins_by_verb, _resolving)
            for k, v in ref_args.items():
                if k not in resolved:
                    resolved[k] = v
                elif isinstance(resolved[k], list) and isinstance(v, list):
                    resolved[k] = v + resolved[k]

        for k, v in mixin_def.items():
            if k == 'mixin':
                continue
            if k not in resolved:
                resolved[k] = v
            elif isinstance(resolved[k], list) and isinstance(v, list):
                resolved[k] = v + resolved[k]
            else:
                resolved[k] = v
        return resolved
    finally:
        _resolving.discard(mixin_name)
