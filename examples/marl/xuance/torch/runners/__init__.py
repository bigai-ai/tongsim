from .runner_basic import RunnerBase
from .runner_marl import RunnerMARL

REGISTRY_Runner = {
    "DL_toolbox": "PyTorch",
    "MARL": RunnerMARL,
}

__all__ = [
    "RunnerBase",
    "RunnerMARL",
]
