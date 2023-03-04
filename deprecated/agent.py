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
        
        # Algorithm
        self.alg = OPGreedy()
        
        # Logger
        log_path = f"{log_dir}/simulation"
        self.logger = Logger(log_path)
    
    def run(self):
        env = self.env_wrapper
        config = self.config
        
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
                num = state.__len__()
                tasks_info = []         # (num, task_info_num)
                compute_info = []       # (num, 2)
                all_cand_num = []       # (num, 1)
                top_cand_info = []      # (num, candidates_num, filestore_info_num)
                true_candidates_num = [candidates_num for _ in range(num)]
                
                for n in range(num):
                    self.temp_point = 0
                    tasks_info.append(get_state_clip(state[n], task_info_num))
                    compute_info.append(get_state_clip(state[n], 2))
                    all_cand_num.append(get_state_clip(state[n], 1))
                    candidates = get_state_clip(state[n], filestore_info_num * candidates_num)
                    sepeated_cand_info = []
                    for i in range(candidates_num):
                        info = candidates[i * filestore_info_num : (i+1) * filestore_info_num]
                        if np.sum(info) == -3.:
                            true_candidates_num[n] = i
                            break
                        sepeated_cand_info.append(info)
                    top_cand_info.append(sepeated_cand_info)
                
                # tasks_info = np.array(tasks_info)
                # compute_info = np.array(compute_info)
                # all_cand_num = np.array(all_cand_num)
                # top_cand_info = np.array(top_cand_info)
                
                # 2. gain action
                actions = []
                for i in range(num):
                    if compute_info[i][0] == -1. or true_candidates_num[i] == 0:
                        actions.append(-1)
                        continue
                    bws = [top_cand_info[i][j][0] for j in range(true_candidates_num[i])]
                    ls = [top_cand_info[i][j][1] for j in range(true_candidates_num[i])]
                    js = [top_cand_info[i][j][2] for j in range(true_candidates_num[i])]
                    a = self.alg.get_action(compute_info[i][1], bws, ls, js)
                    actions.append(a)
            
                actions = np.array(actions)
                
                # 3. go into next step
                state, reward, _ = env.step(actions)
                
                print(f"E{episode}S{step}: reward={np.mean(reward)}")