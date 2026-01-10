"""
Detailed PyBAMM parameter set configurations.

This module provides comprehensive information about available parameter sets
and their specific parameters for different battery chemistries.

Reference: https://docs.pybamm.org/en/stable/source/api/parameters/parameter_sets.html
"""
from typing import Dict, List, Any, Optional


# =============================================================================
# CHEMISTRY-SPECIFIC DEFAULT PARAMETERS
# These are the key parameters that typically differ between chemistries
# =============================================================================

LFP_DEFAULTS = {
    "description": "Lithium Iron Phosphate (LiFePO4) - safe, long cycle life",
    "typical_parameters": {
        "Nominal cell capacity [A.h]": 2.3,
        "Lower voltage cut-off [V]": 2.5,
        "Upper voltage cut-off [V]": 3.65,
        "Nominal voltage [V]": 3.2,
        "Maximum C-rate": 3.0,
        "Typical cycle life": "2000-5000 cycles",
    },
    "characteristics": {
        "energy_density": "Low-Medium",
        "power_density": "Medium",
        "safety": "Excellent",
        "cost": "Medium",
        "temperature_range": "-20°C to 60°C",
    },
    "recommended_parameter_sets": ["Prada2013"],
}

NMC_DEFAULTS = {
    "description": "Lithium Nickel Manganese Cobalt Oxide - high energy density",
    "typical_parameters": {
        "Nominal cell capacity [A.h]": 5.0,
        "Lower voltage cut-off [V]": 2.5,
        "Upper voltage cut-off [V]": 4.2,
        "Nominal voltage [V]": 3.7,
        "Maximum C-rate": 2.0,
        "Typical cycle life": "1000-2000 cycles",
    },
    "characteristics": {
        "energy_density": "High",
        "power_density": "Medium-High",
        "safety": "Good",
        "cost": "High",
        "temperature_range": "-20°C to 55°C",
    },
    "recommended_parameter_sets": ["Chen2020", "ORegan2022", "Ai2020", "Mohtat2020"],
}

NCA_DEFAULTS = {
    "description": "Lithium Nickel Cobalt Aluminum Oxide - highest energy density",
    "typical_parameters": {
        "Nominal cell capacity [A.h]": 3.5,
        "Lower voltage cut-off [V]": 2.5,
        "Upper voltage cut-off [V]": 4.2,
        "Nominal voltage [V]": 3.6,
        "Maximum C-rate": 2.0,
        "Typical cycle life": "500-1500 cycles",
    },
    "characteristics": {
        "energy_density": "Very High",
        "power_density": "High",
        "safety": "Moderate",
        "cost": "High",
        "temperature_range": "-20°C to 50°C",
    },
    "recommended_parameter_sets": ["NCA_Kim2011"],
}

LCO_DEFAULTS = {
    "description": "Lithium Cobalt Oxide - high energy, consumer electronics",
    "typical_parameters": {
        "Nominal cell capacity [A.h]": 2.6,
        "Lower voltage cut-off [V]": 3.0,
        "Upper voltage cut-off [V]": 4.2,
        "Nominal voltage [V]": 3.7,
        "Maximum C-rate": 1.0,
        "Typical cycle life": "500-1000 cycles",
    },
    "characteristics": {
        "energy_density": "High",
        "power_density": "Medium",
        "safety": "Moderate",
        "cost": "Very High",
        "temperature_range": "-20°C to 45°C",
    },
    "recommended_parameter_sets": ["Marquis2019", "Ecker2015", "Ramadass2004"],
}

CHEMISTRY_DEFAULTS = {
    "LFP": LFP_DEFAULTS,
    "NMC": NMC_DEFAULTS,
    "NCA": NCA_DEFAULTS,
    "LCO": LCO_DEFAULTS,
}


# =============================================================================
# DETAILED PARAMETER SET INFORMATION
# =============================================================================

PARAMETER_SET_DETAILS = {
    "Prada2013": {
        "full_name": "Prada et al. 2013 LFP Parameters",
        "chemistry": "LFP",
        "cell_type": "cylindrical",
        "cell_format": "26650",
        "reference": "Prada et al., J. Electrochem. Soc., 160(4), A542-A554 (2013)",
        "doi": "10.1149/2.023304jes",
        "key_parameters": {
            "Nominal cell capacity [A.h]": 2.3,
            "Electrode height [m]": 0.065,
            "Electrode width [m]": 1.58,
            "Negative electrode thickness [m]": 100e-6,
            "Positive electrode thickness [m]": 183e-6,
            "Separator thickness [m]": 25e-6,
        },
        "validated_conditions": {
            "temperature_range": "5°C to 45°C",
            "c_rate_range": "C/25 to 5C",
        },
    },
    "Chen2020": {
        "full_name": "Chen et al. 2020 NMC Parameters (LG M50)",
        "chemistry": "NMC",
        "cell_type": "cylindrical",
        "cell_format": "21700",
        "reference": "Chen et al., J. Electrochem. Soc., 167(8), 080534 (2020)",
        "doi": "10.1149/1945-7111/ab9050",
        "key_parameters": {
            "Nominal cell capacity [A.h]": 5.0,
            "Electrode height [m]": 0.0649,
            "Electrode width [m]": 1.585,
            "Negative electrode thickness [m]": 85.2e-6,
            "Positive electrode thickness [m]": 75.6e-6,
            "Separator thickness [m]": 12e-6,
        },
        "validated_conditions": {
            "temperature_range": "0°C to 45°C",
            "c_rate_range": "C/20 to 4C",
        },
    },
    "ORegan2022": {
        "full_name": "O'Regan et al. 2022 NMC Parameters (LG M50)",
        "chemistry": "NMC",
        "cell_type": "cylindrical",
        "cell_format": "21700",
        "reference": "O'Regan et al., Electrochim. Acta, 425, 140700 (2022)",
        "doi": "10.1016/j.electacta.2022.140700",
        "key_parameters": {
            "Nominal cell capacity [A.h]": 5.0,
        },
        "validated_conditions": {
            "temperature_range": "-10°C to 45°C",
            "c_rate_range": "C/3 to 3C",
        },
        "special_features": ["Thermal parameterization", "Drive cycle validation"],
    },
    "NCA_Kim2011": {
        "full_name": "Kim et al. 2011 NCA Parameters",
        "chemistry": "NCA",
        "cell_type": "cylindrical",
        "cell_format": "18650",
        "reference": "Kim et al., J. Electrochem. Soc., 158(8), A955-A969 (2011)",
        "doi": "10.1149/1.3597614",
        "key_parameters": {
            "Nominal cell capacity [A.h]": 2.9,
        },
        "validated_conditions": {
            "temperature_range": "25°C",
            "c_rate_range": "C/2 to 3C",
        },
    },
    "Marquis2019": {
        "full_name": "Marquis et al. 2019 LCO Parameters",
        "chemistry": "LCO",
        "cell_type": "pouch",
        "reference": "Marquis et al., J. Electrochem. Soc., 166(15), A3693-A3706 (2019)",
        "doi": "10.1149/2.0011915jes",
        "key_parameters": {
            "Nominal cell capacity [A.h]": 0.680,
            "Negative electrode thickness [m]": 100e-6,
            "Positive electrode thickness [m]": 100e-6,
            "Separator thickness [m]": 25e-6,
        },
        "validated_conditions": {
            "temperature_range": "25°C",
            "c_rate_range": "C/10 to 1C",
        },
    },
    "Ecker2015": {
        "full_name": "Ecker et al. 2015 LCO Parameters (Kokam)",
        "chemistry": "LCO",
        "cell_type": "pouch",
        "cell_format": "SLPB78205130H",
        "reference": "Ecker et al., J. Electrochem. Soc., 162(9), A1836-A1848 (2015)",
        "doi": "10.1149/2.0551509jes",
        "key_parameters": {
            "Nominal cell capacity [A.h]": 7.5,
        },
        "validated_conditions": {
            "temperature_range": "25°C to 40°C",
            "c_rate_range": "C/10 to 2C",
        },
        "special_features": ["Comprehensive validation dataset"],
    },
    "Ai2020": {
        "full_name": "Ai et al. 2020 NMC Parameters (Enertech)",
        "chemistry": "NMC",
        "cell_type": "pouch",
        "reference": "Ai et al., J. Electrochem. Soc., 167(1), 013512 (2020)",
        "doi": "10.1149/2.0122001jes",
        "key_parameters": {
            "Nominal cell capacity [A.h]": 12.5,
        },
        "validated_conditions": {
            "temperature_range": "25°C",
            "c_rate_range": "C/20 to 3C",
        },
        "special_features": ["Large format cell", "Thermal characterization"],
    },
    "Ramadass2004": {
        "full_name": "Ramadass et al. 2004 LCO Parameters (Sony)",
        "chemistry": "LCO",
        "cell_type": "cylindrical",
        "cell_format": "18650",
        "reference": "Ramadass et al., J. Electrochem. Soc., 151(2), A196-A203 (2004)",
        "doi": "10.1149/1.1634273",
        "key_parameters": {
            "Nominal cell capacity [A.h]": 1.656,
        },
        "validated_conditions": {
            "temperature_range": "25°C",
            "c_rate_range": "C/6 to 2C",
        },
        "special_features": ["Classic reference parameter set"],
    },
    "Mohtat2020": {
        "full_name": "Mohtat et al. 2020 NMC Parameters",
        "chemistry": "NMC",
        "cell_type": "pouch",
        "reference": "Mohtat et al., J. Electrochem. Soc., 167(9), 090512 (2020)",
        "doi": "10.1149/1945-7111/ab8f59",
        "key_parameters": {
            "Nominal cell capacity [A.h]": 0.490,
        },
        "validated_conditions": {
            "temperature_range": "25°C",
            "c_rate_range": "C/20 to 2C",
        },
    },
    "Xu2019": {
        "full_name": "Xu et al. 2019 Degradation Parameters",
        "chemistry": "NMC",
        "cell_type": "general",
        "reference": "Xu et al., J. Electrochem. Soc., 166(14), A3456-A3463 (2019)",
        "doi": "10.1149/2.0501914jes",
        "special_features": ["Degradation modeling", "SEI parameters"],
    },
}


def get_parameter_set_info(name: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a parameter set."""
    return PARAMETER_SET_DETAILS.get(name)


def get_parameter_sets_for_chemistry(chemistry: str) -> List[str]:
    """Get list of parameter sets available for a given chemistry."""
    return [
        name for name, details in PARAMETER_SET_DETAILS.items()
        if details.get("chemistry") == chemistry
    ]


def get_chemistry_defaults(chemistry: str) -> Optional[Dict[str, Any]]:
    """Get default parameters and characteristics for a chemistry."""
    return CHEMISTRY_DEFAULTS.get(chemistry)


def list_all_parameter_sets() -> Dict[str, Dict[str, Any]]:
    """Get summary of all available parameter sets."""
    return {
        name: {
            "chemistry": details.get("chemistry"),
            "cell_type": details.get("cell_type"),
            "cell_format": details.get("cell_format", "N/A"),
            "reference": details.get("reference"),
        }
        for name, details in PARAMETER_SET_DETAILS.items()
    }
