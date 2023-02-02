import numpy as np

class Task(object):
    def __init__(self, cpu, mem):
        self.cpu = cpu
        self.mem = mem
        
    def bandwidth(self):
        '''return bandwidth occupation
        be care the unit of network is Mb while that of memory is MB
        '''
        return 8
        

# for storage service, task.mem is the file number multiply 50 MB