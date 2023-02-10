import numpy as np
from .device import *

class Line(object):
    def __init__(self, bandwidth, latency):
        self.bandwidth = bandwidth  # MBps
        self.latency = latency      # ms


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
        self.backbone = Line(bw, l)

    def add_device(self, type: int, device_id: int, bandwidth=0):
        """
        The property type indicates the wire or wireless device: 0-wire, 1-wireless.
        Bandwidth is the network interface bandwith of the device.
        """
        if type == 0:
            l = max(3 + 1 * np.random.randn(1)[0], 1.) # wire 1 ~ 6 ms
        elif type == 1:
            l = max(7 + 2 * np.random.randn(1)[0], 1.) # wireless 1 ~ 13 ms
        else:
            raise ValueError(f"The input line type {type} is out of range!")
        
        self.devices.append(device_id)
        self.lines.append(Line(bandwidth, l))
        
    def update_bandwidth(self, device_id: int, bandwidth):
        """We should update bandwidth information once changed."""
        i = self.devices.index(device_id)
        self.lines[i] = bandwidth
    

class Topology(object):
    def __init__(self, area_num):
        self.area_num = area_num
        self.areas: list[Area] = [Area(i) for i in range(area_num)]
        self.device_to_area = {}    # key: device id, value: area id
        self.reset()
        
    def reset(self):
        for area in self.areas:
            area.reset()
    
    def add_device(self, device: Device, area_id=-1):
        if area_id == -1:
            area_id = np.random.randint(0, self.area_num)
        type = 0 if device.type() == 'server' else 1
        self.areas[area_id].add_device(type, device.id, device.bw)
        self.device_to_area[device.id] = area_id
    
    def update_bandwidth(self, device: Device):
        area_id = self.device_to_area[device.id]
        self.areas[area_id].update_bandwidth(device.id, device.bw)
    
    def cal_latency_between_devices_by_id(self, d1: int, d2: int):
        """Only calculate the line latency.
        We need another method to calculate the transmit delay.
        
        Args:
            d1 (int): device 1 id
            d2 (int): device 2 id

        Returns:
            _type_: _description_
        """
        a1 = self.device_to_area[d1]
        a2 = self.device_to_area[d2]
        i1 = self.areas[a1].devices.index(d1)
        i2 = self.areas[a2].devices.index(d2)
        ans = self.areas[a1].lines[i1].latency + self.areas[a2].lines[i2].latency
        if a1 != a2:
            ans += self.areas[a1].backbone.latency + self.areas[a2].backbone.latency
        return ans
    
    def cal_latency_between_devices(self, device1: Device, device2: Device):
        return self.cal_latency_between_devices_by_id(device1.id, device2.id)
    
    def cal_transmit_delay_between_devices_by_id(self, d1: int, d2: int, filesize):
        """Only calculate the transmition delay of the file bewteen two devices

        Args:
            d1 (int): device 1 id
            d2 (int): device 2 id
            filesize (float): size of the transmitted file (MB)
        """
        a1 = self.device_to_area[d1]
        a2 = self.device_to_area[d2]
        i1 = self.areas[a1].devices.index(d1)
        i2 = self.areas[a2].devices.index(d2)
        # find the bottleneck of this line
        bn = min(self.areas[a1].backbone.bandwidth, self.areas[a2].backbone.bandwidth)
        bn = min(bn, self.areas[a1].lines[i1].bandwidth)
        bn = min(bn, self.areas[a2].lines[i2].bandwidth)
        ans = filesize / bn * 1000 # ms
        return ans
    
    def cal_transmit_delay_between_devices(self, device1: Device, device2: Device, filesize):
        return self.cal_transmit_delay_between_devices_by_id(device1.id, device2.id, filesize)
    
    def check_areas(self):
        device_num = 0
        for area in self.areas:
            if area.devices.__len__() == 0:
                print(f"Area {area.id} does not have any devices!")
            device_num += area.devices.__len__()
        if device_num != self.device_to_area.__len__():
            raise ValueError(f"Total devices number in edge areas {device_num} does not equal to the one stored in topology {self.device_to_area.__len__()}.")