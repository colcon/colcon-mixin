# Copyright 2026 Innocent Pious
# Licensed under the Apache License, Version 2.0

"""Tests for the output of the mixin show subverb."""

import argparse
from unittest.mock import patch

from colcon_mixin.subverb.show import ShowMixinSubverb


REFERENCING_MIXINS = {
    ('build', ): {
        'base': {'cmake-args': ['-DA=1']},
        'debug': {'mixin': ['base'], 'cmake-args': ['-DB=1']},
        'strict': {'mixin': ['debug'], 'cmake-args': ['-DC=1']},
    },
}


PLAIN_MIXINS = {
    ('build', ): {
        'debug': {'cmake-args': ['-DB=1']},
        'release': {'cmake-args': ['-DD=1']},
    },
}


def _show(capsys, mixins_by_verb, verb=None, mixin_name=None):
    with patch(
        'colcon_mixin.subverb.show.get_mixins', return_value=mixins_by_verb
    ):
        extension = ShowMixinSubverb()
        extension.add_arguments(parser=argparse.ArgumentParser())
    context = argparse.Namespace(
        args=argparse.Namespace(verb=verb, mixin_name=mixin_name))
    rc = extension.main(context=context)
    return capsys.readouterr().out.splitlines(), rc


def test_application_order_for_referencing_mixins(capsys):
    lines, rc = _show(capsys, REFERENCING_MIXINS)
    assert rc is None
    assert lines == [
        'build:',
        '- base',
        "  cmake-args: ['-DA=1']",
        '- debug',
        "  mixin: ['base']",
        "  cmake-args: ['-DB=1']",
        '  application order: base -> debug',
        '- strict',
        "  mixin: ['debug']",
        "  cmake-args: ['-DC=1']",
        '  application order: base -> debug -> strict',
    ]


def test_no_application_order_without_references(capsys):
    # mixins which don't reference others are shown as before
    lines, _ = _show(capsys, PLAIN_MIXINS)
    assert lines == [
        'build:',
        '- debug',
        "  cmake-args: ['-DB=1']",
        '- release',
        "  cmake-args: ['-DD=1']",
    ]


def test_no_application_order_for_empty_reference_list(capsys):
    mixins = {('build', ): {'a': {'mixin': [], 'cmake-args': ['-DA=1']}}}
    lines, _ = _show(capsys, mixins)
    assert not any('application order' in line for line in lines)


def test_application_order_for_single_mixin_is_not_indented(capsys):
    lines, _ = _show(
        capsys, REFERENCING_MIXINS, verb='build', mixin_name='strict')
    assert lines == [
        "mixin: ['debug']",
        "cmake-args: ['-DC=1']",
        'application order: base -> debug -> strict',
    ]


def test_application_order_repeats_mixins_reached_twice(capsys):
    mixins = {
        ('build', ): {
            'a': {'mixin': ['b', 'c']},
            'b': {'mixin': ['d']},
            'c': {'mixin': ['d']},
            'd': {},
        },
    }
    lines, _ = _show(capsys, mixins, verb='build', mixin_name='a')
    assert 'application order: d -> b -> d -> c -> a' in lines


def test_missing_reference_is_reported_inline(capsys):
    mixins = {
        ('build', ): {
            'broken': {'mixin': ['nope']},
            'fine': {'cmake-args': ['-DA=1']},
        },
    }
    lines, rc = _show(capsys, mixins)
    assert rc is None
    order_line = [x for x in lines if 'application order' in x][0]
    assert 'unavailable' in order_line
    assert "unknown mixin 'nope'" in order_line
    # the remaining mixins are still being shown
    assert '- fine' in lines


def test_circular_reference_is_reported_inline(capsys):
    mixins = {
        ('build', ): {
            'a': {'mixin': ['b']},
            'b': {'mixin': ['a']},
        },
    }
    lines, rc = _show(capsys, mixins)
    assert rc is None
    assert '  application order: unavailable (Circular mixin reference: ' \
        'a -> b -> a)' in lines


def test_invalid_reference_key_is_reported_inline(capsys):
    mixins = {('build', ): {'a': {'mixin': 'b'}, 'b': {}}}
    lines, rc = _show(capsys, mixins)
    assert rc is None
    order_line = [x for x in lines if 'application order' in x][0]
    assert 'unavailable' in order_line
    assert 'expected a list of strings' in order_line
