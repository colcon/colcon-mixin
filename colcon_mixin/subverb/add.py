# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from argparse import ArgumentTypeError

from colcon_core.plugin_system import satisfies_version
from colcon_mixin.mixin.repository import get_repositories
from colcon_mixin.mixin.repository import set_repositories
from colcon_mixin.subverb import MixinSubverbExtensionPoint


class AddMixinSubverb(MixinSubverbExtensionPoint):
    """Add the URL of a repository index."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            MixinSubverbExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def add_arguments(self, *, parser):  # noqa: D102
        parser.add_argument(
            'name',
            type=_non_empty_string_without_pathsep,
            help='The unique name identifying the repository')
        parser.add_argument(
            'url',
            type=_url_string,
            help='The url of a mixin repository index')

    def main(self, *, context):  # noqa: D102
        repos = get_repositories()
        if context.args.name in repos.keys():
            return "A repository with the name '{context.args.name}' " \
                'already exists'.format_map(locals())
        repos[context.args.name] = context.args.url
        set_repositories(repos)


def _non_empty_string_without_pathsep(value):
    if not value:
        raise ArgumentTypeError('must be a non-empty string')
    for pathsep in ('/', '\\'):
        if pathsep in value:
            raise ArgumentTypeError(
                "must not contain '{pathsep}'".format_map(locals()))
    return value


def _url_string(value):
    if '://' not in value:
        raise ArgumentTypeError("must contain '://'")
    return value
