# OpenRaaS Simulation

## A. Entities

### Basic entities in an edge model

### Devices

Global Master: a centralized server with abundant computation & storage ability

Edge servers: edge devices serve as cloud service providers

- Server: 50 GF, 1 TB, 1 Gbps (each), open, fixed

End-users: they can voluntarily beacome worker nodes when they are clients of OpenRaaS

- Desktop: 20 GF, 200 GB, 300 Mbps (average), open & closed, fixed
- Mobile device: 5 GF, 30 GB, 300 Mbps (average), closed, unstable
- IoT device: 5 GF, 10 GB, 100 Mbps (average), open, fixed & unstable

### Tasks

Processing service:

- 5 GF, 5 MB uploads, 3 layers (core os 100 MB, drivers 200 MB, library 100 MB), application 500 MB

- Every APP data is replicated to multiple devices, at least one is on an edge server, as is the image layer.

Storage service:

- -, 20 files (500 MB each) uploads, 4 fixed layers (core os 100 MB, drivers 50 MB, library 50 MB, execution 10 MB)

- The execution workload is low and can be ignored.

- The compute worker only forwards the files to the filestore worker, but it should download the image layers.

- There are totally 100 kinds of files, and 40% of them are public files

Cloud desktop service:

- 5 GF, 100 Mbps downloads, 4 layers (core os 100 MB, drivers 200 MB, library 200 MB, compatible layer 500 MB), application 20 GB

- A task may occupy resources for several slots, which means we should consider the bandwidth in this scenario.

<!-- - DataCenter: resource-rich, open, remote
- Edge Server: resource-rich, open
- PC: resource-rich, open
- Laptop: resource-rich, energy-sensitive, open
- AndroidPhone: energy-sensitive, open
- Mac: resource-rich, close
- MacBook: resource-rich, energy-sensitive, close
- IPhone: energy-sensitive, close 
As described in iFogsim simulation toolkit.-->

## B. Design

Overall:

- $M$ edge servers, $N$ users, and a basic time slot $\Delta t$ is 30 minutes

Device:

<!-- - Each user has three states (for CPU): occupied with task requirements (20%), just occupied (20%), and idle (60%) -->
- Users' online states are dynamic
- Average 20% of the idle users are worker nodes (every idle device has 1/5 chance to become a worker)
- Devices do not use the disk space prepared for OpenRaaS, even if they are not worker nodes. So we don't care about their inner storage space.

Application:

- Different applications may have some layers in common, so we specified application types and their propoties at the beginning of the procedure.
- If a device is idle, it still has probability to require services like remote desktop dislike traditional CEC models.

Task generation:

- Each client has 100% probability to require cloud services in a slot
- If unspecified, those task types has the same chance to be chosen

Task execution:

- Do not care the network balance. Use all the bandwidth for the current task, and let others wait in line.
- The compute worker $C$ should care about **the download link from meta OS**
- Mounting files does not occupy all bandwidth at once, so we set a fixed value of 8 Mbps (1 MBps).
- Uplink and downlink bandwidth are calculated together.
- Once a worker performs computation services, it will preserve the requested resource until task finishing. If it has a new demand, it will turn to ask for OpenRaaS services instead of blocking the ongoing tasks.

For depository:

- Computation cost can be ignored.
- A computation worker who fetched layers can become the depository of those layers.
- All layers on a node has timers to make them survive. When using ($C$) or pushing ($D$) a layer, its timer resets.

## C. Scheduling

### Worker Identification

**Compute worker $C$:**

1. Fixed & open devices with enough resource
2. Should has enough storage to contain the missing layers

- When checking the storage space, it should substract the size of existing layers first.
- After a task finished, it should check its remaining storage (> 1GB) or else release the oldest layers

**Filestore worker $F$:**

1. Fixed devices with target files

<!-- a) $F$ for mounting:

1. Fixed devices with target files

b) $F$ for storage services:

1. A server and another device with enough resource (totally 2 backups) -->

**Depository worker $D$:**

1. Any device with target layers

### Microservice Composition

1. Choose a nearest one from the above compute worker list.
2. Choose filestore workers based on latency between the compute worker
3. Spliting the image layers into several threads, and downloading from all the available depository workers (It prioritizes the node that responds first).

---

## Related

The implementation of [OpenBaaS](https://github.com/zobinHuang/OpenRaaS)
