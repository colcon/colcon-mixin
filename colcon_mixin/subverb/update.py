# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import os
import sys

from colcon_core.plugin_system import satisfies_version
from colcon_mixin.mixin import get_mixin_files
from colcon_mixin.mixin import get_mixin_path
from colcon_mixin.mixin.repository import get_repositories
from colcon_mixin.mixin.repository import get_repository_mixin_files
from colcon_mixin.mixin.repository import load_url
from colcon_mixin.subverb import MixinSubverbExtensionPoint
import yaml


class UpdateMixinSubverb(MixinSubverbExtensionPoint):
    """Update the mixin from the repository indexes."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            MixinSubverbExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def add_arguments(self, *, parser):  # noqa: D102
        parser.description += '\n\n' \
            'For each repository all mixin files are being fetched. ' \
            'The status if each mixin file is indicated by the following ' \
            'symbols:\n' \
            '  + added new mixin file\n' \
            '  * updated the existing mixin file\n' \
            '  . existing mixin file was already the same\n' \
            '  - renamed obsolete mixin file'
        argument = parser.add_argument(
            'name',
            nargs='?',
            help='Only update the mixin from a specific repository')
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

        # IDEA fetch all resources in parallel
        rc = 0
        for name in sorted(repos.keys()):
            if context.args.name and context.args.name != name:
                continue

            # fetch the repository index
            index_url = repos[name]
            print('fetching {name}: {index_url} ...'.format_map(locals()))
            try:
                content = load_url(index_url)
            except Exception as e:
                print(' ', str(e), file=sys.stderr)
                rc = 1
                continue

            # parse the repository index
            try:
                data = yaml.load(content)
            except Exception as e:
                print(' ', str(e), file=sys.stderr)
                rc = 1
                continue
            if not isinstance(data, dict) or 'mixin' not in data.keys():
                print('  The repository index should be a dictionary with a '
                      "'mixin' key, but it is: {data}".format_map(locals()))
                rc = 1
                continue

            # get existing mixin files to remove obsolete ones later
            mixin_files_before = get_repository_mixin_files(
                repository_name=name)

            # fetch all mixin files referenced in the index
            mixin_urls = data['mixin']
            mixin_basenames = set()
            for mixin_url in mixin_urls:
                # if mixin URL is relative prefix the dirname of the index
                if (
                    '://' not in mixin_url and
                    not os.path.isabs(mixin_url)
                ):
                    mixin_url = \
                        os.path.dirname(index_url) + '/' + mixin_url

                # fetch the mixin file
                print('  fetching {mixin_url} ...'.format_map(locals()))
                try:
                    content = load_url(mixin_url)
                except Exception as e:
                    print('  -', str(e), file=sys.stderr)
                    rc = 1
                    continue

                # save the mixin file
                mixin_basename = os.path.basename(mixin_url)
                if mixin_basename in mixin_basenames:
                    print('  Multiple mixin files with the same basename '
                          "'{mixin_basename}'".format_map(locals()),
                          file=sys.stderr)
                else:
                    mixin_basenames.add(mixin_basename)

                destination_basepath = get_mixin_path() / name
                os.makedirs(str(destination_basepath), exist_ok=True)
                destination_path = destination_basepath / mixin_basename
                if not destination_path.exists():
                    mod = '+'
                else:
                    if content == destination_path.read_text():
                        mod = '.'
                    else:
                        # IDEA show the diff if the file already exists
                        mod = '*'
                print(' ', mod, str(destination_path))
                with destination_path.open('w') as h:
                    h.write(content)

            # remove / rename obsolete mixin files
            for mixin_file in mixin_files_before:
                if os.path.basename(mixin_file) not in mixin_basenames:
                    os.rename(mixin_file, mixin_file + '.obsolete')
                    print('  - {mixin_file} -> *.obsolete'
                          .format_map(locals()))

        # remove / rename mixin files from obsolete repositories
        obsolete_files = set(get_mixin_files())
        for name in repos.keys():
            obsolete_files -= set(get_repository_mixin_files(
                repository_name=name))
        for mixin_file in sorted(obsolete_files):
            os.rename(mixin_file, mixin_file + '.obsolete')
            print('  - {mixin_file} -> *.obsolete'.format_map(locals()))

        return rc
