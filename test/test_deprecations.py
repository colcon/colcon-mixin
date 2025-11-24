# Copyright 2025 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from pathlib import Path
import sys
from unittest.mock import patch

import pytest


def test_verb_blacklist():
    if sys.version_info < (3, 7):
        # Older Python doesn't support the syntax to emit this warning
        from colcon_mixin.mixin.mixin_argument \
            import VERB_BLACKLIST  # noqa: F401
    else:
        with pytest.warns(UserWarning, match='deprecated'):
            from colcon_mixin.mixin.mixin_argument \
                import VERB_BLACKLIST  # noqa: F401

        with pytest.warns(UserWarning, match='deprecated'):
            import colcon_mixin.mixin.mixin_argument
            colcon_mixin.mixin.mixin_argument.VERB_BLACKLIST

    with pytest.raises(ImportError):
        from colcon_mixin.mixin.mixin_argument \
            import does_not_exist  # noqa: F401


@patch('colcon_mixin.mixin.repository.get_config_path', Path.cwd)
def test_mixin_repositories_file():
    if sys.version_info < (3, 7):
        # Older Python doesn't support the syntax to emit this warning
        from colcon_mixin.mixin.repository \
            import mixin_repositories_file  # noqa: F401
    else:
        with pytest.warns(UserWarning, match='deprecated'):
            from colcon_mixin.mixin.repository \
                import mixin_repositories_file  # noqa: F401

        with pytest.warns(UserWarning, match='deprecated'):
            import colcon_mixin.mixin.repository
            colcon_mixin.mixin.repository.mixin_repositories_file

    with pytest.raises(ImportError):
        from colcon_mixin.mixin.repository \
            import does_not_exist  # noqa: F401

    with pytest.raises(AttributeError, match='has no attribute'):
        import colcon_mixin.mixin.repository
        colcon_mixin.mixin.repository.does_not_exist
