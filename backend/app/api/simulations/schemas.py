"""
Pydantic models and enums for the simulations API.
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field


class SimulationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatteryChemistry(str, Enum):
    LFP = "LFP"
    NMC = "NMC"
    NCA = "NCA"
    LCO = "LCO"
    SODIUM_ION = "SODIUM_ION"
    LEAD_ACID = "LEAD_ACID"
    CUSTOM = "custom"


class ModelType(str, Enum):
    """PyBaMM model types with different fidelity/speed tradeoffs"""
    SPM = "SPM"              # Single Particle Model - fastest
    SPMe = "SPMe"            # SPM with Electrolyte - balanced
    DFN = "DFN"              # Doyle-Fuller-Newman - most accurate
    MPM = "MPM"              # Many Particle Model
    NEWMAN_TOBIAS = "NewmanTobias"  # Simplified DFN


class ParameterSet(str, Enum):
    """Validated PyBaMM parameter sets for different cells"""
    # NMC cells
    CHEN2020 = "Chen2020"              # LG M50 21700 NMC
    OREGAN2022 = "ORegan2022"          # LG M50 with thermal
    AI2020 = "Ai2020"                  # Enertech NMC
    MOHTAT2020 = "Mohtat2020"          # NMC532
    # LFP cells
    PRADA2013 = "Prada2013"            # LFP 26650
    # NCA cells
    NCA_KIM2011 = "NCA_Kim2011"        # NCA pouch
    # LCO cells  
    MARQUIS2019 = "Marquis2019"        # Kokam LCO
    ECKER2015 = "Ecker2015"            # Kokam LCO
    RAMADASS2004 = "Ramadass2004"      # Sony 18650
    XU2019 = "Xu2019"                  # Degradation focused
    # Other chemistries
    CHAYAMBUKA2022 = "Chayambuka2022"  # Sodium-ion
    # Custom
    CUSTOM = "custom"


class ProtocolType(str, Enum):
    """Standard test protocols used by cell engineers"""
    STANDARD_CYCLE = "standard_cycle"  # Default: CCCV charge + CC discharge
    CAPACITY_CHECK = "capacity_check"  # CCCV charge + C/20 discharge for baseline
    RATE_CAPABILITY = "rate_capability"  # Discharges at different C-rates with rests
    DRIVE_CYCLE = "drive_cycle"  # Time-varying current profile
    HPPC = "hppc"  # Hybrid Pulse Power Characterization
    CUSTOM = "custom"  # User-defined protocol steps


class ThermalMode(str, Enum):
    """Thermal model options for simulation"""
    ISOTHERMAL = "isothermal"  # Default: constant temperature (current behavior)
    LUMPED = "lumped"  # Lumped thermal model - single cell temperature
    # Future: DISTRIBUTED = "distributed"  # Full thermal model with spatial gradients


class ExperimentMode(str, Enum):
    """Mode for defining experiment steps"""
    PROTOCOL = "protocol"      # Use predefined protocol_type
    CUSTOM = "custom"          # Use custom experiment_definition
    TEMPLATE = "template"      # Use experiment_template_id


class StepType(str, Enum):
    """Types of experiment steps supported by PyBAMM"""
    CURRENT = "current"
    C_RATE = "c_rate"
    VOLTAGE = "voltage"
    POWER = "power"
    RESISTANCE = "resistance"
    REST = "rest"
    STRING = "string"          # Raw PyBAMM string instruction


class ExperimentStep(BaseModel):
    """Single step in an experiment"""
    step_type: StepType
    value: Optional[float] = None
    value_unit: Optional[str] = None  # 'A', 'C', 'V', 'W', 'Ohm'
    duration: Optional[str] = None    # "1 hour", "30 minutes", "3600 seconds"
    termination: Optional[str] = None # "3.3V", "C/50", "50mA"
    period: Optional[str] = None      # Sampling period
    temperature: Optional[str] = None # Step-specific temperature
    tags: Optional[List[str]] = None
    direction: Optional[str] = None   # "charge", "discharge"
    step_string: Optional[str] = None # For STRING type - raw PyBAMM string
    drive_cycle_data: Optional[List[List[float]]] = None  # [[time, value], ...]
    drive_cycle_type: Optional[str] = None  # 'current', 'power', 'voltage'


class ExperimentCycle(BaseModel):
    """A cycle is a group of steps that can be repeated"""
    steps: List[ExperimentStep]
    repeat: int = Field(default=1, ge=1, le=1000)


class ExperimentDefinition(BaseModel):
    """Full experiment definition with cycles"""
    cycles: List[ExperimentCycle]
    default_period: Optional[str] = "1 minute"
    default_temperature_celsius: Optional[float] = 25.0


class SimulationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    # Cell & Model (Step 1 of wizard)
    parameter_set: Optional[ParameterSet] = None  # Primary: validated PyBaMM parameter set
    chemistry: BatteryChemistry = BatteryChemistry.LFP  # Fallback/derived from parameter_set
    model_type: ModelType = ModelType.DFN  # Model fidelity selection
    model_options: Optional[dict] = None  # Advanced model options (thermal, SEI, etc.)
    # Experiment (Step 2 of wizard)
    protocol: ProtocolType = ProtocolType.STANDARD_CYCLE
    c_rate: float = Field(default=1.0, ge=0.05, le=10.0)
    temperature_celsius: float = Field(default=25.0, ge=-20.0, le=60.0)
    cycles: int = Field(default=1, ge=1, le=1000)
    experiment_mode: ExperimentMode = ExperimentMode.PROTOCOL
    experiment_definition: Optional[ExperimentDefinition] = None
    experiment_template_id: Optional[str] = None
    experiment_period: Optional[str] = "1 minute"
    # Additional options
    custom_parameters: Optional[dict] = None
    # Comparison helper: also run with alternate model
    also_run_with_model: Optional[ModelType] = None


class SimulationResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    status: SimulationStatus
    progress: int
    # Cell & Model
    parameter_set: Optional[str] = None
    chemistry: BatteryChemistry
    model_type: Optional[str] = "DFN"
    model_options: Optional[dict] = None
    # Experiment
    protocol: Optional[ProtocolType] = ProtocolType.STANDARD_CYCLE
    c_rate: float
    temperature_celsius: float
    cycles: int
    experiment_mode: Optional[ExperimentMode] = ExperimentMode.PROTOCOL
    experiment_definition: Optional[dict] = None
    experiment_template_id: Optional[str] = None
    experiment_period: Optional[str] = None
    # Additional
    custom_parameters: Optional[dict]
    also_run_with_model: Optional[str] = None
    comparison_simulation_id: Optional[str] = None  # Link to comparison sim if created
    # Results and status
    results: Optional[dict]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class CompareSimulationsRequest(BaseModel):
    """Request to compare multiple simulations"""
    simulation_ids: List[str] = Field(..., min_length=2, max_length=10)


class MultiChemistryRequest(BaseModel):
    """Request to run the same test across multiple chemistries"""
    name_prefix: str
    description: Optional[str] = None
    chemistries: List[BatteryChemistry] = Field(..., min_length=2, max_length=5)
    protocol: ProtocolType = ProtocolType.STANDARD_CYCLE
    c_rate: float = Field(default=1.0, ge=0.1, le=10.0)
    temperature_celsius: float = Field(default=25.0, ge=-20.0, le=60.0)
    cycles: int = Field(default=1, ge=1, le=100)
    custom_parameters: Optional[dict] = None
    experiment_mode: ExperimentMode = ExperimentMode.PROTOCOL
    experiment_definition: Optional[ExperimentDefinition] = None
    experiment_template_id: Optional[str] = None


# ============================================================================
# Experiment Step and Template CRUD schemas
# ============================================================================

class ExperimentStepCreate(BaseModel):
    """Create a reusable experiment step"""
    name: str
    description: Optional[str] = None
    is_public: bool = False
    step_type: StepType
    value: Optional[float] = None
    value_unit: Optional[str] = None
    duration: Optional[str] = None
    termination: Optional[str] = None
    period: Optional[str] = None
    temperature: Optional[str] = None
    tags: Optional[List[str]] = None
    direction: Optional[str] = None
    step_string: Optional[str] = None
    drive_cycle_data: Optional[List[List[float]]] = None
    drive_cycle_type: Optional[str] = None


class ExperimentStepResponse(BaseModel):
    """Response for experiment step"""
    id: str
    user_id: Optional[str]
    name: str
    description: Optional[str]
    is_public: bool
    step_type: str
    value: Optional[float]
    value_unit: Optional[str]
    duration: Optional[str]
    termination: Optional[str]
    period: Optional[str]
    temperature: Optional[str]
    tags: Optional[List[str]]
    direction: Optional[str]
    step_string: Optional[str]
    drive_cycle_data: Optional[List[List[float]]]
    drive_cycle_type: Optional[str]
    created_at: datetime
    updated_at: datetime


class ExperimentTemplateCreate(BaseModel):
    """Create an experiment template"""
    name: str
    description: Optional[str] = None
    is_public: bool = False
    cycles: List[ExperimentCycle]
    default_period: Optional[str] = "1 minute"
    default_temperature_celsius: Optional[float] = 25.0


class ExperimentTemplateResponse(BaseModel):
    """Response for experiment template"""
    id: str
    user_id: Optional[str]
    name: str
    description: Optional[str]
    is_public: bool
    cycles: List[dict]
    default_period: Optional[str]
    default_temperature_celsius: Optional[float]
    created_at: datetime
    updated_at: datetime


class DriveCycleCreate(BaseModel):
    """Create a drive cycle"""
    name: str
    description: Optional[str] = None
    is_public: bool = True
    cycle_type: str = Field(..., pattern="^(current|power|voltage)$")
    data: List[List[float]]  # [[time_s, value], ...]
    duration_seconds: Optional[float] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = None


class DriveCycleResponse(BaseModel):
    """Response for drive cycle"""
    id: str
    user_id: Optional[str]
    name: str
    description: Optional[str]
    is_public: bool
    cycle_type: str
    data: List[List[float]]
    duration_seconds: Optional[float]
    source: Optional[str]
    tags: Optional[List[str]]
    created_at: datetime
    updated_at: datetime
