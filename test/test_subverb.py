# Copyright 2025 Leander Stephen Desouza
# Licensed under the Apache License, Version 2.0

"""Integration tests for colcon mixin."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

MIXIN_IDENTIFIER = 'demo'

if sys.platform == 'win32':
    HOME = 'USERPROFILE'
else:
    HOME = 'HOME'


class TestMixinSubverbs:
    """Test the colcon mixin subverbs."""

    def setup_method(self):
        """Set up test environment."""
        test_index_path = Path(__file__).parent / 'index.yaml'
        self.test_url = test_index_path.absolute().as_uri()

        self.original_home = os.environ.get(HOME, '')

        # Override HOME to point to the temporary directory
        self.temp_dir = tempfile.mkdtemp(suffix='_colcon_mixin_test')
        os.environ[HOME] = self.temp_dir

    def teardown_method(self):
        """Clean up test environment."""
        # Restore original home
        os.environ[HOME] = self.original_home
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_colcon_command(self, args):
        """Run a colcon mixin command and return the result."""
        cmd = [sys.executable, '-m', 'colcon', 'mixin'] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            check=False
        )
        return result

    def test_add_success(self):
        """Test successfully adding a mixin repository."""
        result = self.run_colcon_command(
            ['add', MIXIN_IDENTIFIER, self.test_url])

        assert result.returncode == 0
        assert result.stderr == ''

    def test_add_repository_invalid_url(self):
        """Test adding a repository with an invalid URL format."""
        result = self.run_colcon_command(
            ['add', MIXIN_IDENTIFIER, 'invalid-url'])
        assert result.returncode != 0
        assert "must contain '://'" in result.stderr

    def test_add_repository_invalid_name(self):
        """Test adding a repository with an invalid name."""
        # Forward slash test
        result1 = self.run_colcon_command(
            ['add', f'{MIXIN_IDENTIFIER}/invalid', self.test_url])
        assert result1.returncode != 0
        assert "must not contain '/'" in result1.stderr

        # Backslash test
        result2 = self.run_colcon_command(
            ['add', f'{MIXIN_IDENTIFIER}\\invalid', self.test_url])
        assert result2.returncode != 0
        assert "must not contain '\\'" in result2.stderr

    def test_add_repository_duplicate_name(self):
        """Test adding a repository with a name that already exists."""
        result1 = self.run_colcon_command(
            ['add', MIXIN_IDENTIFIER, self.test_url])
        assert result1.returncode == 0

        result2 = self.run_colcon_command(
            ['add', MIXIN_IDENTIFIER, self.test_url])
        assert result2.returncode != 0
        assert ("A repository with the name 'demo' "
                'already exists') in result2.stderr

    def test_update_mixin(self):
        """Test updating a mixin repository."""
        result1 = self.run_colcon_command(
            ['add', MIXIN_IDENTIFIER, self.test_url])
        assert result1.returncode == 0

        result2 = self.run_colcon_command(['update', MIXIN_IDENTIFIER])
        assert result2.returncode == 0
        assert f'fetching {MIXIN_IDENTIFIER}:' in result2.stdout
        assert 'build-type.mixin' in result2.stdout
        assert 'coverage.mixin' in result2.stdout

    def test_show_mixins(self):
        """Test showing available mixins against expected files."""
        self.run_colcon_command(['add', MIXIN_IDENTIFIER, self.test_url])
        self.run_colcon_command(['update', MIXIN_IDENTIFIER])

        expected_demo_mixin = \
            Path(__file__).parent / 'expected_mixins' / 'demo.txt'
        with expected_demo_mixin.open('r') as f:
            expected_content = f.read().strip()

        result = self.run_colcon_command(['show'])
        assert result.returncode == 0
        assert result.stdout.strip() == expected_content

    def test_remove_repository_success(self):
        """Test successfully removing a mixin repository."""
        result1 = self.run_colcon_command(
            ['add', MIXIN_IDENTIFIER, self.test_url])
        assert result1.returncode == 0

        result2 = self.run_colcon_command(['remove', MIXIN_IDENTIFIER])
        assert result2.returncode == 0

    def test_remove_repository_not_exists(self):
        """Test removing a repository that doesn't exist."""
        result = self.run_colcon_command(['remove', MIXIN_IDENTIFIER])
        assert result.returncode != 0
        assert (f"A repository with the name '{MIXIN_IDENTIFIER}' "
                "doesn't exist") in result.stderr
