"""Config flow happy-path tests (unit, no HA runtime)."""

from custom_components.dotnl_chargers.config_flow import _unique_id
from custom_components.dotnl_chargers.const import DOMAIN


def test_unique_id_rounding():
    uid = _unique_id(52.0907123, 5.1214567, 2.0)
    assert uid == f"{DOMAIN}_52.0907_5.1215_2.00"
    # Same rounded values collide
    assert _unique_id(52.09074, 5.12145, 2.0) == uid


def test_unique_id_different_radius():
    a = _unique_id(52.09, 5.12, 2.0)
    b = _unique_id(52.09, 5.12, 5.0)
    assert a != b
