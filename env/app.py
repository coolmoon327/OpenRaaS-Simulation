import numpy as np

class Data(object):
    def __init__(self, id, size):
        '''Basic data class'''
        self.size = size    # Data size: MegaBytes
        self.id = id
        

class ContainerLayer(Data):
    def __init__(self, id, size, type):
        '''Container layers handled by depository worker nodes
        size: MB
        type: 0-os, 1-driver, 2-library, 3-execution, 4-compatible
        '''
        super.__init__(id, size)
        if not (0<=type<5):
            raise ValueError(f"Input type {type} is out of range!")
        self.type_num = type
        self.hosts = [] # host devices which store this layer

    def type(self):
        if self.type_num == 0:
            print("os")
        elif self.type_num == 1:
            print("driver")
        elif self.type_num == 2:
            print("library")
        elif self.type_num == 3:
            print("execution")
        elif self.type_num == 4:
            print("compatible")

class Application(Data):
    def __init__(self, id, size):
        '''Application files stored on filestore worker nodes'''
        super.__init__(id, size)
        self.env_layers: list[ContainerLayer] = []
        self.hosts = [] # host devices which store this application

class LayerList(object):
    layers: list[ContainerLayer] = []  # store all layers, and sort by id
    os_layers: list[ContainerLayer] = []
    driver_layers: list[ContainerLayer] = []
    lib_layers: list[ContainerLayer] = []
    exec_layers: list[ContainerLayer] = []
    compatible_layers: list[ContainerLayer] = []
    
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
    
    
class ApplicationList(object):
    apps: list[Application] = [] # store all applications, and sort by id
    process_apps: list[Application] = []
    storage_apps: list[Application] = []
    desktop_apps: list[Application] = []
    
    @ classmethod
    def init_apps(cls):
        LayerList.init_layers() # only can init once!
        index = 0
        # processing
        for _ in range(30):
            app = Application(index, 500.)
            osl = LayerList.os_layers[np.random.randint(0,3)]
            dl = LayerList.driver_layers[np.random.randint(1,5)]
            ll = LayerList.lib_layers[np.random.randint(4,8)]
            app.env_layers = [osl, dl, ll]
            cls.process_apps.append(app)
            index += 1
        # storage
        app = Application(index, 0.)
        osl = LayerList.os_layers[0]
        dl = LayerList.driver_layers[0]
        ll = LayerList.lib_layers[0]
        el = LayerList.exec_layers[0]
        app.env_layers = [osl, dl, ll, el]
        cls.storage_apps.append(app)
        index += 1
        # desktop
        for _ in range(20):
            size = max(5000 + 1000 * np.random.randn(1)[0], 1.)     # 2000 ~ 8000 MB
            app = Application(index, size)
            osl = LayerList.os_layers[1]
            dl = LayerList.driver_layers[1]
            ll = LayerList.lib_layers[np.random.randint(1,4)]
            cl = LayerList.lib_layers[0]
            app.env_layers = [osl, dl, ll, cl]
            cls.desktop_apps.append(app)
            index += 1
        
        cls.apps = cls.process_apps + cls.storage_apps + cls.desktop_apps
        if cls.apps.__len__() != index:
            raise ValueError(f"The app list length {cls.apps.__len__()} is not equal to the total app number {index}")
    
    @classmethod
    def get_arbitrary_application(cls, app_type=-1):
        '''get an application from the list
        app_type indicates the application type: 0-processing, 1-storage, 2-desktop
        storage app (1) only return the fixed result
        '''
        if app_type == -1:
            app_type = np.random.randint(0, 3)
        if cls.apps.__len__() == 0:
            cls.init_apps() # here is initialization, remember not to init twice
        if app_type == 0:
            applist = cls.process_apps
        elif app_type == 1:
            applist = cls.storage_apps
        elif applist == 2:
            applist = cls.desktop_apps
        else:
            raise ValueError(f"Input app_type {app_type} is out of range!")
        
        num = applist.__len__()
        
        index = np.random.randint(0, num)
        return applist[index]