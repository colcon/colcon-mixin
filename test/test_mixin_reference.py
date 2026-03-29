# Demo for mixin referencing 
import pytest
from colcon_mixin.mixin import Mixin

def test_mixin_reference():
    class A(Mixin):
        pass
    class B(Mixin):
        base = A()
    assert isinstance(B.base, A)
