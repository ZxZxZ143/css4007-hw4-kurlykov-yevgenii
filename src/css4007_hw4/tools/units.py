from css4007_hw4.domain.errors import ToolError
from css4007_hw4.tools.validation import checked_number

# Dimension and multiplier into its base unit.
UNITS = {"m": ("length", 1.0), "km": ("length", 1000.0),
         "m2": ("area", 1.0), "km2": ("area", 1_000_000.0),
         "L": ("volume", 1.0), "m3": ("volume", 1000.0), "ML": ("volume", 1_000_000.0),
         **{u: (u, 1.0) for u in ("one", "KZT", "person", "pupil", "school")}}
SCALES = {"one": 1.0, "thousand": 1000.0, "million": 1_000_000.0}


def convert(value: float, from_unit: str, to_unit: str, scale: str = "one") -> float:
    if not isinstance(scale, str) or scale not in SCALES:
        raise ToolError("INVALID_ARGUMENTS", "scale must be one, thousand or million.")
    if not isinstance(from_unit, str) or not isinstance(to_unit, str):
        raise ToolError("INVALID_ARGUMENTS", "Unit labels must be strings.")
    if from_unit not in UNITS or to_unit not in UNITS:
        raise ToolError("UNSUPPORTED_UNIT", "Unsupported unit; use one of the documented case-sensitive labels.")
    source, destination = UNITS[from_unit], UNITS[to_unit]
    if source[0] != destination[0]:
        raise ToolError("INCOMPATIBLE_UNITS", "Source and target units have different dimensions or count labels.")
    scaled = checked_number(checked_number(value) * SCALES[scale])
    # Direct ratio avoids an unnecessary large intermediate in base units.
    return checked_number(scaled * (source[1] / destination[1]))
