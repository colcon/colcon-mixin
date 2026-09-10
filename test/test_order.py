# Copyright 2026 Innocent Pious
# Licensed under the Apache License, Version 2.0

"""Tests for the mixin application-order function."""

from colcon_mixin.mixin.order import CircularMixinError
from colcon_mixin.mixin.order import compute_application_order
from colcon_mixin.mixin.order import InvalidMixinError
from colcon_mixin.mixin.order import MissingMixinError
import pytest


def test_no_mixin_key():
    mixins = {'A': {'cmake-args': ['-DA=1']}}
    assert compute_application_order(mixins, 'A') == ['A']


def test_empty_mixin_list():
    mixins = {'A': {'mixin': [], 'cmake-args': ['-DA=1']}}
    assert compute_application_order(mixins, 'A') == ['A']


def test_single_reference():
    mixins = {
        'A': {'mixin': ['B']},
        'B': {},
    }
    assert compute_application_order(mixins, 'A') == ['B', 'A']


def test_two_references_order_preserved():
    mixins = {
        'A': {'mixin': ['B', 'C']},
        'B': {},
        'C': {},
    }
    assert compute_application_order(mixins, 'A') == ['B', 'C', 'A']


def test_nested_chain():
    mixins = {
        'A': {'mixin': ['B']},
        'B': {'mixin': ['C']},
        'C': {'mixin': ['D']},
        'D': {},
    }
    assert compute_application_order(mixins, 'A') == ['D', 'C', 'B', 'A']


def test_canonical_example():
    mixins = {
        'A': {'mixin': ['B', 'D'], 'cmake-args': ['-DA=1']},
        'B': {'mixin': ['C'], 'cmake-args': ['-DB=1']},
        'C': {'mixin': ['D'], 'cmake-args': ['-DC=1']},
        'D': {'cmake-args': ['-DD=1']},
    }
    assert compute_application_order(mixins, 'A') == \
        ['D', 'C', 'B', 'D', 'A']


def test_diamond_re_application():
    # D is reached through both B and C, so it shows up twice
    mixins = {
        'A': {'mixin': ['B', 'C']},
        'B': {'mixin': ['D']},
        'C': {'mixin': ['D']},
        'D': {},
    }
    order = compute_application_order(mixins, 'A')
    assert order == ['D', 'B', 'D', 'C', 'A']
    assert order.count('D') == 2


def test_self_reference_cycle():
    mixins = {'A': {'mixin': ['A']}}
    with pytest.raises(CircularMixinError) as exc_info:
        compute_application_order(mixins, 'A')
    assert 'A -> A' in str(exc_info.value)


def test_two_node_cycle():
    mixins = {
        'A': {'mixin': ['B']},
        'B': {'mixin': ['A']},
    }
    with pytest.raises(CircularMixinError) as exc_info:
        compute_application_order(mixins, 'A')
    assert 'A -> B -> A' in str(exc_info.value)


def test_three_node_cycle():
    mixins = {
        'A': {'mixin': ['B']},
        'B': {'mixin': ['C']},
        'C': {'mixin': ['A']},
    }
    with pytest.raises(CircularMixinError) as exc_info:
        compute_application_order(mixins, 'A')
    assert 'A -> B -> C -> A' in str(exc_info.value)


def test_missing_referenced_mixin():
    mixins = {'A': {'mixin': ['B']}}
    with pytest.raises(MissingMixinError) as exc_info:
        compute_application_order(mixins, 'A')
    assert "'A'" in str(exc_info.value)
    assert "'B'" in str(exc_info.value)


def test_malformed_mixin_string_not_list():
    mixins = {'A': {'mixin': 'B'}}
    with pytest.raises(InvalidMixinError):
        compute_application_order(mixins, 'A')


def test_malformed_mixin_list_with_non_string():
    mixins = {
        'A': {'mixin': ['B', 1]},
        'B': {},
    }
    with pytest.raises(InvalidMixinError):
        compute_application_order(mixins, 'A')


def test_requested_mixin_not_in_dict():
    mixins = {'A': {}}
    with pytest.raises(MissingMixinError):
        compute_application_order(mixins, 'Z')


def test_mixin_key_never_in_output():
    mixins = {
        'A': {'mixin': ['B', 'D']},
        'B': {'mixin': ['C']},
        'C': {'mixin': ['D']},
        'D': {},
    }
    order = compute_application_order(mixins, 'A')
    assert 'mixin' not in order
    assert set(order) <= set(mixins.keys())
