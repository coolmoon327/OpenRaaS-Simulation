import numpy as np
from .device import *

class Line(object):
    def __init__(self, bandwidth, latency, jilter):
        self.bandwidth = bandwidth  # MBps
        self.latency = latency      # ms
        self.jilter = jilter        # mean jilter times in a slot
        
        self.occupied_time = 0.     # the fully occupied time interval in this slot
        # in each slot, first serve those tasks with long span, and then using all bandwidth for data transfer tasks one by one
        # but we do not care about the left bandwidth (4-3-5, left 1-0-2) for easy 

    def get_jilter(self):
        ans = max(self.jilter + self.jilter/3 * np.random.randn(1)[0], 0.)  # 0 ~ 2 mean_jilter
        return ans

class Area(object):
    def __init__(self, id):
        self.id = id
        self.devices: list[int] = []    # devices' IDs
        self.lines: list[Line] = []     # devices' lines with respect to self.devices
        self.reset()
    
    def reset(self):
        self.devices.clear()
        self.lines.clear()
        
        bw = max(300 + 100 * np.random.randn(1)[0], 1.)*1000/8 # (1 ~ 500)/8 GBps
        l = max(10 + 3 * np.random.randn(1)[0], 1.) # 1 ~ 19 ms
        j = max(5 + 1 * np.random.randn(1)[0], 0) # 2 ~ 8
        self.backbone = Line(bw, l, j)

    def add_device(self, type: int, device_id: int, bandwidth=0):
        """
        The property type indicates the wire or wireless device: 0-wire, 1-wireless.
        Bandwidth is the network interface bandwith of the device.
        """
        if type == 0:
            l = max(3 + 1 * np.random.randn(1)[0], 1.) # wire 1 ~ 6 ms
            j = max(4 + 1 * np.random.randn(1)[0], 0) # 1 ~ 7
        elif type == 1:
            l = max(7 + 2 * np.random.randn(1)[0], 1.) # wireless 1 ~ 13 ms
            j = max(6 + 2 * np.random.randn(1)[0], 0) # 0 ~ 12
        else:
            raise ValueError(f"The input line type {type} is out of range!")
        
        self.devices.append(device_id)
        self.lines.append(Line(bandwidth, l, j))
        
    def update_bandwidth(self, device_id: int, bandwidth):
        """We should update bandwidth information once changed."""
        i = self.devices.index(device_id)
        self.lines[i].bandwidth = bandwidth
    

class Topology(object):
    def __init__(self, area_num):
        self.area_num = area_num
        self.areas: list[Area] = [Area(i) for i in range(area_num)]
        self.device_to_area = {}    # key: device id, value: area id
        self.reset()
        
    def reset(self):
        for area in self.areas:
            area.reset()
    
    def get_area_by_device_id(self, device_id: int):
        return self.areas[self.device_to_area[device_id]]
    
    def get_area_by_device(self, device: Device):
        return self.get_area_by_device_id(device.id)
    
    def get_device_interface_link_by_id(self, device_id: int):
        area = self.get_area_by_device_id(device_id)
        return area.lines[area.devices.index(device_id)]
    
    def get_device_interface_link(self, device: Device):
        self.get_device_interface_link_by_id(device.id)
    
    def add_device(self, device: Device, area_id=-1):
        if area_id == -1:
            area_id = np.random.randint(0, self.area_num)
        type = 0 if device.print_type() == 'server' else 1
        self.areas[area_id].add_device(type, device.id, device.bw)
        self.device_to_area[device.id] = area_id
    
    def transmit_between_devices(self, device1: Device, device2: Device, datasize):
        """update the bandwidth occupation

        Args:
            device1 (Device): device 1
            device2 (Device): device 2
            datasize (float): size of the transmitted file (MB)
        
        Returns:
            speed: minimum bandwith on the link
            latency: total latency
            jilter: total sampledd jilters
        
        """
        if datasize == 0 or device1 == device2:
            return
        
        a1 = self.get_area_by_device_id(device1.id)
        a2 = self.get_area_by_device_id(device2.id)
        i1 = self.get_device_interface_link_by_id(device1.id)
        i2 = self.get_device_interface_link_by_id(device2.id)
        
        if i1.bandwidth != device1.bw or i2.bandwidth != device2.bw:
            raise ValueError(f"The link bandwidth is not equal to the interface's.")
        
        i1.bandwidth -= datasize
        i2.bandwidth -= datasize
        device1.bw = i1.bandwidth
        device2.bw = i2.bandwidth
        
        if a1 != a2:
            a1.backbone.bandwidth -= datasize
            a2.backbone.bandwidth -= datasize

        if i1.bandwidth < 0 or i2.bandwidth < 0 or a1.backbone.bandwidth < 0 or a2.backbone.bandwidth < 0:
            raise ValueError(f"Negative bandwidth.")
        
    def release_between_devices(self, device1: Device, device2: Device, datasize):
        return self.transmit_between_devices(device1, device2, -datasize)
    
    def get_link_states_between_devices_by_id(self, d1: int, d2: int):
        """get link states between d1 and d2

        Args:
            d1 (int): device 1 id
            d2 (int): device 2 id
        
        Returns:
            speed: minimum bandwith on the link
            latency: total latency
            jilter: total sampledd jilters
        
        """
        a1 = self.get_area_by_device_id(d1)
        a2 = self.get_area_by_device_id(d2)
        i1 = self.get_device_interface_link_by_id(d1)
        i2 = self.get_device_interface_link_by_id(d2)
        
        speed = min(i1.bandwidth, i2.bandwidth)
        latency = i1.latency + i2.latency
        jilter = i1.get_jilter() + i2.get_jilter()
        if a1 != a2:
            speed = min(speed, a1.backbone.bandwidth)
            speed = min(speed, a2.backbone.bandwidth)
            latency += a1.backbone.latency + a2.backbone.latency
            jilter += a1.backbone.get_jilter() + a2.backbone.get_jilter()
        
        return speed, latency, jilter
    
    def get_link_states_between_devices(self, device1: Device, device2: Device):
        return self.get_link_states_between_devices_by_id(device1.id, device2.id)
    
    def cal_transmit_delay_between_devices_by_id(self, d1: int, d2: int, datasize):
        """Calculate the transmition delay of the file bewteen two devices

        Args:
            d1 (int): device 1 id
            d2 (int): device 2 id
            datasize (float): size of the transmitted file (MB)
        """
        speed, _, _ = self.get_link_states_between_devices_by_id(d1, d2)
        ans = datasize / speed * 1000 # ms
        return ans
    
    def cal_transmit_delay_between_devices(self, device1: Device, device2: Device, datasize):
        return self.cal_transmit_delay_between_devices_by_id(device1.id, device2.id, datasize)
    
    def check_areas(self):
        device_num = 0
        for area in self.areas:
            if area.devices.__len__() == 0:
                print(f"Area {area.id} does not have any devices!")
            device_num += area.devices.__len__()
        if device_num != self.device_to_area.__len__():
            raise ValueError(f"Total devices number in edge areas {device_num} does not equal to the one stored in topology {self.device_to_area.__len__()}.")