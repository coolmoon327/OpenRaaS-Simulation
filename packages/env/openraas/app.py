import numpy as np

'''data.type
-1: not set
0: os layer
1: driver layer
2: library layer
3: execution layer
4: compatible layer
10: processing app
11: storage app
12: desktop app
'''

class Data(object):
    def __init__(self, id, size):
        '''Basic data class'''
        self.size = size    # Data size: MegaBytes
        self.id = id
        self.hosts = []     # IDs of host devices storing this data
        self.type = -1
    
    def add_host(self, host_id: int):
        if host_id in self.hosts:
            raise ValueError(f"Host {host_id} is already existing!")
        self.hosts.append(host_id)
    
    def remove_host(self, host_id: int):
        if host_id not in self.hosts:
            raise ValueError(f"Host {host_id} isn't existing!")
        self.hosts.remove(host_id)
    
    def print_type(self):
        return "basic data"


class ContainerLayer(Data):
    def __init__(self, id, size, type):
        '''Container layers handled by depository worker nodes
        size: MB
        type: 0-os, 1-driver, 2-library, 3-execution, 4-compatible
        '''
        super().__init__(id, size)
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
    def __init__(self, id, size, type):
        '''Application files stored on filestore worker nodes
        type: 10-process, 11-storage, 12-desktop
        '''
        if type<10:
            type += 10
        if not (10<=type<13):
            raise ValueError(f"Input type {type} is out of range!")
        super().__init__(id, size)
        self.type = type
        self.env_layers: list[ContainerLayer] = []
    
    def print_type(self):
        if self.type == 10:
            return "processing app"
        elif self.type == 11:
            return "storage app"
        elif self.type == 12:
            return "desktop app"


class LayerList(object):
    layer_num: int
    
    def __init__(self):
        self.layers = []  # store all layers, and sort by id
        self.os_layers = []
        self.driver_layers = []
        self.lib_layers = []
        self.exec_layers = []
        self.compatible_layers = []
        self.type_num = 5
        self.init_layers()
    
    def init_layers(self):
        index = 0
        # OS layers
        for _ in range(3):
            self.os_layers.append(ContainerLayer(index, 100, 0)) # os_layers[0] for storage & processing, 1 for processing & desktop, 2 for processing
            index += 1
            
        # driver layers
        self.driver_layers.append(ContainerLayer(index, 50, 1)) # driver_layers[0] for storage
        index += 1
        for _ in range(4):
            self.driver_layers.append(ContainerLayer(index, 200, 1)) # driver_layers[1] for desktop & processing, 2 3 4 for processing
            index += 1
            
        # library layers
        self.lib_layers.append(ContainerLayer(index, 50, 2)) # lib_layers[0] for storage
        index += 1
        for _ in range(3):
            self.lib_layers.append(ContainerLayer(index, 200, 2)) # lib_layers[1~3] for desktop,
            index += 1
        for _ in range(4):
            self.lib_layers.append(ContainerLayer(index, 100, 2)) # lib_layers[4~7] for processing
            index += 1
        
        # execution layers
        self.exec_layers.append(ContainerLayer(index, 10, 3)) # exec_layers[0] for storage
        index += 1
        
        # compatible layers
        self.compatible_layers.append(ContainerLayer(index, 500, 4)) # compatible_layers[0] for desktop
        index += 1
        
        self.layers = self.os_layers + self.driver_layers + self.lib_layers + self.exec_layers + self.compatible_layers
        LayerList.layer_num = self.layers.__len__()
        if LayerList.layer_num != index:
            raise ValueError(f"The layer list length {self.layers.__len__()} is not equal to the total sublayers number {index}")
    
    def get_arbitrary_data(self, layer_type=-1):
        '''get an layer from the list
        layer_type indicates the layer type (default -1 to random in the whole list)
        '''
        layerlist = self.get_list(layer_type)
        num = layerlist.__len__()
        
        index = np.random.randint(0, num)
        return layerlist[index]
    
    def get_next_data(self, data):
        index = data.id + 1
        if index >= self.layers.__len__():
            return self.layers[0]
        return self.layers[index]
    
    def get_list(self, layer_type=-1):
        '''
        -1: all
        0: os
        1: driver
        2: library
        3: execution
        4: compatible
        '''

        if layer_type == -1:
            # layer_type = np.random.randint(0, 3)
            layerlist = self.layers
        elif layer_type == 0:
            layerlist = self.os_layers
        elif layer_type == 1:
            layerlist = self.driver_layers
        elif layer_type == 2:
            layerlist = self.lib_layers
        elif layer_type == 3:
            layerlist = self.exec_layers
        elif layer_type == 4:
            layerlist = self.compatible_layers
        else:
            raise ValueError(f"Input layer_type {layer_type} is out of range!")
        return layerlist
    
    def get_data_by_id(self, id):   
        if not (0 <= id < self.layers.__len__()):
            raise IndexError(f"The input id {id} is out of range!")
        return self.layers[id]
    
    def reset(self):
        self.layers.clear()
        self.os_layers.clear()
        self.driver_layers.clear()
        self.lib_layers.clear()
        self.exec_layers.clear()
        self.compatible_layers.clear()
    
    
class ApplicationList(object):
    app_num: int
    
    def __init__(self, layerList):
        self.apps = [] # store all applications, and sort by id
        self.process_apps = []
        self.storage_apps = []
        self.desktop_apps = []
        self.type_num = 3
        self.layerList = layerList
        self.init_apps()
    
    def init_apps(self):
        index = 0
        # processing
        for _ in range(30):
            app = Application(index, 500., 10)
            osl = self.layerList.get_list(0)[np.random.randint(0,3)]
            dl = self.layerList.get_list(1)[np.random.randint(1,5)]
            ll = self.layerList.get_list(2)[np.random.randint(4,8)]
            app.env_layers = [osl, dl, ll]
            self.process_apps.append(app)
            index += 1
        # storage
        # every compatible worker can become a storage filestore, so every device has this app
        app = Application(index, 0., 11)
        osl = self.layerList.get_list(0)[0]
        dl = self.layerList.get_list(1)[0]
        ll = self.layerList.get_list(2)[0]
        el = self.layerList.get_list(3)[0]
        app.env_layers = [osl, dl, ll, el]
        self.storage_apps.append(app)
        index += 1
        # desktop
        for _ in range(20):
            size = max(5000 + 1000 * np.random.randn(1)[0], 1.)     # 2000 ~ 8000 MB
            app = Application(index, size, 12)
            osl = self.layerList.get_list(0)[1]
            dl = self.layerList.get_list(1)[1]
            ll = self.layerList.get_list(2)[np.random.randint(1,4)]
            cl = self.layerList.get_list(4)[0]
            app.env_layers = [osl, dl, ll, cl]
            self.desktop_apps.append(app)
            index += 1
        
        self.apps = self.process_apps + self.storage_apps + self.desktop_apps
        ApplicationList.app_num = self.apps.__len__()
        if ApplicationList.app_num != index:
            raise ValueError(f"The app list length {self.apps.__len__()} is not equal to the total app number {index}")
    
    def get_arbitrary_data(self, app_type=-1):
        '''get an application from the list
        app_type indicates the application type: 0-processing, 1-storage, 2-desktop (default -1 to random in the whole list)
        storage app (1) only return the fixed result
        '''
        applist = self.get_list(app_type)
        num = applist.__len__()
        
        index = np.random.randint(0, num)
        return applist[index]

    def get_next_data(self, data):
        index = data.id + 1
        if index >= self.apps.__len__():
            return self.apps[0]
        return self.apps[index]
    
    def get_list(self, app_type=-1):
        '''
        -1: all
        0: processing
        1: storage
        2: desktop
        '''
        if app_type == -1:
            # app_type = np.random.randint(0, 3)
            applist = self.apps
        elif app_type == 0:
            applist = self.process_apps
        elif app_type == 1:
            applist = self.storage_apps
        elif app_type == 2:
            applist = self.desktop_apps
        else:
            raise ValueError(f"Input app_type {app_type} is out of range!")
        return applist
    
    def get_data_by_id(self, id):
        if not (0 <= id < self.apps.__len__()):
            raise IndexError(f"The input id {id} is out of range!")
        return self.apps[id]
    
    def reset(self):
        self.apps.clear()
        self.process_apps.clear()
        self.storage_apps.clear()
        self.desktop_apps.clear()
    