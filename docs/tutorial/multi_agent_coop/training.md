## Usage

### Training a New Model

To train a new model, specify the algorithm's configuration file. For example, to train MAPPO:

```bash
uv run examples/marl/example/train.py  --config examples/marl/example/config/mappo.yaml  --method mappo
```

> **Tip**: To reduce memory usage during training, it is highly recommended to disable unnecessary logs in the Unreal Engine console (press `` ` `` to open) by running:
> ```bash
> log LogTemp off
> log LogTongSimGRPC off
> ```

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

The following table shows the performance comparison of different baseline algorithms on the MACS task. Note that due to the inherent stochasticity of multi-agent environments, the reported performance metrics may exhibit minor fluctuations; these results are primarily intended to verify the effectiveness of the environment and provide a baseline for comparison.

| Method | Average Reward per Step | Average Reward |
|--------|-------------------------|----------------|
| MAPPO  | 0.038                   | 19.24          |
| IPPO   | 0.030                  | 14.75         |
| Random | -0.013                   | -6.51          |


### Evaluating a Pre-trained Model

To evaluate the latest saved model for a given configuration, add the `--test` flag:

```bash
uv run examples/marl/example/train.py  --config examples/marl/example/config/mappo.yaml --test --method mappo
```

The evaluation script will load the most recent checkpoint from the `models/` directory and run it in a test environment without further training.
