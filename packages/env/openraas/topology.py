import numpy as np
from .device import *

p0 = 1e-10
n0 = -p0


class Line(object):
    def __init__(self, bandwidth, latency, jilter):
        self.capacity = [bandwidth, latency, jilter]
        self.reset()

    def get_jilter(self):
        ans = round(max(self.jilter + self.jilter/3 * np.random.randn(1)[0], 0.))  # 0 ~ 2 mean_jilter
        return ans

    def reset(self):
        self.bandwidth = self.capacity[0]       # MBps
        self.latency = self.capacity[1]         # ms
        self.jilter = self.capacity[2]          # mean jilter times in a slot
        self.occupied_time = 0.
    
    def step(self):
        self.occupied_time = 0.


class Area(object):
    def __init__(self, id):
        self.id = id
        self.devices: list[int] = []    # devices' IDs
        self.lines: list[Line] = []     # devices' lines with respect to self.devices
        
        bw = max(3 + 2 * np.random.randn(1)[0], .5)*1000/8 # (1 ~ 10)/8 GBps
        l = max(40 + 20 * np.random.randn(1)[0], 1.) # 1 ~ 19 ms
        j = max(15 + 10 * np.random.randn(1)[0], 0) # 2 ~ 8
        self.backbone = Line(bw, l, j)
    
    def clear(self):
        self.devices.clear()
        self.lines.clear()
        self.backbone.reset()
    
    def reset(self):
        for line in self.lines:
            line.reset()
        self.backbone.reset()

    def step(self):
        for line in self.lines:
            line.step()
        self.backbone.step()

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
    

class Topology(object):
    def __init__(self, area_num):
        self.area_num = area_num
        self.areas: list[Area] = [Area(i) for i in range(area_num)]
        self.device_to_area = {}    # key: device id, value: area id
        self.reset()
    
    def clear(self):
        for area in self.areas:
            area.clear()
        self.device_to_area.clear()
    
    def reset(self):
        for area in self.areas:
            area.reset()
    
    def step(self):
        for area in self.areas:
            area.step()
    
    def get_area_by_device_id(self, device_id: int):
        return self.areas[self.device_to_area[device_id]]
    
    def get_area_by_device(self, device: Device):
        return self.get_area_by_device_id(device.id)
    
    def get_device_interface_link_by_id(self, device_id: int):
        area = self.get_area_by_device_id(device_id)
        return area.lines[area.devices.index(device_id)]
    
    def get_device_interface_link(self, device: Device):
        return self.get_device_interface_link_by_id(device.id)
    
    def add_device(self, device: Device, area_id=-1):
        if area_id == -1:
            area_id = np.random.randint(0, self.area_num)
        type = 0 if device.print_type() == 'server' else 1
        self.areas[area_id].add_device(type, device.id, device.bw)
        self.device_to_area[device.id] = area_id
    
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
        if d1 == d2:
            return 1e8, 0., 0.
        
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
    
    # def cal_transmit_delay_between_devices_by_id(self, d1: int, d2: int, datasize):
    #     """Calculate the transmition delay of the file bewteen two devices

    #     Args:
    #         d1 (int): device 1 id
    #         d2 (int): device 2 id
    #         datasize (float): size of the transmitted file (MB)
    #     """
    #     speed, _, _ = self.get_link_states_between_devices_by_id(d1, d2)
    #     ans = datasize / speed * 1000 # ms
    #     return ans
    
    # def cal_transmit_delay_between_devices(self, device1: Device, device2: Device, datasize):
    #     return self.cal_transmit_delay_between_devices_by_id(device1.id, device2.id, datasize)
    
    def occupy_bandwidth_between_devices(self, device1: Device, device2: Device, bw):
        """update the bandwidth occupation

        Args:
            device1 (Device): device 1
            device2 (Device): device 2
            bw (float): long-term occupied bandwidth (MB)
        """
        if bw == 0. or device1 == device2:
            return
        a1 = self.get_area_by_device_id(device1.id)
        a2 = self.get_area_by_device_id(device2.id)
        i1 = self.get_device_interface_link_by_id(device1.id)
        i2 = self.get_device_interface_link_by_id(device2.id)
        if i1.bandwidth != device1.bw or i2.bandwidth != device2.bw:
            raise ValueError(f"The link bandwidth {i1.bandwidth} {i2.bandwidth} is not equal to the interface's {device1.bw} {device2.bw}.")
        
        i1.bandwidth -= bw
        i2.bandwidth -= bw
        device1.bw = i1.bandwidth
        device2.bw = i2.bandwidth
        
        if a1 != a2:
            a1.backbone.bandwidth -= bw
            a2.backbone.bandwidth -= bw

        if i1.bandwidth < n0 or i2.bandwidth < n0:
            raise ValueError(f"Negative bandwidth ({i1.bandwidth}, {i2.bandwidth}) in interface.")
        if a1.backbone.bandwidth < n0 or a2.backbone.bandwidth < n0:
            raise ValueError(f"Negative bandwidth ({a1.bandwidth}, {a2.bandwidth}) in backbone.")
        
    def release_bandwidth_between_devices(self, device1: Device, device2: Device, bw):
        return self.occupy_bandwidth_between_devices(device1, device2, -bw)
    
    def transmit_task_between_devices(self, device1: Device, device2: Device, datasize, min_startup_time=0.):
        """update the occupated time
        auto released when stepping because only temporary transmissions use the occupied_time property

        Args:
            device1 (Device): device 1
            device2 (Device): device 2
            datasize (float): temporarily transmitted file size
            min_startup_time (default=0.): the specified minimize transmission begin time, used to transmit a file after initializing the compute worker (fetch images)
        
        Returns:
            end_time (float): the transmission latency after the begin of this slot (ms)
        """
        if device1 == device2:
            return
        a1 = self.get_area_by_device_id(device1.id)
        a2 = self.get_area_by_device_id(device2.id)
        i1 = self.get_device_interface_link_by_id(device1.id)
        i2 = self.get_device_interface_link_by_id(device2.id)
        
        # calculate end_time
        begin_time = max(self.get_link_occupied_time(device1, device2), min_startup_time)
        duration = self.cal_transmission_duration(device1, device2, datasize)
        end_time = begin_time + duration
        
        # update link states
        i1.occupied_time = end_time
        i2.occupied_time = end_time
        if a1 != a2:
            a1.backbone.occupied_time = end_time
            a2.backbone.occupied_time = end_time
        
        return end_time    
    
    def get_link_occupied_time(self, device1: Device, device2: Device):
        a1 = self.get_area_by_device_id(device1.id)
        a2 = self.get_area_by_device_id(device2.id)
        i1 = self.get_device_interface_link_by_id(device1.id)
        i2 = self.get_device_interface_link_by_id(device2.id)
        
        ans = min(i1.occupied_time, i2.occupied_time)
        
        if ans and a1 != a2:
            ans = min(ans, a1.backbone.occupied_time)
            ans = min(ans, a2.backbone.occupied_time)
        
        return ans
    
    def cal_transmission_duration(self, device1: Device, device2: Device, datasize):
        # only calculation, no application
        speed, _, _ = self.get_link_states_between_devices_by_id(device1.id, device2.id)
        duration = datasize / (speed+1e6) * 1000 # ms
        return duration
    
    def check_areas(self):
        device_num = 0
        for area in self.areas:
            if area.devices.__len__() == 0:
                print(f"Area {area.id} does not have any devices!")
            device_num += area.devices.__len__()
        if device_num != self.device_to_area.__len__():
            raise ValueError(f"Total devices number in edge areas {device_num} does not equal to the one stored in topology {self.device_to_area.__len__()}.")