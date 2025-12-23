from xuance.common import Any, Dict

from .base import AgentKeys, MultiAgentDict, RawEnvironment, RawMultiAgentEnv
from .wrapper import XuanCeAtariEnvWrapper, XuanCeEnvWrapper, XuanCeMultiAgentEnvWrapper

EnvName = Any
EnvObject = Any
EnvironmentDict = Dict[EnvName, EnvObject]


__all__ = [
    "RawEnvironment",
    "RawMultiAgentEnv",
    "XuanCeEnvWrapper",
    "XuanCeAtariEnvWrapper",
    "XuanCeMultiAgentEnvWrapper",
    "EnvironmentDict",
    "MultiAgentDict",
    "AgentKeys",
]
