import numpy as np

class Data(object):
    def __init__(self, size):
        '''Basic data class'''
        self.size = size    # Data size: MegaBytes
        

class ContainerLayer(Data):
    def __init__(self, size):
        '''Container layers handled by depository worker nodes'''
        super.__init__(size)
        

class Application(Data):
    def __init__(self, size):
        '''Application files stored on filestore worker nodes'''
        super.__init__(size)