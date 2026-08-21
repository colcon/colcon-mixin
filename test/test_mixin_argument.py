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
