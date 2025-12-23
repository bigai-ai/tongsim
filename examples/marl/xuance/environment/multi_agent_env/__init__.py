from xuance.common import Optional
from xuance.environment.multi_agent_env.macsr_dummy import MACSR as ParallelUeMACSREnv
from xuance.environment.utils import EnvironmentDict

REGISTRY_MULTI_AGENT_ENV: Optional[EnvironmentDict] = {"parralle_UeMACSR": ParallelUeMACSREnv}

__all__ = [
    "REGISTRY_MULTI_AGENT_ENV",
]
