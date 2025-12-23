from collections.abc import Callable, Mapping, Sequence
from typing import Any, Dict, List, Optional, SupportsFloat, Tuple, Type, Union

from xuance.common.common_tools import (
    EPS,
    combined_shape,
    create_directory,
    discount_cumsum,
    get_arguments,
    get_configs,
    get_runner,
    get_time_string,
    recursive_dict_update,
    space2shape,
)
from xuance.common.memory_offline import OfflineBuffer_D4RL
from xuance.common.memory_tools import (
    Buffer,
    DummyOffPolicyBuffer,
    DummyOffPolicyBuffer_Atari,
    DummyOnPolicyBuffer,
    DummyOnPolicyBuffer_Atari,
    EpisodeBuffer,
    PerOffPolicyBuffer,
    RecurrentOffPolicyBuffer,
    SequentialReplayBuffer,
    create_memory,
    sample_batch,
    store_element,
)
from xuance.common.memory_tools_marl import (
    BaseBuffer,
    MARL_OffPolicyBuffer,
    MARL_OffPolicyBuffer_RNN,
    MARL_OnPolicyBuffer,
    MARL_OnPolicyBuffer_RNN,
    MeanField_OffPolicyBuffer,
    MeanField_OffPolicyBuffer_RNN,
    MeanField_OnPolicyBuffer,
    MeanField_OnPolicyBuffer_RNN,
)
from xuance.common.segtree_tool import MinSegmentTree, SegmentTree, SumSegmentTree
from xuance.common.statistic_tools import RunningMeanStd, mpi_mean, mpi_moments

__all__ = [
    # typing
    "Optional",
    "Union",
    "List",
    "Dict",
    "Sequence",
    "Callable",
    "Any",
    "Tuple",
    "SupportsFloat",
    "Type",
    "Mapping",
    # common_tools
    "EPS",
    "recursive_dict_update",
    "get_configs",
    "get_arguments",
    "get_runner",
    "create_directory",
    "combined_shape",
    "space2shape",
    "discount_cumsum",
    "get_time_string",
    # statistic_tools
    "mpi_mean",
    "mpi_moments",
    "RunningMeanStd",
    # memory_tools
    "create_memory",
    "store_element",
    "sample_batch",
    "Buffer",
    "EpisodeBuffer",
    "DummyOnPolicyBuffer",
    "DummyOnPolicyBuffer_Atari",
    "DummyOffPolicyBuffer",
    "DummyOffPolicyBuffer_Atari",
    "RecurrentOffPolicyBuffer",
    "PerOffPolicyBuffer",
    "SequentialReplayBuffer",
    # memory_tools_marl
    "BaseBuffer",
    "MARL_OnPolicyBuffer",
    "MARL_OnPolicyBuffer_RNN",
    "MARL_OffPolicyBuffer",
    "MARL_OffPolicyBuffer_RNN",
    "MeanField_OnPolicyBuffer",
    "MeanField_OnPolicyBuffer_RNN",
    "MeanField_OffPolicyBuffer",
    "MeanField_OffPolicyBuffer_RNN",
    "I3CNet_Buffer",
    "I3CNet_Buffer_RNN",
    "OfflineBuffer_D4RL",
    # segtree_tool
    "SegmentTree",
    "SumSegmentTree",
    "MinSegmentTree",
]

try:
    from xuance.common.tuning_tools import (
        HyperParameterTuner,
        MultiObjectiveTuner,
        set_hyperparameters,
    )

    __all__ += ["HyperParameterTuner", "MultiObjectiveTuner", "set_hyperparameters"]
except ImportError:
    pass

try:
    from xuance.common.offline_util import (
        compute_mean_std,
        load_d4rl_dataset,
        normalize_states,
        return_range,
    )

    __all__ += ["load_d4rl_dataset", "compute_mean_std", "normalize_states", "return_range"]
except ImportError:
    pass
