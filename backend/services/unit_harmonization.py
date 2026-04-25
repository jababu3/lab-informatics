import pint
import logging

logger = logging.getLogger(__name__)

# Initialize the pint registry globally
ureg = pint.UnitRegistry()

# Add a few common biochemical aliases if needed
ureg.define("Molar = 1 * mole / liter = M")


def standardize_concentration(
    value: float, unit_str: str, target_unit: str = "uM"
) -> dict:
    """
    Takes a raw numeric value and a unit string (e.g. 150, "nM") and converts it to a standard unit (default uM).
    Returns a dictionary with the canonical harmonized data.
    """
    try:
        # Construct the pint Quantity
        quantity = value * ureg(unit_str)

        # Check if it is a concentration (amount / volume)
        if not quantity.check("[substance]/[volume]"):
            raise ValueError(f"Unit '{unit_str}' is not a valid concentration.")

        # Perform the conversion
        harmonized = quantity.to(target_unit)

        return {
            "original_value": value,
            "original_unit": unit_str,
            "harmonized_value": round(float(harmonized.magnitude), 6),
            "harmonized_unit": target_unit,
        }
    except pint.errors.UndefinedUnitError as e:
        logger.error(f"Undefined unit passed to harmonize: {e}")
        raise ValueError(f"Unknown scientific unit: {unit_str}")
    except Exception as e:
        logger.error(f"Error harmonizing unit {value} {unit_str}: {e}")
        raise ValueError(f"Failed to harmonize: {str(e)}")
