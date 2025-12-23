"""Main file to run training and testing for RL navigation tasks."""

import run

if __name__ == "__main__":
    # run.train(model_name="search_ppo_10000000_steps.zip")
    run.test(model_name="search_ppo_10000000_steps.zip")
    # run.manual()
