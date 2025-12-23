# TongSIM

![TongSim Lite Hero](assets/tongsim-main.jpg)

!!! info "🔗 Official Links"
    - 🏠 [Homepage](https://tongsim-platform.github.io/tongsim)
    - 🤗 [Asset Library](https://huggingface.co/datasets/bigai/TongSIM-Asset)
    - [GitHub](https://github.com/bigai-ai/tongsim)

As AI capabilities (especially Large Language Models) advance, research is shifting from single-text modality to more challenging multimodal and embodied intelligence. Embodied intelligence emphasizes training agents in realistic simulation environments through a physical body and action feedback, rather than relying solely on labeled data. However, most existing simulation platforms are designed for specific tasks, and a unified, high-consistency environment spanning low-level skills to high-level multi-agent interaction remains scarce.

TongSIM is a high-fidelity, general-purpose platform for embodied agent training and testing built on Unreal Engine. It supports tasks from low-level single-agent skills (e.g., navigation) to high-level scenarios such as multi-agent social simulation and human–AI collaboration. TongSIM constructs 100+ diverse multi-room indoor scenarios alongside an open-ended, interaction-rich outdoor simulated town, and incorporates thousands of interactive 3D object models spanning 500+ categories.

On top of the environment, TongSIM provides a comprehensive evaluation system and a suite of benchmarks covering major agent capabilities: perception, cognition, decision-making, learning, execution, and social collaboration. The platform also offers high-fidelity and customizable scenes, rich annotations, and parallel training to accelerate research and development of general embodied intelligence.

## Highlights

- High-fidelity indoor + outdoor worlds: 100+ multi-room indoor scenes and an open-ended outdoor town
- Large-scale interactive assets: thousands of objects spanning 500+ categories
- Benchmarks and evaluation: perception, cognition, decision-making, learning, execution, and social collaboration
- Multimodal perception: built-in vision and audio; extensible to other modalities
- Physics-consistent simulation with causal world dynamics and rich annotations
- Parallel simulation for scalable training
- Easy integration: Python SDK over gRPC with practical examples
- Extensible, plugin-oriented architecture
