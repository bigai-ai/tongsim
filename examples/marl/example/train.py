import argparse

import xuance


def main():
    parser = argparse.ArgumentParser(description="Run XuanCe framework.")
    parser.add_argument("--method", type=str, default="mappo", help="The RL method to use (e.g., mappo, ippo).")
    parser.add_argument(
        "--config", type=str, default="examples/marl/example/config/mappo.yaml", help="Path to the configuration file."
    )
    parser.add_argument("--env", type=str, default="UeMACS", help="The environment type.")
    parser.add_argument("--env_id", type=str, default="MACS-v1", help="The specific environment ID.")
    parser.add_argument("--test", action="store_true", help="Run in test mode.")
    parser.add_argument(
        "--load_model_path", type=str, default=None, help="Path to a specific model to load for testing."
    )

    args = parser.parse_args()

    runner = xuance.get_runner(
        method=args.method, env=args.env, env_id=args.env_id, config_path=args.config, is_test=args.test
    )

    if args.test:
        if args.load_model_path:
            runner.run(filter_prefix=[args.load_model_path])
        else:
            runner.run()  # Load the model from the most recent experiment by default
    else:
        print("Train")
        # runner.run()
        runner.benchmark()


if __name__ == "__main__":
    main()
