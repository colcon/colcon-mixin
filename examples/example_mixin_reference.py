# example_mixin_reference.py
from colcon_mixin.mixin import Mixin

class BaseMixin(Mixin):
    pass

class ExtendedMixin(Mixin):
    # This references BaseMixin
    base = BaseMixin()
