## Usage

### Training a New Model

To train a new model, specify the algorithm's configuration file. For example, to train MAPPO:

```bash
uv run examples/marl/example/train.py --config example/config/mappo.yaml
```

**Available Algorithms:**
- MAPPO: `example/config/mappo.yaml`
- IPPO: `example/config/ippo.yaml`


**Configuration:** You can customize training parameters (e.g., learning rate, network size, environment settings) by editing the corresponding `.yaml` file.

**Output:** Trained models and logs are saved by default in the `models/` and `logs/` directories, respectively. You can monitor training progress using TensorBoard:

```bash
tensorboard --logdir logs
```

#### Training Results

Below is a sample reward curve from a training session, showing the model's learning progress over time:

![Training Results](train_results.png)

**Performance Comparison:**

The following table shows the performance comparison of different baseline algorithms on the MACSR task:

| Method | Average Reward per Step | Average Reward |
|--------|-------------------------|----------------|
| MAPPO  | 0.038                   | 19.24          |
| IPPO   | 0.022                  | 11.10          |
| Random | 0.009                   | 4.601          |


### Evaluating a Pre-trained Model

To evaluate the latest saved model for a given configuration, add the `--test` flag:

```bash
uv run examples/marl/example/train.py --config example/config/mappo.yaml --test
```

The evaluation script will load the most recent checkpoint from the `models/` directory and run it in a test environment without further training.


## Acknowledgements

This project is built upon the fantastic work of the [XuanCe](https://github.com/agi-brain/xuance) team. We are also grateful for the high-quality simulation environment provided by `tongsim lite`.
