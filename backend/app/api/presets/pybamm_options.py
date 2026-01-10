"""
Comprehensive PyBAMM model options and configurations.

All options are documented per PyBAMM official documentation:
- Models: https://docs.pybamm.org/en/stable/source/api/models/index.html
- Model Options: https://docs.pybamm.org/en/stable/source/api/models/base_models/base_battery_model.html
- Submodels: https://docs.pybamm.org/en/stable/source/api/models/submodels/index.html
"""
from typing import Dict, List, Any


# =============================================================================
# LITHIUM-ION MODELS
# Reference: https://docs.pybamm.org/en/stable/source/api/models/lithium_ion/index.html
# =============================================================================
LITHIUM_ION_MODELS = {
    "SPM": {
        "name": "Single Particle Model",
        "class": "pybamm.lithium_ion.SPM",
        "description": "Simplified model treating each electrode as a single spherical particle. Fast but less accurate for high C-rates.",
        "complexity": "low",
        "recommended_use": "Quick screening, parameter estimation, low C-rate simulations",
        "variants": ["SPM", "BasicSPM", "Basic3DThermalSPM"],
    },
    "SPMe": {
        "name": "Single Particle Model with Electrolyte",
        "class": "pybamm.lithium_ion.SPMe",
        "description": "SPM with electrolyte dynamics included. Better accuracy than SPM at moderate C-rates.",
        "complexity": "medium-low",
        "recommended_use": "Moderate C-rate simulations, parameter sensitivity studies",
        "variants": ["SPMe"],
    },
    "MPM": {
        "name": "Many Particle Model",
        "class": "pybamm.lithium_ion.MPM",
        "description": "Models particle size distribution effects. Good for cells with heterogeneous electrodes.",
        "complexity": "medium",
        "recommended_use": "Particle size distribution studies, heterogeneous electrode modeling",
        "variants": ["MPM"],
    },
    "DFN": {
        "name": "Doyle-Fuller-Newman Model",
        "class": "pybamm.lithium_ion.DFN",
        "description": "Full physics-based pseudo-2D model. Most comprehensive and accurate for general use.",
        "complexity": "high",
        "recommended_use": "Accurate simulations, high C-rate, thermal analysis, degradation studies",
        "variants": ["DFN", "BasicDFN", "BasicDFNComposite", "BasicDFNHalfCell"],
    },
    "NewmanTobias": {
        "name": "Newman-Tobias Model",
        "class": "pybamm.lithium_ion.NewmanTobias",
        "description": "Simplified DFN with uniform concentration in solid phase. Fast with reasonable accuracy.",
        "complexity": "medium",
        "recommended_use": "When solid diffusion is not rate-limiting",
        "variants": ["NewmanTobias"],
    },
    "MSMR": {
        "name": "Multi-Species Multi-Reaction Model",
        "class": "pybamm.lithium_ion.MSMR",
        "description": "Advanced model for multi-species intercalation and multiple reaction pathways.",
        "complexity": "very high",
        "recommended_use": "Multi-species electrodes, advanced reaction mechanisms",
        "variants": ["MSMR"],
    },
    "Yang2017": {
        "name": "Yang et al. 2017 Model",
        "class": "pybamm.lithium_ion.Yang2017",
        "description": "Specialized model from Yang et al. 2017 publication.",
        "complexity": "high",
        "recommended_use": "Specific research applications",
        "variants": ["Yang2017"],
    },
}


# =============================================================================
# LEAD-ACID MODELS
# Reference: https://docs.pybamm.org/en/stable/source/api/models/lead_acid/index.html
# =============================================================================
LEAD_ACID_MODELS = {
    "Full": {
        "name": "Full Lead-Acid Model",
        "class": "pybamm.lead_acid.Full",
        "description": "Complete physics-based lead-acid battery model.",
        "complexity": "high",
        "recommended_use": "Accurate lead-acid simulations",
    },
    "LOQS": {
        "name": "Leading-Order Quasi-Static Model",
        "class": "pybamm.lead_acid.LOQS",
        "description": "Simplified quasi-static lead-acid model.",
        "complexity": "low",
        "recommended_use": "Fast lead-acid simulations",
    },
    "Composite": {
        "name": "Composite Lead-Acid Model",
        "class": "pybamm.lead_acid.Composite",
        "description": "Composite lead-acid model with multiple scales.",
        "complexity": "medium",
        "recommended_use": "Multi-scale lead-acid analysis",
    },
}


# =============================================================================
# EQUIVALENT CIRCUIT MODELS
# Reference: https://docs.pybamm.org/en/stable/source/api/models/equivalent_circuit/index.html
# =============================================================================
EQUIVALENT_CIRCUIT_MODELS = {
    "Thevenin": {
        "name": "Thevenin Equivalent Circuit",
        "class": "pybamm.equivalent_circuit.Thevenin",
        "description": "Simple Thevenin equivalent circuit model with RC pairs.",
        "complexity": "very low",
        "recommended_use": "BMS applications, real-time control, system-level simulations",
    },
    "SplitOCVR": {
        "name": "Split OCV-R Model",
        "class": "pybamm.lithium_ion.SplitOCVR",
        "description": "Equivalent circuit model with split OCV representation.",
        "complexity": "low",
        "recommended_use": "Fast SOC estimation, electrode-level OCV tracking",
    },
}


# =============================================================================
# MODEL OPTIONS (SUBMODELS)
# Reference: https://docs.pybamm.org/en/stable/source/api/models/base_models/base_battery_model.html
# =============================================================================
PYBAMM_MODEL_OPTIONS = {
    "thermal": {
        "description": "Thermal model to use for temperature evolution",
        "options": ["isothermal", "lumped", "x-lumped", "x-full"],
        "default": "isothermal",
        "details": {
            "isothermal": "Constant temperature throughout simulation",
            "lumped": "Single temperature for entire cell (0D thermal)",
            "x-lumped": "Temperature varies through cell thickness only",
            "x-full": "Full thermal model with spatial temperature gradients",
        },
    },
    "SEI": {
        "description": "Solid Electrolyte Interphase growth model",
        "options": [
            "none",
            "constant",
            "reaction limited",
            "solvent-diffusion limited",
            "electron-migration limited",
            "interstitial-diffusion limited",
            "ec reaction limited",
        ],
        "default": "none",
        "details": {
            "none": "No SEI growth (pybamm.sei.NoSEI)",
            "constant": "Constant SEI thickness",
            "reaction limited": "SEI growth limited by reaction kinetics",
            "solvent-diffusion limited": "SEI growth limited by solvent diffusion",
            "electron-migration limited": "SEI growth limited by electron migration",
            "interstitial-diffusion limited": "SEI growth limited by interstitial diffusion",
            "ec reaction limited": "SEI growth limited by EC reaction",
        },
    },
    "SEI film resistance": {
        "description": "Additional overpotential term due to SEI resistance",
        "options": ["none", "distributed", "average"],
        "default": "none (or distributed if SEI is enabled)",
        "details": {
            "none": "No additional resistance from SEI",
            "distributed": "Spatially distributed SEI resistance",
            "average": "Average SEI resistance (approximation)",
        },
    },
    "SEI porosity change": {
        "description": "Whether to include porosity change due to SEI formation",
        "options": ["false", "true"],
        "default": "false",
    },
    "SEI on cracks": {
        "description": "Whether to include SEI growth on particle cracks",
        "options": ["false", "true"],
        "default": "false",
    },
    "lithium plating": {
        "description": "Lithium plating/stripping model",
        "options": ["none", "reversible", "partially reversible", "irreversible"],
        "default": "none",
        "details": {
            "none": "No lithium plating",
            "reversible": "Fully reversible plating/stripping",
            "partially reversible": "Partial reversibility with dead lithium formation",
            "irreversible": "Irreversible plating (capacity loss)",
        },
    },
    "lithium plating porosity change": {
        "description": "Whether to include porosity change due to lithium plating",
        "options": ["false", "true"],
        "default": "false",
    },
    "particle": {
        "description": "Particle diffusion submodel",
        "options": ["Fickian diffusion", "uniform profile", "quadratic profile", "quartic profile"],
        "default": "Fickian diffusion",
        "details": {
            "Fickian diffusion": "Full Fickian diffusion in particles (most accurate)",
            "uniform profile": "Uniform concentration profile (fastest)",
            "quadratic profile": "Quadratic concentration profile approximation",
            "quartic profile": "Quartic concentration profile approximation",
        },
    },
    "particle size": {
        "description": "Single particle size or distribution",
        "options": ["single", "distribution"],
        "default": "single",
        "details": {
            "single": "Single representative particle size",
            "distribution": "Particle size distribution at each location",
        },
    },
    "particle shape": {
        "description": "Shape of electrode particles for surface area calculation",
        "options": ["spherical", "no particles"],
        "default": "spherical",
    },
    "particle mechanics": {
        "description": "Mechanical effects in particles",
        "options": ["none", "swelling only", "swelling and cracking"],
        "default": "none",
        "details": {
            "none": "No mechanical effects",
            "swelling only": "Particle swelling during cycling",
            "swelling and cracking": "Swelling with crack formation",
        },
        "electrode_specific": True,  # Can be tuple for neg/pos electrodes
    },
    "stress-induced diffusion": {
        "description": "Whether to include stress-induced diffusion",
        "options": ["false", "true"],
        "default": "false (true if particle mechanics enabled)",
        "electrode_specific": True,
    },
    "loss of active material": {
        "description": "Loss of active material mechanism",
        "options": ["none", "stress-driven", "reaction-driven", "stress and reaction-driven"],
        "default": "none",
        "electrode_specific": True,
    },
    "intercalation kinetics": {
        "description": "Kinetic model for intercalation reaction",
        "options": [
            "symmetric Butler-Volmer",
            "asymmetric Butler-Volmer",
            "linear",
            "Marcus",
            "Marcus-Hush-Chidsey",
        ],
        "default": "symmetric Butler-Volmer",
        "details": {
            "symmetric Butler-Volmer": "Standard symmetric Butler-Volmer kinetics",
            "asymmetric Butler-Volmer": "Asymmetric Butler-Volmer with different transfer coefficients",
            "linear": "Linearized kinetics (small overpotential)",
            "Marcus": "Marcus theory kinetics",
            "Marcus-Hush-Chidsey": "Marcus-Hush-Chidsey kinetics (Zeng 2014 asymptotic form)",
        },
        "electrode_specific": True,
    },
    "interface utilisation": {
        "description": "How electrode interface area is utilized",
        "options": ["full", "constant", "current-driven"],
        "default": "full",
    },
    "current collector": {
        "description": "Current collector model",
        "options": ["uniform", "potential pair", "potential pair quite conductive"],
        "default": "uniform",
        "details": {
            "uniform": "Uniform current distribution",
            "potential pair": "Potential-pair model for tab effects",
            "potential pair quite conductive": "Simplified potential-pair for conductive collectors",
        },
    },
    "dimensionality": {
        "description": "Dimension of current collector problem",
        "options": [0, 1, 2],
        "default": 0,
        "details": {
            0: "0D (lumped current collector)",
            1: "1D (through-plane variation)",
            2: "2D (in-plane variation, e.g., pouch cell tabs)",
        },
    },
    "electrolyte conductivity": {
        "description": "Electrolyte conductivity model",
        "options": ["default", "full", "leading order", "composite", "integrated"],
        "default": "default",
    },
    "surface form": {
        "description": "Whether to use surface formulation",
        "options": ["false", "differential", "algebraic"],
        "default": "false",
    },
    "convection": {
        "description": "Convection effects (lead-acid only)",
        "options": ["none", "uniform transverse", "full transverse"],
        "default": "none",
    },
    "operating mode": {
        "description": "How the cell is driven",
        "options": [
            "current",
            "voltage",
            "power",
            "resistance",
            "differential power",
            "differential resistance",
            "explicit power",
            "explicit resistance",
            "CCCV",
        ],
        "default": "current",
        "details": {
            "current": "Explicitly supplied current",
            "voltage": "Solve for current to match voltage",
            "power": "Solve for current to match power",
            "resistance": "Solve for current to match resistance",
            "differential power": "Differential equation for power",
            "differential resistance": "Differential equation for resistance",
            "explicit power": "Current defined to match power",
            "explicit resistance": "Current defined to match resistance",
            "CCCV": "Constant-current constant-voltage protocol",
        },
    },
    "cell geometry": {
        "description": "Cell geometry type",
        "options": ["pouch", "arbitrary"],
        "default": "pouch",
        "details": {
            "pouch": "Standard pouch cell geometry",
            "arbitrary": "Arbitrary geometry with prescribed volume/area",
        },
    },
    "working electrode": {
        "description": "Which electrode(s) are working",
        "options": ["both", "negative", "positive"],
        "default": "both",
        "details": {
            "both": "Standard full cell",
            "negative": "Half-cell with negative working electrode",
            "positive": "Half-cell with positive working electrode",
        },
    },
    "calculate discharge energy": {
        "description": "Whether to calculate discharge energy",
        "options": ["false", "true"],
        "default": "false",
    },
    "calculate heat source for isothermal models": {
        "description": "Calculate heat sources even in isothermal mode",
        "options": ["false", "true"],
        "default": "false",
    },
    "total interfacial current density as a state": {
        "description": "Whether to solve for total interfacial current density",
        "options": ["false", "true"],
        "default": "false (true if SEI film resistance is distributed)",
    },
    "x-average side reactions": {
        "description": "Whether to average side reactions over x-axis (SPM/SPMe)",
        "options": ["false", "true"],
        "default": "false for SPMe, true for SPM",
    },
    "timescale": {
        "description": "Timescale for non-dimensionalization",
        "options": ["default", "number"],
        "default": "default (discharge timescale)",
    },
    "hydrolysis": {
        "description": "Include hydrolysis (lead-acid only)",
        "options": ["false", "true"],
        "default": "false",
    },
}


# =============================================================================
# PARAMETER SETS
# Reference: https://docs.pybamm.org/en/stable/source/api/parameters/parameter_sets.html
# =============================================================================
PARAMETER_SETS = {
    # LFP chemistries
    "Prada2013": {
        "chemistry": "LFP",
        "description": "LFP/Graphite parameters from Prada et al. 2013",
        "cell_type": "cylindrical",
        "reference": "Prada et al., Journal of The Electrochemical Society, 160(4), A542-A554 (2013)",
    },
    # NMC chemistries
    "Chen2020": {
        "chemistry": "NMC",
        "description": "NMC/Graphite parameters for LG M50 cell from Chen et al. 2020",
        "cell_type": "cylindrical 21700",
        "reference": "Chen et al., Journal of The Electrochemical Society, 167(8), 080534 (2020)",
    },
    "ORegan2022": {
        "chemistry": "NMC",
        "description": "NMC/Graphite parameters for LG M50 from O'Regan et al. 2022",
        "cell_type": "cylindrical 21700",
        "reference": "O'Regan et al., Electrochimica Acta, 425, 140700 (2022)",
    },
    "Mohtat2020": {
        "chemistry": "NMC",
        "description": "NMC parameters from Mohtat et al. 2020",
        "cell_type": "pouch",
        "reference": "Mohtat et al., Journal of The Electrochemical Society, 167(9), 090512 (2020)",
    },
    "Ai2020": {
        "chemistry": "NMC",
        "description": "Enertech cell parameters from Ai et al. 2020",
        "cell_type": "pouch",
        "reference": "Ai et al., Journal of The Electrochemical Society, 167(1), 013512 (2020)",
    },
    # NCA chemistries
    "NCA_Kim2011": {
        "chemistry": "NCA",
        "description": "NCA/Graphite parameters from Kim et al. 2011",
        "cell_type": "cylindrical",
        "reference": "Kim et al., Journal of The Electrochemical Society, 158(8), A955-A969 (2011)",
    },
    # LCO chemistries
    "Marquis2019": {
        "chemistry": "LCO",
        "description": "LCO/Graphite parameters from Marquis et al. 2019",
        "cell_type": "pouch",
        "reference": "Marquis et al., Journal of The Electrochemical Society, 166(15), A3693-A3706 (2019)",
    },
    "Ecker2015": {
        "chemistry": "LCO",
        "description": "Kokam SLPB78205130H parameters from Ecker et al. 2015",
        "cell_type": "pouch",
        "reference": "Ecker et al., Journal of The Electrochemical Society, 162(9), A1836-A1848 (2015)",
    },
    # Other/General
    "Xu2019": {
        "chemistry": "NMC",
        "description": "Parameters for degradation modeling from Xu et al. 2019",
        "cell_type": "general",
        "reference": "Xu et al., Journal of The Electrochemical Society, 166(14), A3456-A3463 (2019)",
    },
    "Ramadass2004": {
        "chemistry": "LCO",
        "description": "Sony 18650 parameters from Ramadass et al. 2004",
        "cell_type": "cylindrical 18650",
        "reference": "Ramadass et al., Journal of The Electrochemical Society, 151(2), A196-A203 (2004)",
    },
}


def get_model_options_schema() -> Dict[str, Any]:
    """
    Get a JSON-serializable schema of all available PyBAMM model options.
    Useful for API documentation and frontend configuration.
    """
    return {
        "lithium_ion_models": LITHIUM_ION_MODELS,
        "lead_acid_models": LEAD_ACID_MODELS,
        "equivalent_circuit_models": EQUIVALENT_CIRCUIT_MODELS,
        "model_options": PYBAMM_MODEL_OPTIONS,
        "parameter_sets": PARAMETER_SETS,
    }


def validate_model_options(options: Dict[str, Any]) -> List[str]:
    """
    Validate a dictionary of model options against available options.
    
    Args:
        options: Dictionary of option_name -> value
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    for key, value in options.items():
        if key not in PYBAMM_MODEL_OPTIONS:
            errors.append(f"Unknown model option: '{key}'")
            continue
        
        option_config = PYBAMM_MODEL_OPTIONS[key]
        valid_options = option_config.get("options", [])
        
        # Handle boolean string conversion
        if value in [True, False]:
            value = str(value).lower()
        
        if valid_options and value not in valid_options:
            errors.append(
                f"Invalid value '{value}' for option '{key}'. "
                f"Valid options: {valid_options}"
            )
    
    return errors


def get_recommended_options_for_use_case(use_case: str) -> Dict[str, Any]:
    """
    Get recommended model options for common use cases.
    
    Args:
        use_case: One of 'fast', 'accurate', 'thermal', 'degradation', 'optimization'
        
    Returns:
        Dictionary of recommended options
    """
    use_cases = {
        "fast": {
            "model": "SPM",
            "options": {
                "thermal": "isothermal",
                "particle": "uniform profile",
                "SEI": "none",
            },
            "description": "Fastest simulation for quick screening",
        },
        "accurate": {
            "model": "DFN",
            "options": {
                "thermal": "lumped",
                "particle": "Fickian diffusion",
                "SEI": "none",
            },
            "description": "Accurate physics-based simulation",
        },
        "thermal": {
            "model": "DFN",
            "options": {
                "thermal": "lumped",
                "particle": "Fickian diffusion",
                "calculate heat source for isothermal models": "true",
            },
            "description": "Thermal analysis with temperature evolution",
        },
        "degradation": {
            "model": "DFN",
            "options": {
                "thermal": "lumped",
                "SEI": "solvent-diffusion limited",
                "SEI porosity change": "true",
                "lithium plating": "partially reversible",
                "particle mechanics": "swelling and cracking",
                "loss of active material": "stress and reaction-driven",
            },
            "description": "Full degradation modeling",
        },
        "optimization": {
            "model": "SPMe",
            "options": {
                "thermal": "isothermal",
                "particle": "quadratic profile",
                "SEI": "none",
            },
            "description": "Balanced speed/accuracy for parameter optimization",
        },
    }
    
    return use_cases.get(use_case, use_cases["accurate"])
