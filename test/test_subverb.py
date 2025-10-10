# Copyright 2025 Leander Stephen Desouza
# Licensed under the Apache License, Version 2.0

from argparse import ArgumentTypeError
from pathlib import Path
from unittest.mock import Mock

from colcon_core.command import CommandContext
from colcon_core.location import set_default_config_path
import pytest

set_default_config_path(path=Path('/tmp/colcon_mixin_test'))

# Import colcon-mixin modules after config path is set
# flake8: noqa: E402
from colcon_mixin.mixin.repository import set_repositories
from colcon_mixin.subverb.add import (_non_empty_string_without_pathsep,
                                      _url_string, AddMixinSubverb)
from colcon_mixin.subverb.remove import RemoveMixinSubverb
from colcon_mixin.subverb.show import ShowMixinSubverb
from colcon_mixin.subverb.update import UpdateMixinSubverb


MIXIN_IDENTIFIER = 'demo'
TEST_URL = Path(__file__).parent.joinpath('index.yaml').absolute().as_uri()


@pytest.fixture(autouse=True)
def mixin_cleanup():
    """Cleanup mixin repositories before and after each test."""
    set_repositories({})
    yield
    set_repositories({})


def test_add_success():
    """Test successfully adding a mixin repository."""
    extension = AddMixinSubverb()
    context = CommandContext(command_name='colcon', args=Mock())

    context.args.name = MIXIN_IDENTIFIER
    context.args.url = TEST_URL

    result = extension.main(context=context)
    assert result is None


def test_add_repository_duplicate_name():
    """Test adding a repository with a name that already exists."""
    extension = AddMixinSubverb()

    context1 = CommandContext(command_name='colcon', args=Mock())
    context1.args.name = MIXIN_IDENTIFIER
    context1.args.url = TEST_URL
    result1 = extension.main(context=context1)
    assert result1 is None

    # Second add (duplicate)
    context2 = CommandContext(command_name='colcon', args=Mock())
    context2.args.name = MIXIN_IDENTIFIER
    context2.args.url = TEST_URL
    result2 = extension.main(context=context2)
    assert result2 == (
        f"A repository with the name '{MIXIN_IDENTIFIER}' already exists"
    )


def test_add_repository_invalid_url():
    """Test adding a repository with an invalid URL format."""
    with pytest.raises(ArgumentTypeError, match="must contain '://'"):
        _url_string('invalid-url')


def test_add_repository_invalid_name():
    """Test adding a repository with an invalid name."""
    # Forward slash test
    with pytest.raises(ArgumentTypeError, match="must not contain '/'"):
        _non_empty_string_without_pathsep(f'{MIXIN_IDENTIFIER}/invalid')

    # Backslash test
    with pytest.raises(ArgumentTypeError, match="must not contain '\\\\'"):
        _non_empty_string_without_pathsep(f'{MIXIN_IDENTIFIER}\\invalid')


def test_update_mixin(capsys):
    """Test updating a mixin repository."""
    add_extension = AddMixinSubverb()
    add_context = CommandContext(command_name='colcon', args=Mock())
    add_context.args.name = MIXIN_IDENTIFIER
    add_context.args.url = TEST_URL
    add_extension.main(context=add_context)

    update_extension = UpdateMixinSubverb()
    update_context = CommandContext(command_name='colcon', args=Mock())
    update_context.args.name = MIXIN_IDENTIFIER

    result = update_extension.main(context=update_context)
    captured = capsys.readouterr()

    assert result == 0
    assert f'fetching {MIXIN_IDENTIFIER}:' in captured.out
    assert 'build-type.mixin' in captured.out
    assert 'coverage.mixin' in captured.out


def test_show_mixins(capsys):
    """Test showing available mixins against expected files."""
    add_extension = AddMixinSubverb()
    add_context = CommandContext(command_name='colcon', args=Mock())
    add_context.args.name = MIXIN_IDENTIFIER
    add_context.args.url = TEST_URL
    add_extension.main(context=add_context)

    update_extension = UpdateMixinSubverb()
    update_context = CommandContext(command_name='colcon', args=Mock())
    update_context.args.name = MIXIN_IDENTIFIER
    update_extension.main(context=update_context)

    # Clear previous output from add/update
    capsys.readouterr()

    show_extension = ShowMixinSubverb()
    show_extension.add_arguments(parser=Mock())  # Initialize mixins_by_verb
    show_context = CommandContext(command_name='colcon', args=Mock())

    # Show all verbs and all mixins
    show_context.args.verb = None
    show_context.args.mixin_name = None

    result = show_extension.main(context=show_context)
    captured = capsys.readouterr()

    assert result is None

    expected_demo_file = Path(__file__).parent.joinpath('expected_mixins', 'demo.txt')
    with expected_demo_file.open('r', encoding='utf-8') as f:
        expected_content = f.read().strip()

    assert captured.out.strip() == expected_content


def test_remove_repository_success():
    """Test successfully removing a mixin repository."""
    add_extension = AddMixinSubverb()
    add_context = CommandContext(command_name='colcon', args=Mock())
    add_context.args.name = MIXIN_IDENTIFIER
    add_context.args.url = TEST_URL
    add_extension.main(context=add_context)

    remove_extension = RemoveMixinSubverb()
    remove_context = CommandContext(command_name='colcon', args=Mock())
    remove_context.args.name = MIXIN_IDENTIFIER

    result = remove_extension.main(context=remove_context)
    assert result is None


def test_remove_repository_not_exists():
    """Test removing a repository that doesn't exist."""
    extension = RemoveMixinSubverb()
    context = CommandContext(command_name='colcon', args=Mock())
    context.args.name = MIXIN_IDENTIFIER

    result = extension.main(context=context)
    assert result == (
        f"A repository with the name '{MIXIN_IDENTIFIER}' doesn't exist"
    )
