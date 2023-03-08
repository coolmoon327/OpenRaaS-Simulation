from ..env.wrapper import *
from ..utils.logger import Logger
from .sim.openraas_greedy import *

class SimulationAgent(object):
    def __init__(self, config, log_dir=''):
        self.config = config
        self.max_episodes = config["num_ep_train"]
        self.max_steps = config['max_ep_length']
        
        # Environment
        self.env_wrapper = EnvWrapper(config)
        self.env_wrapper.seed(config['seed'])
        
        # Algorithm
        self.alg = OPGreedy()
        
        # Logger
        log_path = f"{log_dir}/simulation"
        self.logger = Logger(log_path)
    
    def run(self):
        env = self.env_wrapper
        config = self.config
        
        logs = []

        def get_state_clip(s, length):
            # reset self.temp_point beforing using this function
            begin = self.temp_point
            end = begin + length
            self.temp_point = end
            return s[begin:end]
        
        for episode in range(self.max_episodes):
            state = env.reset()
            
            for step in range(self.max_steps):
                task_info_num = config['task_info_num']
                filestore_info_num = config['filestore_info_num']
                candidates_num = config['candidates_num']
                
                # 1. modify state
                self.temp_point = 0
                tasks_info = get_state_clip(state, task_info_num)
                compute_info = get_state_clip(state, 2)
                all_cand_num = get_state_clip(state, 1)
                candidates = get_state_clip(state, filestore_info_num * candidates_num)
                
                real_candidates_num = candidates_num
                arranged_candidates_info = []      # (candidates_num, filestore_info_num)
                for i in range(candidates_num):
                    info = candidates[i * filestore_info_num : (i+1) * filestore_info_num]
                    if np.sum(info) == -3.:
                        real_candidates_num = i
                        break
                    arranged_candidates_info.append(info)
                
                
                # 2. gain action
                action = -1
                if compute_info[0] != -1. and real_candidates_num:
                    bws = [arranged_candidates_info[j][0] for j in range(real_candidates_num)]
                    ls = [arranged_candidates_info[j][1] for j in range(real_candidates_num)]
                    js = [arranged_candidates_info[j][2] for j in range(real_candidates_num)]
                    action = self.alg.get_action(compute_info[1], bws, ls, js)
                
                # 3. go into next step
                state, reward, _ = env.step(action)
                
                # if step % 100 == 0:
                #     print(f"E{episode}S{step}: reward={reward}")
            if config['get_statistics']:
                logs.append(env.log_episode_statistics())
        
        mean_logs = {}
        if config['get_statistics']:
            for key in logs[0]:
                mean_logs[key] = np.mean([logs[i][key] for i in range(len(logs))])

        return mean_logs