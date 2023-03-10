## 关于环境本身

- 是否有必要修改 slot 的定义？
- 是否有必要将 computation 相关的内容改回 GHz？
  - 那么就能实现计算时间的估计
- QoS 里的启动延迟应该算作响应延迟的指标（在传统计算任务中，从发送请求到接受结果的时间差），服务延迟应该是针对云桌面这类重交互的服务所特有的指标



---

## 修改关于带宽的实现

### 现在的实现方式

- 分为长期占用与临时占用两类
  - 长期占用：对于远程桌面这种需要一直推流的服务，我们直接**扣除对应链路上的一段额定带宽**。
    - 推流带宽的大小来自任务信息
    - filestore 挂载的带宽假定为恒定的 1MBps
  - 临时占用：对于更加一般的文件推送或者计算信息送回的服务，我们以链路上的最小带宽为速度，计算其**发送时间作为服务延迟**参数
    - 不对带宽上限进行占用
    - 所有 depository 都算作此类服务
- 未实现排队相关操作
- 未实现 depository 的下载延迟计算
  - 所有 depository 都作为待选节点，导致仿真性能下降

### 接下来的修改

1. 长期占用保持不变，依旧假设这段链路资源完全分配给该任务
   1. 先考虑长期占用的资源，剩下的资源再交给临时占用进行分配
2.  选用**估计下载时间**最短的节点作为 depository，没必要刷新所有节点的资源存储
   1. depository 同样要作为临时占用进行延迟计算，它的延迟算在启动时延中
   2. 单个任务的启动时延取最后一个 missing layer 完成下载的时间节点
3. 对于临时占用的情况，直接为 topology 类中的每个 link 维护一个队列
   1. 元素为一个定制的类，包含属性：任务、开始时间、持续时间
   2. 该队列为优先队列，元素按照任务分配顺序进行排列
4. 占用时间分配方式：
   1. 取链路上的最小带宽作为传输速度计算持续时间
   2. 取链路上的最大结束时间（开始时间+持续时间）作为开始时间
   3. 误差：真实的传输应该是“见缝插针”的，但考虑到所有对比实验都用这一套，应该影响不大
5. 需要设计两种文件传输的先后顺序
   1. 镜像传输：决定了启动时间。
   2. 文件传输：分为 u-c 与 u-c-f 两种。按理说应该在启动之后进行，这部分的计价只统计从启动后开始到传输完成的时间。在实现中，我们通过传输速度对他进行计价，降低了复杂度。

---

## 修改环境的每步更新

### 现在的实现方式

- 每个 step 为一个 slot 的更新
  - 对当前 slot 的每一个任务采取行动
    - 每个任务进行一次判决
  - 进入下一个 slot
  - 收集该 slot 的所有任务作为状态
    - 每个状态实际上是许多个任务的状态拼接在一起
- 在 step 的过程中完成了 compute 与 depositories 的挑选
  - 预先为备选的节点都**预约了资源**（使用一个单独的 preoccupied 属性）
- 暂未存储两个相邻状态（s 与 s'）

### 问题所在

1. 预约的资源会导致每个 slot 中靠后的任务被**错误丢弃**
2. 一个 step 环境更新的时间极长
3. 每个 step 需要执行大量的决策
4. 如何定义状态转移？

### 接下来的修改

1. 保留现有结构，从环境更新中剔除 state 相关内容，替换为一个任务数 task_num 属性
   1. step 只负责执行单步 action 并返回 reward
   2. 独立出 next 函数用于 slot 更新
2. 修改 agent 的执行流程
   1. for i in range(task_num):
   2. ​      action = actor(env.get_state(task_id=i))    # 不再预留资源
   3. ​      reward[i] = env.step(task_id=i, action=action)
   4. task_num = env.next()
3. 关于状态转移的几种考量
   1. 如果定义状态转移是 action 导致全网资源的变化，应该取执行完该 action 后的下一个任务的状态，但是这样就无法学习环境的状态转移
      1. 环境本身偏向于随机转移，影响不是很大
      2. 真正有影响的应该是 long span 任务会为后面的 slots 带来影响，但是远不如直接对它紧邻的任务的影响大
      3. 或许可以考虑不记录每个 slot 中最后一个任务的经验，这样获得的状态转移就是统一的
   2. 如果按照之前计划书里的方案，取相同任务类型、follower 类型的下一个任务的状态，就会导致环境更新与本次 action 的关联性太低
   3. 如果定义状态转移包括了环境自身的变化，那么就应该从下一个 slot 中选择随机的或第一个任务的状态，但是这样的状态转移包含了其他 action 带来的不稳定更新
      1. multi agent 是一个好的思路，然而单 slots 内 agents 数量不固定
4. 延迟的状态应该加上来自占用的延迟

### 一种新思路

- 一个 slot 算作一个 episode
  - 单 slot 内任务贼多，一个任务进行一次决策，本来就不应该用传统的方式
  - 相邻 slots 间存在 trajectory 的断代
  - 这样能把其他任务看作未来决策，**纵向**考虑这个 slot 里的剩下任务（Multi agent 算做**横向**同时考虑其他任务的决策）
    - 当前的状态包含了该 slot 前面任务的影响，TD 考虑了之后的任务情况，理论上也算是有在考虑该 slot 中的其他决策
- 经过讨论，直接单链 MDP 可能就行

---

## 修改参数

1. 服务器与用户的比例失调
   1. 现在一台服务器能同时服务的用户数量较少，虽然很合理，但是需要解释
2. 关于带宽的占用有待商榷

---

## 定价模式



---

## 预计出图

### OPENRAAS vs 中心化 vs 边缘化

- OPENRAAS 组合方式：直接按照会影响到的 QoS 指标贪婪选择节点
- 中心化实现方式：有且仅在一个 area 中放置 servers，且该 area 的 backbone 链路延迟与带宽均较大
- 边缘化实现方式：仅由每个 area 中的 server 为自己的区域提供服务
  1. 传统边缘：将每个 application 及其对应的 layer 分配到多个 server 上，每个 server 只能提供自己具有的完整服务
  2. 合作边缘：仅在 openraas 的基础上关闭所有 client 的 is_worker 属性

- 对比内容（在单独的三种任务模式 + 混合任务模式下进行 4 组测试）
  1. 所有 worker 的平均资源占用百分比
  2. 任务的接受率
  3. 平均任务延迟（计算任务需要加上计算时间）
  4. 用户的满意度（QoS 加权，论文 1 的实验可以不计量成本开销，除非结果够好）