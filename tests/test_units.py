import pytest

from css4007_hw4.tools.calculate import calculate


@pytest.mark.parametrize("value,source,target,scale,expected", [
    (1, "KZT", "KZT", "million", 1_000_000), (2.5, "ML", "m3", "one", 2500),
    (2_151_400, "m3", "L", "one", 2_151_400_000), (2500, "m3", "ML", "one", 2.5),
    (2, "km", "m", "one", 2000), (1, "km2", "m2", "one", 1e6),
    (1, "pupil", "pupil", "thousand", 1000), (1, "one", "one", "one", 1),
    (1000, "m", "km", "one", 1), (1e6, "m2", "km2", "one", 1)])
def test_conversion(value, source, target, scale, expected):
    result = calculate(mode="convert", value=value, from_unit=source, to_unit=target, scale=scale)
    assert result["ok"] and result["value"] == expected and result["unit"] == target


@pytest.mark.parametrize("source,target,code", [("m3", "KZT", "INCOMPATIBLE_UNITS"),
                                                ("school", "person", "INCOMPATIBLE_UNITS"),
                                                ("USD", "KZT", "UNSUPPORTED_UNIT"),
                                                ("km/person", "km", "UNSUPPORTED_UNIT"),
                                                ("ml", "ML", "UNSUPPORTED_UNIT")])
def test_units_rejected(source, target, code):
    assert calculate(mode="convert", value=1, from_unit=source, to_unit=target)["error"]["code"] == code


@pytest.mark.parametrize("value,scale,code", [(True, "one", "INVALID_ARGUMENTS"), ("5", "one", "INVALID_ARGUMENTS"),
                                            (1, [], "INVALID_ARGUMENTS"), (1e15, "million", "LIMIT_EXCEEDED"),
                                            (float("nan"), "one", "LIMIT_EXCEEDED"),
                                            (float("inf"), "one", "LIMIT_EXCEEDED")])
def test_conversion_validation(value, scale, code):
    assert calculate(mode="convert", value=value, scale=scale, from_unit="KZT", to_unit="KZT")["error"]["code"] == code
