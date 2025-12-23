import gymnasium as gym


class InputWrapper(gym.Wrapper):
    def __init__(self, env):
        super().__init__(env)

    def get_action(self):
        space = self.env.action_space

        if isinstance(space, gym.spaces.Discrete):
            while True:
                try:
                    action = int(input(f"please input action [0-{space.n - 1}]: "))
                    if action in range(space.n):
                        return action
                    print("⚠️ illegal action, please input again.")
                except ValueError:
                    print("⚠️ must be integer input.")

        elif isinstance(space, gym.spaces.MultiDiscrete):
            action = []
            for i, n in enumerate(space.nvec):
                while True:
                    try:
                        val = int(
                            input(
                                f"please input the {i}th dimension action [0-{n - 1}]: "
                            )
                        )
                        if val in range(n):
                            action.append(val)
                            break
                        print("⚠️ illegal action, please input again.")
                    except ValueError:
                        print("⚠️ must be integer input.")
            return action

        else:
            raise NotImplementedError(f"unsupported action space: {type(space)}")

    def step(self, action=None):
        action = self.get_action()
        obs, reward, terminated, truncated, info = self.env.step(action)
        self.env.render()
        return obs, reward, terminated, truncated, info


if __name__ == "__main__":
    env = gym.make("CartPole-v1", render_mode="human")
    env = InputWrapper(env)

    obs, info = env.reset()
    done = False
    while not done:
        obs, reward, terminated, truncated, info = env.step()
        done = terminated or truncated

    env.close()
