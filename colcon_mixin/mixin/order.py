# Copyright 2026 Innocent Pious
# Licensed under the Apache License, Version 2.0

"""Compute the order in which mixins referencing other mixins are applied."""


class CircularMixinError(Exception):
    """Raised when the mixin reference graph contains a cycle."""


class MissingMixinError(Exception):
    """Raised when a referenced mixin name does not exist."""


class InvalidMixinError(Exception):
    """Raised when a 'mixin' key is not a list of strings."""


def _read_references(mixins, name):
    refs = mixins[name].get('mixin', [])
    if not isinstance(refs, list) or not all(
        isinstance(ref, str) for ref in refs
    ):
        raise InvalidMixinError(
            "Mixin '{name}' has an invalid 'mixin' key: expected a list of "
            'strings'.format_map(locals()))
    return refs


def compute_application_order(mixins, requested):
    """Return the mixins to apply for a requested mixin, dependencies first.

    A mixin may reference other mixins through a 'mixin' key. References are
    ordered before the mixin that references them (depth-first, post-order),
    so the referencing mixin is applied last and can override them. A mixin
    reached through several paths is applied once per path to keep
    last-applied-wins semantics, so duplicates in the result are intentional.

    :raises CircularMixinError: on a circular reference.
    :raises MissingMixinError: if a referenced mixin does not exist.
    :raises InvalidMixinError: if a 'mixin' key is malformed.
    """
    order = []
    stack_path = []  # names on the active recursion path, for cycle detection

    def visit(name, referrer):
        if name not in mixins:
            if referrer is None:
                raise MissingMixinError(
                    "Requested mixin '{name}' does not exist"
                    .format_map(locals()))
            raise MissingMixinError(
                "Mixin '{referrer}' references unknown mixin '{name}'"
                .format_map(locals()))

        if name in stack_path:
            path = ' -> '.join(stack_path + [name])
            raise CircularMixinError(
                'Circular mixin reference: {path}'.format_map(locals()))

        refs = _read_references(mixins, name)
        stack_path.append(name)
        for ref in refs:
            visit(ref, name)
        stack_path.pop()
        order.append(name)

    visit(requested, None)
    return order
