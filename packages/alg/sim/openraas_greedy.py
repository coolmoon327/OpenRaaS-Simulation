import numpy as np
from ..utils import *

class OPGreedy(object):
    def __init__(self):
        pass
    
    def get_action(self, compute_bandwidth, candidates_bandwidth, candidates_latency, candidates_jilter):
        """select a candidate via simple greedy strategy

        Args:
            compute_bandwidth (float)
            candidates_bandwidth (list)
            candidates_latency (list)
            candidates_jilter (list)

        Returns:
            int: the selection index of given candidates
        """
        
        # 1. sort by estimated link latency and  pick the top candidates
        num = len(candidates_bandwidth)
        link_bd = [min(compute_bandwidth, candidates_bandwidth[i]) for i in range(num)]
        top_bd = get_top_keys([i for i in range(num)], link_bd)
        
        # if several worksers remains, find the one with lowest latency and jilter
        if len(top_bd) > 1:
            nl = [-candidates_latency[i] for i in top_bd]
            top_l = get_top_keys(top_bd, nl)
            
            if len(top_l) > 1:
                nj = [-candidates_jilter[i] for i in top_l]
                top_j = get_top_keys(top_l, nj)
                ans = top_j[0]
            else:
                ans = top_l[0]
        
        else:
            ans = top_bd[0]
        
        return ans