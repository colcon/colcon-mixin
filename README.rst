colcon-mixin
============

An extension for `colcon-core <https://github.com/colcon/colcon-core>`_ to fetch and manage CLI mixins from repositories.

For an example repository containing mixins see `colcon-mixin-repository <https://github.com/colcon/colcon-mixin-repository>`_.

Argument Priority
-----------------

colcon applies arguments in this order, where each level overrides the previous:

1. ``defaults.yaml`` — lowest priority
2. Mixins
3. Command line arguments — highest priority

Note: list-type arguments like ``cmake-args`` are replaced entirely, not merged.
To preserve defaults, just define them inside a mixin instead
