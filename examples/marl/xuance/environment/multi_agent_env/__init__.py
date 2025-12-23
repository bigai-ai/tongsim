from xuance.common import Optional
from xuance.environment.multi_agent_env.macs_dummy import MACS as ParallelUeMACSEnv
from xuance.environment.utils import EnvironmentDict

REGISTRY_MULTI_AGENT_ENV: Optional[EnvironmentDict] = {"parralle_UeMACS": ParallelUeMACSEnv}

__all__ = [
    "REGISTRY_MULTI_AGENT_ENV",
]
