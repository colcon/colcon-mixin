# Copyright 2026 Open Robotics
# Licensed under the Apache License, Version 2.0

from collections import defaultdict

from colcon_mixin.mixin import resolve_mixin
import pytest


def _make_mixins(mixin_dict):
    """Build a mixins_by_verb dict for verb ('build',)."""
    mbv = defaultdict(dict)
    mbv[('build',)] = dict(mixin_dict)
    return mbv


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
