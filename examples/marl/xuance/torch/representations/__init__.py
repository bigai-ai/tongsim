from .mlp import Basic_Identical, Basic_MLP
from .rnn import Basic_RNN

REGISTRY_Representation = {
    "Basic_Identical": Basic_Identical,
    "Basic_MLP": Basic_MLP,
    "Basic_RNN": Basic_RNN,
}

__all__ = [
    "REGISTRY_Representation",
    "Basic_Identical",
    "Basic_MLP",
    "Basic_CNN",
    "AC_CNN_Atari",
    "Basic_RNN",
    "Basic_ViT",
]
