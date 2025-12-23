# Training

## Environment

`CollectTask` inherits from `gymnasium.Env` and implements its standard interface specification.

To simplify the problem, the 3D scene in this project is projected onto the 2D ground and discretized to generate an occupancy grid map. Obstacles, the agent, and targets each lie on separate layers, and each layer uses one-hot encoding.

**Observation Space**

The agent’s observation includes local grid information and the relative position to the next target point.

```python
spaces.Dict(
    {
        "grid_tensor": spaces.Box(
            low=0,
            high=1,
            shape=(3, view_size, view_size),
            dtype=np.uint8,
        ),
        "target_direction": spaces.Box(
            low=np.array([-tgt_dir_max, -tgt_dir_max]),
            high=np.array([tgt_dir_max, tgt_dir_max]),
            shape=(2,),
            dtype=np.int8,
        ),
    }
)
```

`grid_tensor` represents local grid information centered on the agent with size `view_size * view_size`. `target_direction` is the relative position between the agent and the next target point.

**Action Space**

The agent’s action space has two parts: movement direction and movement step length.

```python
spaces.MultiDiscrete([4, 2])
```

The first dimension indicates the movement direction—forward, backward, left, and right. The second dimension indicates the step length on the discrete occupancy grid map; by default there are two step lengths: one cell and two cells.

**Environment Creation**

This project provides a wrapper to create the task environment. The main configuration parameters include `grpc_endpoint`, `anchor`, `max_steps`, and `render_mode`.

```python
def make_env(grpc_endpoint, anchor, max_steps=1024, render_mode=None):
    """Creates a function that initializes a CollectTask environment with the specified anchor point."""
    def _init():
        ue = ts.TongSim(grpc_endpoint=grpc_endpoint)
        return CollectTask(
            ue=ue,
            anchor=anchor,
            grid_size=para.GRID_SIZE,
            view_size=para.VIEW_SIZE,
            max_steps=max_steps,
            render_mode=render_mode,
        )
    return _init
```

`grpc_endpoint` is the configuration required to connect to the TongSIM simulation environment. If running on the same machine, it defaults to `"127.0.0.1:5726"`. TongSIM supports loading multiple sub-maps for parallelization; `anchor` is the anchor point in the world coordinate system where the current map is loaded. To ensure the sub-maps do not overlap in space, the spacing between anchors must be greater than the sub-map length/width/height.

**Environment Execution**

As with Gymnasium, after creating the environment, call `reset` to reset it. The agent then produces actions based on the observations and feeds them to the environment to obtain the next observation—repeating this interaction.

```python
with ts.TongSim(grpc_endpoint=para.GRPC_ENDPOINT) as ue:
    ue.context.sync_run(ts.UnaryAPI.reset_level(ue.context.conn))
    max_steps = 1024
    env = make_env(
        grpc_endpoint=para.GRPC_ENDPOINT,
        anchor=(0, 0, 0),
        max_steps=max_steps,
        render_mode="human",
    )()
    env = InputWrapper(env)
    obs, _ = env.reset()
    done = False
    steps = 0
    while not done:
        steps += 1
        obs, reward, terminated, truncated, info = env.step()
        done = terminated or truncated
        env.render()
        time.sleep(0.01)
```

The above code demonstrates how to run the environment using a manual control example. `InputWrapper` is a keyboard input wrapper implemented in `./common/manual.py`. Running the code starts the environment. Actions are printed to the terminal, and the agent in the simulator executes the corresponding actions.

## Training

**Step 1: Generate the Occupancy Grid Map**

Except for the agent and targets, objects in the scene remain unchanged before and after training, so you can pre-generate the environment’s occupancy grid map for subsequent training.

Generation function:

```python
async def request_global_map(
    context: WorldContext, wx: int = 512, wy: int = 512, h: int = 64
):
    start_transform = ts.Transform(location=ts.Vector3(para.ROOM_CENTER))
    voxel_bytes = await ts.UnaryAPI.query_voxel(
        context.conn,
        start_transform,
        wx,
        wy,
        h,
        ts.Vector3(para.ROOM_EXT),
    )
    vox = decode_voxel(voxel_bytes, (wx, wy, h))
    vox_flattened = np.any(vox, axis=-1, keepdims=False)
    vox_flattened_img = vox_flattened.astype(np.uint8) * 255
    Image.fromarray(vox_flattened_img).save(
        f"./examples/rl_nav/occupy_grid/global_map_{wx}.png"
    )
    return vox_flattened
```

Here, `start_transform` is the central spatial position for generating the grid, `box_extent` is the spatial range for generating the grid, `wx` is the number of grids along the x-axis, `wy` is the number along the y-axis, and `h` is the number along the z-axis.

Open the TongSIM simulation environment, select and load the map for which you want to generate the grid, run the simulation, and call the Python API to obtain the occupancy grid data. The specific calling method is as follows:

```python
    with ts.TongSim(grpc_endpoint="127.0.0.1:5726") as ue:
        ue.context.sync_run(request_global_map(ue.context, wx=512, wy=512, h=64))
```

On success, a PNG occupancy grid map will be generated under `./examples/rl_nav/occupy_grid`.

**Step 2: Configure the Model**

This project trains with the `stable_baselines3` framework. Model hyperparameters are configured as follows:

```python
def make_model(envs, last_path, tsboard_log_path):
    if last_path is not None and os.path.exists(last_path):
        print(f"[INFO] load already trained model: {last_path}")
        model = PPO.load(last_path, env=envs)
    else:
        print("[INFO] not found trained model, create a new model.")
        model = PPO(
            "MultiInputPolicy",
            envs,
            learning_rate=2e-4,
            n_steps=1024,
            batch_size=128,
            n_epochs=8,
            gamma=0.99,
            gae_lambda=0.98,
            clip_range=0.15,
            ent_coef=0.03,
            vf_coef=0.6,
            verbose=1,
            tensorboard_log=tsboard_log_path,
            # policy_kwargs=policy_kwargs,
            device="cpu",
        )

    return model
```

**Step 3: Create Parallel Environments for Training**

TongSIM natively supports parallel training. Set `env_num` as the number of parallel environments to improve sample throughput and convergence efficiency. After creating the vectorized environments, configure the model hyperparameters and start training.

```python
def train(model_name=None):
    """Trains the RL navigation model using multiple parallel environments."""
    with ts.TongSim(grpc_endpoint=para.GRPC_ENDPOINT) as ue:
        # reset level
        ue.context.sync_run(ts.UnaryAPI.reset_level(ue.context.conn))
        env_num = 25
        row_num = 5
        envs = SubprocVecEnv(
            [
                make_env(
                    grpc_endpoint=para.GRPC_ENDPOINT,
                    anchor=(x * 2000, y * 2000, 0),
                    max_steps=1024,
                    render_mode=None,
                )
                for i in range(env_num)
                for x, y in [divmod(i, row_num)]
            ]
        )
        envs = VecMonitor(envs, log_dir + "/vecmonitor_log")
        model = make_model(
            envs=envs,
            last_path=None if model_name is None else model_dir + model_name,
            tsboard_log_path=log_dir + "/tsboard_log",
        )

        checkpoint_callback = CheckpointCallback(
            save_freq=50_000 // env_num,
            save_path=model_dir,
            name_prefix="search_ppo",
        )
        try:
            model.learn(
                total_timesteps=1e9,
                callback=checkpoint_callback,
            )
        except Exception as e:
            print(f"[ERROR] error occurred while training: {e}")
            model.save(model_dir + "/search_ppo_crash")
            raise
        finally:
            model.save(model_dir + "search_ppo_final")
```

**Training Logs**

Based on the above configuration, training logs are as follows:
![Training Logs](train_log.png)
***Figure 1**. Training Logs: Average Episode Length (left), Average Episode Reward (right)*

As shown in the figures, the number of steps required by the agent to complete the task decreases over time while the reward increases. After 10M steps of training, both the step length and reward tend to converge.

## Evaluation

The main evaluation metrics are Success Rate (*SR*) and Efficiency (*E*). Success means the agent can, within the maximum number of steps, complete a sweep of the entire task space and visit all paper balls. Efficiency measures how quickly the agent completes the task and is evaluated by the number of steps—the fewer the steps, the higher the efficiency. The exact formulas for the two metrics can be found in the technical report.

After training, run:

```bash
uv run python ./examples/rl_nav/run.py test --model_name="xx.zip"
```

Replace `model_name` with your model filename. After running the evaluation script, it automatically outputs *SR* and *E*.
Using this benchmark, we evaluated the baseline model and humans. The results are as follows:

***Table 1**. Performance of Humans and the RL Model on This Task*

| Agent | *SR* |  *E* |
| :---: | :--: | :--: |
|  PPO  |  0.6 | 0.34 |
| Human |  1.0 | 0.54 |
