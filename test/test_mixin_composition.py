# Copyright 2026 Open Robotics
# Licensed under the Apache License, Version 2.0

import argparse
from collections import defaultdict
from unittest.mock import patch

from colcon_mixin.mixin import resolve_mixin
from colcon_mixin.mixin.mixin_argument import MixinArgumentDecorator
import pytest


def _make_mixins(mixin_dict):
    """Build a mixins_by_verb dict for verb ('build',)."""
    mbv = defaultdict(dict)
    mbv[('build',)] = dict(mixin_dict)
    return mbv


def _make_argument_parser():
    parser = MixinArgumentDecorator(argparse.ArgumentParser())
    subparsers = parser.add_subparsers(dest='verb')
    build = subparsers.add_parser('build')
    build.add_argument('--build-base')
    build.add_argument('--args', nargs='*')
    return parser


def test_resolve_no_composition():
    """Mixin without a 'mixin' key returns its args unchanged."""
    mbv = _make_mixins({
        'debug': {'args': ['--flag-a']},
    })
    result = resolve_mixin(('build',), 'debug', mbv)
    assert result == {'args': ['--flag-a']}


def test_resolve_simple():
    """Mixin referencing another gets the referenced args plus its own."""
    mbv = _make_mixins({
        'base': {'args': ['--flag-a']},
        'composed': {
            'mixin': ['base'],
            'build-base': '/tmp/build',
        },
    })
    result = resolve_mixin(('build',), 'composed', mbv)
    assert result == {
        'args': ['--flag-a'],
        'build-base': '/tmp/build',
    }


def test_resolve_nested_composition():
    """Nested references are flattened recursively before own args apply."""
    mbv = _make_mixins({
        'base': {'args': ['base']},
        'extra': {'args': ['extra']},
        'base-extra': {'mixin': ['base', 'extra']},
        'combined': {
            'mixin': ['base-extra'],
            'args': ['combined'],
        },
    })
    result = resolve_mixin(('build',), 'combined', mbv)
    assert result == {
        'args': ['combined', 'extra', 'base'],
    }


def test_resolve_list_concatenation():
    """List args use prepending order, matching CLI --mixin."""
    mbv = _make_mixins({
        'base': {'args': ['--flag-a']},
        'extra': {
            'mixin': ['base'],
            'args': ['--flag-b'],
        },
    })
    result = resolve_mixin(('build',), 'extra', mbv)
    # own args go first, matching _update_args behavior
    assert result == {
        'args': ['--flag-b', '--flag-a'],
    }


def test_resolve_scalar_own_overrides_ref():
    """Own scalar args override referenced mixin's scalar args."""
    mbv = _make_mixins({
        'base': {'build-base': '/tmp/base'},
        'override': {
            'mixin': ['base'],
            'build-base': '/tmp/override',
        },
    })
    result = resolve_mixin(('build',), 'override', mbv)
    assert result == {'build-base': '/tmp/override'}


def test_resolve_scalar_first_ref_wins():
    """Between references, first scalar wins (matches CLI behavior)."""
    mbv = _make_mixins({
        'a': {'build-base': '/from-a'},
        'b': {'build-base': '/from-b'},
        'composed': {'mixin': ['a', 'b']},
    })
    result = resolve_mixin(('build',), 'composed', mbv)
    assert result == {'build-base': '/from-a'}


def test_resolve_cycle_detection():
    """Cyclic references raise RuntimeError."""
    mbv = _make_mixins({
        'a': {'mixin': ['b'], 'x': 1},
        'b': {'mixin': ['a'], 'y': 2},
    })
    with pytest.raises(RuntimeError, match='Cycle detected'):
        resolve_mixin(('build',), 'a', mbv)


def test_resolve_missing_reference():
    """Reference to a non-existent mixin raises RuntimeError."""
    mbv = _make_mixins({
        'broken': {'mixin': ['nonexistent']},
    })
    with pytest.raises(RuntimeError, match='does not exist'):
        resolve_mixin(('build',), 'broken', mbv)


@pytest.mark.parametrize(
    ('mixin_def', 'error_match'),
    [
        ({'mixin': 'base'}, 'expected a list'),
        ({'mixin': ['base', 1]}, 'non-string entry'),
    ],
)
def test_resolve_invalid_mixin_definition(mixin_def, error_match):
    """Malformed 'mixin' definitions raise a RuntimeError."""
    mbv = _make_mixins({
        'broken': mixin_def,
    })
    with pytest.raises(RuntimeError, match=error_match):
        resolve_mixin(('build',), 'broken', mbv)


@patch('colcon_mixin.mixin.mixin_argument.get_mixins')
def test_parse_args_with_composed_mixin(get_mixins):
    """Parser integration applies composed mixins before explicit CLI args."""
    get_mixins.return_value = _make_mixins({
        'base': {
            'build-base': '/tmp/base',
            'args': ['base'],
        },
        'extra': {'args': ['extra']},
        'combo': {'mixin': ['base', 'extra']},
    })
    parser = _make_argument_parser()

    args = parser.parse_args([
        'build',
        '--mixin', 'combo',
        '--build-base', '/tmp/cli',
        '--args', 'cli',
    ])

    assert args.build_base == '/tmp/cli'
    assert args.args == ['extra', 'base', 'cli']


@pytest.mark.parametrize(
    ('mixin_name', 'mixins', 'error_match'),
    [
        (
            'broken-type',
            {
                'broken-type': {'mixin': 'base'},
                'base': {'args': ['base']},
            },
            'expected a list',
        ),
        (
            'missing-ref',
            {'missing-ref': {'mixin': ['missing']}},
            'does not exist',
        ),
        (
            'cycle-a',
            {
                'cycle-a': {'mixin': ['cycle-b']},
                'cycle-b': {'mixin': ['cycle-a']},
            },
            'Cycle detected',
        ),
    ],
)
@patch('colcon_mixin.mixin.mixin_argument.get_mixins')
def test_parse_args_reports_composition_errors(
    get_mixins, mixin_name, mixins, error_match
):
    """Parser errors surface malformed composition definitions cleanly."""
    get_mixins.return_value = _make_mixins(mixins)
    parser = _make_argument_parser()

    with patch.object(
        parser._parser,
        'error',
        side_effect=lambda message: (_ for _ in ()).throw(
            RuntimeError(message)),
    ):
        with pytest.raises(RuntimeError, match=error_match):
            parser.parse_args(['build', '--mixin', mixin_name])
