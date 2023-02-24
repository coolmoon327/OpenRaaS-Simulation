from .openraas.environment import *
import numpy as np

class EnvWrapper:
    def __init__(self, config={}):
        self.config = config
        self.env = Environment(config)

    def reset(self):
        state = self.env.reset()
        return state

    def seed(self, seed):
        self.env.seed(seed)
        
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
        next_state, reward = self.env.step(action)
        terminal = 0
        if self.config['get_statistics']:
            self.statistic()
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
    
    def statistic(self):
        env = self.env
        M = self.config['M']

        served_percent = env.served_percent
        
        occupation = [[],[],[]]
        for device in env.devices:
            if device.is_worker:
                for i in range(3):
                    occupation[i].append(device.idle_resource_occupation_rate(i))
        
        ave_ocp = [np.mean(occupation[0]), np.mean(occupation[1]), np.mean(occupation[2])]
        
        print(f"Serverd percent: {served_percent}, average worker occupation: {ave_ocp}")