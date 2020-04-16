# Copyright 2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import argparse
import os
from pathlib import Path

from colcon_core.argument_default import is_default_value
from colcon_core.argument_default import unwrap_default_value
from colcon_core.argument_default import wrap_default_value
from colcon_core.argument_parser import ArgumentParserDecoratorExtensionPoint
from colcon_core.argument_parser import SuppressUsageOutput
from colcon_core.argument_parser.destination_collector \
    import DestinationCollectorDecorator
from colcon_core.logging import colcon_logger
from colcon_core.plugin_system import satisfies_version
from colcon_mixin.mixin import add_mixins
from colcon_mixin.mixin import get_mixins

logger = colcon_logger.getChild(__name__)


class MixinArgumentParserDecorator(
    ArgumentParserDecoratorExtensionPoint
):
    """Mixin argument for every verb."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            ArgumentParserDecoratorExtensionPoint.EXTENSION_POINT_VERSION,
            '^1.0')

    def decorate_argument_parser(self, *, parser):  # noqa: D102
        return MixinArgumentDecorator(parser)


# verbs which should not get the mixin arguments injected
VERB_BLACKLIST = {
    ('metadata', ),  # also matching all subverbs of metadata
    ('mixin', ),  # also matching all subverbs of mixin
}


class MixinArgumentDecorator(DestinationCollectorDecorator):
    """Inject a mixin argument to every verb with completion."""

    def __init__(self, parser):  # noqa: D107
        # avoid setting members directly, the base class overrides __setattr__
        # pass them as keyword arguments instead
        super().__init__(
            parser,
            _parsers={},
            _subparsers=[])

    def add_parser(self, *args, **kwargs):
        """Collect association of parsers to their name."""
        parser = super().add_parser(*args, **kwargs)
        self._parsers[args[0]] = parser
        return parser

    def add_subparsers(self, *args, **kwargs):
        """Collect all subparsers."""
        subparser = super().add_subparsers(*args, **kwargs)
        self._subparsers.append(subparser)
        return subparser

    def add_argument(self, *args, **kwargs):
        """Wrap default value in a custom class."""
        if 'default' in kwargs:
            default_value = kwargs['default']
            kwargs['default'] = _custom_wrap_default_value(default_value)
        # For store_`bool`, the default is the negation
        elif kwargs.get('action') == 'store_true':
            kwargs['default'] = _custom_wrap_default_value(False)
        elif kwargs.get('action') == 'store_false':
            kwargs['default'] = _custom_wrap_default_value(True)
        return super().add_argument(*args, **kwargs)

    def set_defaults(self, **kwargs):
        """Wrap default values in a custom class."""
        return self._parser.set_defaults(
            **{k: _custom_wrap_default_value(v) for (k, v) in kwargs.items()})

    def parse_known_args(self, *args, **kwargs):
        """Unwrap default values."""
        known_args, remaining_args = self._parser.parse_known_args(
            *args, **kwargs)
        # undo default value wrapping injected in the add_argument() method
        for k, v in known_args.__dict__.items():
            if is_default_value(v):
                setattr(known_args, k, _custom_unwrap_default_value(v))
        return (known_args, remaining_args)

    def parse_args(self, *args, **kwargs):
        """Add mixin argument for each parser."""
        global VERB_BLACKLIST

        # mapping of all "leaf" verbs to parsers
        def collect_parsers_by_verb(root, parsers, parent_verbs=()):
            found_any = False
            for sp in root._subparsers:
                for name, p in sp._parsers.items():
                    verbs = parent_verbs + (name, )
                    found_children = collect_parsers_by_verb(p, parsers, verbs)
                    # only add verbs which don't have subverbs
                    if not found_children:
                        parsers[verbs] = p
                        found_any = True
            return found_any
        parsers = {}
        collect_parsers_by_verb(self, parsers)

        mixins_by_verb = get_mixins()

        # add mixin arguments to these parsers
        # doing this here instead of in the add_parser() method makes sure
        # the arguments are documented at the very end of the help message
        groups = {}
        for k, p in parsers.items():
            # match all slices starting from index 0 of k against the blacklist
            # e.g. k=(a,b,c) it checks against (a), (a,b), (a,b,c)
            k_prefixes = {k[0:l] for l in range(1, len(k) + 1)}
            if not k_prefixes & VERB_BLACKLIST:
                groups[p] = self._add_mixin_argument_group(p)

        # add dummy --mixin argument to prevent parse_known_args to interpret
        # --mixin arguments as --mixin-files
        mixin_arguments = {}
        for verb, p in parsers.items():
            if p in groups:
                mixin_arguments[verb] = self._add_mixin_argument(
                    p, groups[p], verb)

        with SuppressUsageOutput([self._parser] + list(parsers.values())):
            known_args, _ = self._parser.parse_known_args(*args, **kwargs)

        for mixin_file in (getattr(known_args, 'mixin_files', None) or []):
            # add mixins from explicitly provided file
            add_mixins(Path(mixin_file), mixins_by_verb)

        # update the --mixin argument help and completer with available mixins
        for verb, argument in mixin_arguments.items():
            self._update_mixin_argument(argument, mixins_by_verb.get(verb, {}))

        args = self._parser.parse_args(*args, **kwargs)

        # update args based on selected mixins
        if 'mixin_verb' in args:
            mixins = mixins_by_verb.get(args.mixin_verb, {})
            for mixin in args.mixin or ():
                if mixin not in mixins:
                    context = '.'.join(args.mixin_verb)
                    logger.warning(
                        "Mixin '{mixin}' is not available for '{context}'"
                        .format_map(locals()))
                    continue
                mixin_args = mixins[mixin]
                logger.debug(
                    "Using mixin '{mixin}': {mixin_args}".format_map(locals()))
                self._update_args(args, mixin_args, '.'.join(args.mixin_verb))

        # undo default value wrapping injected in the add_argument() method
        for k, v in args.__dict__.items():
            if is_default_value(v):
                setattr(args, k, _custom_unwrap_default_value(v))

        return args

    def _add_mixin_argument_group(self, parser):
        group = parser.add_argument_group(
            title='Mixin predefined sets of command line parameters')

        argument = group.add_argument(
            '--mixin-files', nargs='*', metavar='FILE',
            type=_argparse_existing_file,
            help='Additional files providing mixins')
        try:
            from argcomplete.completers import FilesCompleter
        except ImportError:
            pass
        else:
            argument.completer = FilesCompleter(['mixin'])

        return group

    def _add_mixin_argument(self, parser, group, verb):
        # the help and completer are skipped for now
        # they are updated later in _update_mixin_argument
        argument = group.add_argument(
            '--mixin', nargs='*', metavar=('mixin1', 'mixin2'))

        # makes the used verb available to choose the corresponding mixins
        parser.set_defaults(mixin_verb=verb)

        return argument

    def _update_mixin_argument(self, argument, mixins):
        descriptions = ''
        for key in sorted(mixins.keys()):
            args = mixins[key]
            # it requires a custom formatter to maintain the newline
            descriptions += '\n* {key}:'.format_map(locals())
            for k, v in args.items():
                descriptions += '\n  - {k}: {v}'.format_map(locals())

        if descriptions:
            descriptions = 'The following mixins are available:' + descriptions
        else:
            descriptions = 'No mixins are available for this verb'
        argument.help = descriptions

        try:
            from argcomplete.completers import ChoicesCompleter
        except ImportError:
            pass
        else:
            argument.completer = ChoicesCompleter(mixins.keys())

    def _update_args(self, args, mixin_args, context):
        destinations = self.get_destinations()
        for mixin_key, mixin_value in mixin_args.items():
            if mixin_key not in destinations:
                logger.warning(
                    "Mixin key '{mixin_key}' is not a valid argument for "
                    "'{context}'".format_map(locals()))
                continue

            arg_key = destinations[mixin_key]
            arg_value = getattr(args, arg_key)
            if arg_value is None or is_default_value(arg_value):
                logger.debug(
                    "Replacing default value of '{arg_key}' with mixin value: "
                    '{mixin_value}'.format_map(locals()))
                setattr(args, arg_key, mixin_value)
            elif isinstance(arg_value, list):
                combined_value = mixin_value + arg_value
                logger.debug(
                    "Updating argument '{arg_key}' by prepending mixin value "
                    "'{mixin_value}' to command line argument "
                    "'{arg_value}'".format_map(locals()))
                setattr(args, arg_key, combined_value)
            else:
                logger.debug(
                    "Skipping mixin key '{mixin_key}' which was passed "
                    'explicitly as a command line argument'
                    .format_map(locals()))


def _custom_wrap_default_value(value):
    try:
        value = wrap_default_value(value)
    except ValueError:
        # avoid double wrapping and mark those default value to not unwrap them
        value._mixin_argument_already_default_value = True
    return value


def _custom_unwrap_default_value(value):
    assert is_default_value(value)
    try:
        delattr(value, '_mixin_argument_already_default_value')
        # don't unwrap default values which haven't been wrapped by
        # _custom_wrap_default_value
    except AttributeError:
        value = unwrap_default_value(value)
    return value


def _argparse_existing_file(path):
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(
            "Path '{path}' does not exist".format_map(locals()))
    if not os.path.isfile(path):
        raise argparse.ArgumentTypeError(
            "Path '{path}' is not a file".format_map(locals()))
    return path
