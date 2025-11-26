# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from colcon_core.plugin_system import satisfies_version
from colcon_mixin.mixin import get_mixins
from colcon_mixin.subverb import MixinSubverbExtensionPoint
import yaml


def _get_mixin_name_completer(verb_key, mixins_by_verb):
    def mixin_name_completer(prefix, **kwargs):
        """Callable returning a list of mixin names."""
        args = kwargs.get('parsed_args', {})
        verb = getattr(args, verb_key)
        key = tuple(verb.split('.'))
        return mixins_by_verb.get(key, {}).keys()
    return mixin_name_completer


class IndentDumper(yaml.Dumper):
    """Custom YAML dumper with yamllint compliant indentation."""

    def increase_indent(self, flow=False, indentless=False):
        """Override to disable indentless option."""
        return super(IndentDumper, self).increase_indent(flow, False)


class ShowMixinSubverb(MixinSubverbExtensionPoint):
    """Show available mixins and their mapping."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            MixinSubverbExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def add_arguments(self, *, parser):  # noqa: D102
        self.mixins_by_verb = get_mixins()
        argument = parser.add_argument(
            'verb', nargs='?',
            help='Only show the mixins for a specific verb')
        try:
            from argcomplete.completers import ChoicesCompleter
        except ImportError:
            pass
        else:
            argument.completer = \
                ChoicesCompleter(self.mixins_by_verb.keys())
        argument = parser.add_argument(
            'mixin_name', nargs='?',
            help='Only show a specific mixin for a specific verb')
        argument.completer = _get_mixin_name_completer(
            'verb', self.mixins_by_verb)

    def main(self, *, context):  # noqa: D102
        if (
            context.args.verb and
            tuple(context.args.verb.split('.')) not in self.mixins_by_verb
        ):
            return f"Passed verb name '{context.args.verb}' has no mixins"

        output_data = {}

        for verb in sorted(self.mixins_by_verb.keys()):
            if context.args.verb:
                if context.args.verb != '.'.join(verb):
                    continue

            verb_key = '.'.join(verb)
            mixins = self.mixins_by_verb[verb]

            # Filter mixins if specific mixin name is requested
            if context.args.mixin_name:
                if context.args.mixin_name not in mixins:
                    return (
                        f'Passed mixin name "{context.args.mixin_name}"'
                        ' is not defined'
                    )
                output_data[verb_key] = {
                    context.args.mixin_name: mixins[context.args.mixin_name]
                }
            else:
                output_data[verb_key] = mixins

        print(yaml.dump(output_data, Dumper=IndentDumper,
                        sort_keys=True, explicit_start=True), end='')
