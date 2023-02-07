import numpy as np

'''data.type
-1: not set
0: os layer
1: driver layer
2: library layer
3: execution layer
4: compatible layer
10: app
'''

class Data(object):
    def __init__(self, id, size):
        '''Basic data class'''
        self.size = size    # Data size: MegaBytes
        self.id = id
        self.hosts = []     # IDs of host devices storing this data
        self.type = -1
    
    def add_host(self, host_id: int):
        self.hosts.append(host_id)
    
    def print_type(self):
        return "basic data"


class ContainerLayer(Data):
    def __init__(self, id, size, type):
        '''Container layers handled by depository worker nodes
        size: MB
        type: 0-os, 1-driver, 2-library, 3-execution, 4-compatible
        '''
        super.__init__(id, size)
        if not (0<=type<5):
            raise ValueError(f"Input type {type} is out of range!")
        self.type = type

    def print_type(self):
        if self.type == 0:
            return "os"
        elif self.type == 1:
            return "driver"
        elif self.type == 2:
            return "library"
        elif self.type == 3:
            return "execution"
        elif self.type == 4:
            return "compatible"


class Application(Data):
    def __init__(self, id, size):
        '''Application files stored on filestore worker nodes'''
        super.__init__(id, size)
        self.type = 10
        self.env_layers: list[ContainerLayer] = []
    
    def print_type(self):
        return "app"


class LayerList(object):
    layers: list[ContainerLayer] = []  # store all layers, and sort by id
    os_layers: list[ContainerLayer] = []
    driver_layers: list[ContainerLayer] = []
    lib_layers: list[ContainerLayer] = []
    exec_layers: list[ContainerLayer] = []
    compatible_layers: list[ContainerLayer] = []
    type_num = 5
    
    @classmethod
    def init_layers(cls):
        index = 0
        # OS layers
        for _ in range(3):
            cls.os_layers.append(ContainerLayer(index, 100, 0)) # os_layers[0] for storage & processing, 1 for processing & desktop, 2 for processing
            index += 1
            
        # driver layers
        cls.driver_layers.append(ContainerLayer(index, 50, 1)) # driver_layers[0] for storage
        index += 1
        for _ in range(4):
            cls.driver_layers.append(ContainerLayer(index, 200, 1)) # driver_layers[1] for desktop & processing, 2 3 4 for processing
            index += 1
            
        # library layers
        cls.lib_layers.append(ContainerLayer(index, 50, 2)) # lib_layers[0] for storage
        index += 1
        for _ in range(3):
            cls.lib_layers.append(ContainerLayer(index, 200, 2)) # lib_layers[1~3] for desktop,
            index += 1
        for _ in range(4):
            cls.lib_layers.append(ContainerLayer(index, 100, 2)) # lib_layers[4~7] for processing
            index += 1
        
        # execution layers
        cls.exec_layers.append(ContainerLayer(index, 10, 3)) # exec_layers[0] for storage
        index += 1
        
        # compatible layers
        cls.compatible_layers.append(ContainerLayer(index, 500, 4)) # compatible_layers[0] for desktop
        index += 1
        
        cls.layers = cls.os_layers + cls.driver_layers + cls.exec_layers + cls.compatible_layers
        if cls.layers.__len__() != index:
            raise ValueError(f"The layer list length {cls.layers.__len__()} is not equal to the total sublayers number {index}")
    
    @classmethod
    def get_arbitrary_data(cls, layer_type=-1):
        '''get an layer from the list
        layer_type indicates the layer type (default -1 to random in the whole list)
        '''
        layerlist = cls.get_list(layer_type)
        num = layerlist.__len__()
        
        index = np.random.randint(0, num)
        return layerlist[index]
    
    @classmethod
    def get_list(cls, layer_type=-1):
        '''
        -1: all
        0: os
        1: driver
        2: library
        3: execution
        4: compatible
        '''
        if cls.layers.__len__() == 0:
            cls.init_layers() # here is initialization, remember not to init twice
        
        if layer_type == -1:
            # layer_type = np.random.randint(0, 3)
            layerlist = cls.layers
        elif layer_type == 0:
            layerlist = cls.os_layers
        elif layer_type == 1:
            layerlist = cls.driver_layers
        elif layer_type == 2:
            layerlist = cls.lib_layers
        elif layer_type == 3:
            layerlist = cls.exec_layers
        elif layer_type == 4:
            layerlist = cls.compatible_layers
        else:
            raise ValueError(f"Input layer_type {layer_type} is out of range!")
        return layerlist
    
    @classmethod
    def get_data_by_id(cls, id):
        if cls.layers.__len__() == 0:
            cls.init_layers()
            
        if not (0 <= id < cls.layers.__len__()):
            raise IndexError(f"The input id {id} is out of range!")
        return cls.layers[id]
    
    
class ApplicationList(object):
    apps: list[Application] = [] # store all applications, and sort by id
    process_apps: list[Application] = []
    storage_apps: list[Application] = []
    desktop_apps: list[Application] = []
    type_num = 3
    
    @classmethod
    def init_apps(cls):
        index = 0
        # processing
        for _ in range(30):
            app = Application(index, 500.)
            osl = LayerList.get_list(0)[np.random.randint(0,3)]
            dl = LayerList.get_list(1)[np.random.randint(1,5)]
            ll = LayerList.get_list(2)[np.random.randint(4,8)]
            app.env_layers = [osl, dl, ll]
            cls.process_apps.append(app)
            index += 1
        # storage
        app = Application(index, 0.)
        osl = LayerList.get_list(0)[0]
        dl = LayerList.get_list(1)[0]
        ll = LayerList.get_list(2)[0]
        el = LayerList.get_list(3)[0]
        app.env_layers = [osl, dl, ll, el]
        cls.storage_apps.append(app)
        index += 1
        # desktop
        for _ in range(20):
            size = max(5000 + 1000 * np.random.randn(1)[0], 1.)     # 2000 ~ 8000 MB
            app = Application(index, size)
            osl = LayerList.get_list(0)[1]
            dl = LayerList.get_list(1)[1]
            ll = LayerList.get_list(2)[np.random.randint(1,4)]
            cl = LayerList.get_list(4)[0]
            app.env_layers = [osl, dl, ll, cl]
            cls.desktop_apps.append(app)
            index += 1
        
        cls.apps = cls.process_apps + cls.storage_apps + cls.desktop_apps
        if cls.apps.__len__() != index:
            raise ValueError(f"The app list length {cls.apps.__len__()} is not equal to the total app number {index}")
    
    @classmethod
    def get_arbitrary_data(cls, app_type=-1):
        '''get an application from the list
        app_type indicates the application type: 0-processing, 1-storage, 2-desktop (default -1 to random in the whole list)
        storage app (1) only return the fixed result
        '''
        applist = cls.get_list(app_type)
        num = applist.__len__()
        
        index = np.random.randint(0, num)
        return applist[index]

    @classmethod
    def get_list(cls, app_type=-1):
        '''
        -1: all
        0: processing
        1: storage
        2: desktop
        '''
        if cls.apps.__len__() == 0:
            cls.init_apps() # here is initialization, remember not to init twice
        
        if app_type == -1:
            # app_type = np.random.randint(0, 3)
            applist = cls.apps
        elif app_type == 0:
            applist = cls.process_apps
        elif app_type == 1:
            applist = cls.storage_apps
        elif applist == 2:
            applist = cls.desktop_apps
        else:
            raise ValueError(f"Input app_type {app_type} is out of range!")
        return applist
    
    @classmethod
    def get_data_by_id(cls, id):
        if cls.apps.__len__() == 0:
            cls.init_apps()
            
        if not (0 <= id < cls.apps.__len__()):
            raise IndexError(f"The input id {id} is out of range!")
        return cls.apps[id]