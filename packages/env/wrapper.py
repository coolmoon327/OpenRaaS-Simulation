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
        next_state, reward, next_slot = self.env.step(action)
        if self.config['get_statistics']:
            self.statistic(next_slot)
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
    
    def statistic(self, print_last_record=False):
        if print_last_record:
            print(f"Serverd percent: {self.served_percent}, average worker occupation: {self.ave_ocp}")
            
        env = self.env

        self.served_percent = env.served_num / env.tasks_num
        
        occupation = [[],[],[]]
        for device in env.workers:
            for i in range(3):
                occupation[i].append(device.idle_resource_occupation_rate(i))
        
        self.ave_ocp = [np.mean(occupation[0]), np.mean(occupation[1]), np.mean(occupation[2])]