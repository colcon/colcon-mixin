# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from colcon_core.plugin_system import satisfies_version
from colcon_mixin.mixin import get_mixin_files
from colcon_mixin.mixin.repository import get_repositories
from colcon_mixin.mixin.repository import get_repository_mixin_files
from colcon_mixin.subverb import MixinSubverbExtensionPoint


class ListMixinSubverb(MixinSubverbExtensionPoint):
    """List all repositories and their mixin."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            MixinSubverbExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def add_arguments(self, *, parser):  # noqa: D102
        argument = parser.add_argument(
            'name',
            nargs='?',
            help='Only list the information for a specific repository')
        try:
            from argcomplete.completers import ChoicesCompleter
        except ImportError:
            pass
        else:
            repos = get_repositories()
            argument.completer = \
                ChoicesCompleter(repos.keys())

    def main(self, *, context):  # noqa: D102
        repos = get_repositories()
        if context.args.name and context.args.name not in repos.keys():
            return "Passed repository name '{context.args.name}' is unknown" \
                .format_map(locals())

        mixin_files_from_repos = set()
        for name in sorted(repos.keys()):
            if context.args.name and context.args.name != name:
                continue
            url = repos[name]
            print('{name}: {url}'.format_map(locals()))
            mixin_files = get_repository_mixin_files(
                repository_name=name)
            for path in sorted(mixin_files):
                print('- {path}'.format_map(locals()))
                mixin_files_from_repos.add(path)

        mixin_files = get_mixin_files()
        mixin_files_without_repo = set(mixin_files) - mixin_files_from_repos
        if mixin_files_without_repo:
            print('mixin files not associated with a repository')
            for path in sorted(mixin_files_without_repo):
                print('- {path}'.format_map(locals()))
