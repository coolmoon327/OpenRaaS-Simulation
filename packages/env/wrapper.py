from .openraas.environment import *

class EnvWrapper:
    def __init__(self, config={}):
        self.env = Environment(config)

    def reset(self):
        self.env.reset()
        self.env.next()
        state = self.env.get_state()
        return state

    def get_random_action(self):
        action = self.env.action_space.sample()
        return action

    def step(self, action):
        """step into next state with the input action executed

        Args:
            action (np.array)

        Returns:
            state (np.array)
        """
        # next_state, reward, terminal, _ = self.env.step(action.ravel())
        self.env.step(action)
        next_state = self.env.get_state()
        reward = 0
        terminal = 0
        return next_state, reward, terminal

    def set_random_seed(self, seed):
        self.env.seed(seed)

    def render(self):
        # frame = self.env.render(mode='rgb_array')
        # return frame
        pass

    def close(self):
        # self.env.close()
        pass

    def get_action_space(self):
        return self.env.action_space

    def normalise_state(self, state):
        return state

    def normalise_reward(self, reward):
        return reward