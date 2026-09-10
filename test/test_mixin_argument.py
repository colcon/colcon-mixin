# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

import argparse
from unittest.mock import patch

from colcon_mixin.mixin.mixin_argument import MixinArgumentDecorator
import pytest

MIXINS = {
    'a': {'cmake-args': ['FOO=A']},
    'b': {'cmake-args': ['FOO=B']},
    'c': {'cmake-args': ['FOO=C']},
}


SCALAR_MIXINS = {
    'a': {'build-base': 'BASE_A'},
    'b': {'build-base': 'BASE_B'},
}


NESTED_MIXINS = {
    'base': {'cmake-args': ['FOO=BASE']},
    'child': {'mixin': ['base'], 'cmake-args': ['FOO=CHILD']},
}


SCALAR_NESTED_MIXINS = {
    'base': {'build-base': 'BASE'},
    'child': {'mixin': ['base'], 'build-base': 'CHILD'},
}


CANONICAL_MIXINS = {
    'A': {'mixin': ['B', 'D'], 'cmake-args': ['A']},
    'B': {'mixin': ['C'], 'cmake-args': ['B']},
    'C': {'mixin': ['D'], 'cmake-args': ['C']},
    'D': {'cmake-args': ['D']},
}


def _parse(argv, mixins=MIXINS):
    base = argparse.ArgumentParser(prog='colcon')
    decorator = MixinArgumentDecorator(base)
    subparsers = decorator.add_subparsers(dest='verb')
    build = subparsers.add_parser('build')
    build.add_argument('--cmake-args', nargs='*', default=[])
    build.add_argument('--build-base', default='build')
    mixins_by_verb = {('build',): mixins}
    with patch(
        'colcon_mixin.mixin.mixin_argument.get_mixins',
        return_value=mixins_by_verb,
    ):
        return decorator.parse_args(argv)


def test_multiple_mixins_preserve_command_line_order():
    # order the mixins were given on the command line
    args = _parse(['build', '--mixin', 'a', 'b'])
    assert args.cmake_args == ['FOO=A', 'FOO=B']


def test_multiple_mixins_follow_reversed_selection():
    args = _parse(['build', '--mixin', 'b', 'a'])
    assert args.cmake_args == ['FOO=B', 'FOO=A']


def test_three_mixins_preserve_order():
    args = _parse(['build', '--mixin', 'a', 'b', 'c'])
    assert args.cmake_args == ['FOO=A', 'FOO=B', 'FOO=C']


def test_command_line_arguments_take_precedence():
    # explicit command line arguments must come last so they win
    args = _parse(['build', '--mixin', 'a', 'b', '--cmake-args=FOO=CLI'])
    assert args.cmake_args == ['FOO=A', 'FOO=B', 'FOO=CLI']


def test_single_mixin():
    args = _parse(['build', '--mixin', 'a'])
    assert args.cmake_args == ['FOO=A']


def test_no_mixin():
    args = _parse(['build'])
    assert args.cmake_args == []


def test_scalar_last_listed_mixin_wins():
    # a scalar value from a later mixin must override an earlier one
    args = _parse(['build', '--mixin', 'a', 'b'], SCALAR_MIXINS)
    assert args.build_base == 'BASE_B'


def test_scalar_reversed_selection():
    args = _parse(['build', '--mixin', 'b', 'a'], SCALAR_MIXINS)
    assert args.build_base == 'BASE_A'


def test_scalar_command_line_argument_take_precedence():
    args = _parse(
        ['build', '--mixin', 'a', 'b', '--build-base', 'CLI'], SCALAR_MIXINS)
    assert args.build_base == 'CLI'


def test_unavailable_mixin_reports_first(capsys):
    with pytest.raises(SystemExit):
        _parse(['build', '--mixin', 'bad', 'a'])
    assert "Mixin 'bad' is not available" in capsys.readouterr().err


def test_referenced_mixin_applied_before_referencing():
    args = _parse(['build', '--mixin', 'child'], NESTED_MIXINS)
    assert args.cmake_args == ['FOO=BASE', 'FOO=CHILD']


def test_referencing_mixin_overrides_referenced_scalar():
    args = _parse(['build', '--mixin', 'child'], SCALAR_NESTED_MIXINS)
    assert args.build_base == 'CHILD'


def test_canonical_reference_graph_order():
    # D appears twice, once per path
    args = _parse(['build', '--mixin', 'A'], CANONICAL_MIXINS)
    assert args.cmake_args == ['D', 'C', 'B', 'D', 'A']


def test_nested_mixin_command_line_arguments_take_precedence():
    args = _parse(
        ['build', '--mixin', 'child', '--cmake-args=FOO=CLI'], NESTED_MIXINS)
    assert args.cmake_args == ['FOO=BASE', 'FOO=CHILD', 'FOO=CLI']


def test_circular_mixin_reference_reports_error(capsys):
    mixins = {
        'a': {'mixin': ['b']},
        'b': {'mixin': ['a']},
    }
    with pytest.raises(SystemExit):
        _parse(['build', '--mixin', 'a'], mixins)
    assert 'Circular mixin reference' in capsys.readouterr().err


def test_unknown_referenced_mixin_reports_error(capsys):
    mixins = {'a': {'mixin': ['missing']}}
    with pytest.raises(SystemExit):
        _parse(['build', '--mixin', 'a'], mixins)
    assert "unknown mixin 'missing'" in capsys.readouterr().err
