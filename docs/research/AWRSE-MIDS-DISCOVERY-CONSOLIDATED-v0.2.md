# AWRSE MIDS 世界设计发现整合稿 v0.2

> 状态：`NON_CANONICAL_DESIGN_EVIDENCE / USER_CONFIRMED_MIDS_DISCOVERY`
>
> 用途：把本轮 MIDS 中用户已经明确确认的 AWRSE 世界设计意图集中保存，供 Control Tower、Codex / GPT Engineering Worker、Independent Reviewer 在后续 architecture compilation 时读取。
>
> 重要：本文件不是 `ARCHITECTURE.md`，不自动获得 canonical authority。正式写入 canonical architecture / contracts / Golden / OPEN_DECISION 前必须 fresh reconcile 当前 GitHub `main` 与相关治理证据。
>
> 决策规则：
> - 用户明确选择/补充 = `USER_EXPLICIT_CONFIRMED`
> - AI起的机制名称/工程结构 = `AI_DERIVED_CANDIDATE`
> - 用户没有在后续重复某条旧规则，不代表取消
> - 只有用户明确推翻旧决定时才 `SUPERSEDED`

---

## 0. MIDS 工作方式

### 0.1 交互方式
- MIDS 用来让用户回答“世界应该怎样感觉和运行”，而不是让用户回答工程术语。
- 题目应优先覆盖总体架构、世界哲学、重大不可逆边界。
- 对明显属于工程最佳实践、且没有真实产品取舍的问题，不要无休止让用户确认。
- 细节域下钻 1~3 轮后应重新回到总体架构。
- 当总体架构已经足以施工时，停止大规模提问，剩余问题进入 `OPEN_DECISION`，由样品/实现反馈重新触发 MIDS。
- 语音模式下曾采用“第一道题/第二道题 + 1/2/3 选项”，但用户发现语音效率较低，当前回到文字模式。
- 默认一轮约 10 个高价值问题；但不为凑数量而提问。

### 0.2 认识状态
1. `USER_EXPLICIT_CONFIRMED`
2. `USER_TACIT_CANDIDATE`
3. `AI_DISCOVERABLE_OPTION`
4. `EXPERT_BLIND_ZONE`

Tacit candidate 不得冒充用户明确意图；AI option 不得直接变成 world law。

---

# 1. 产品定位与世界哲学

## 1.1 AWRSE 的目标
用户确认 AWRSE 最终应同时具备：

1. 能持续产生高质量故事的互动叙事引擎；
2. 可被 AI 电影系统实时表现/拍摄的真实世界底座；
3. 玩家可以用自然语言执行几乎任何合理行为的角色扮演系统。

候选总体描述：

> 一个持续运行、分层解析、拥有统一 World Truth、开放式角色行动、多 Authority 动态反馈、可追溯因果、可产生自主历史，并可把高价值真实因果编译成互动叙事与 AI 电影素材的 Living World Runtime。

## 1.2 玩家不是世界因果中心
- 玩家是重要体验主体，但不是宇宙因果中心。
- 世界可发生玩家永远不知道的重要历史。
- Narrative 可以提高玩家接触值得体验的世界切片的机会，但不能重写世界因果。
- 故事可以围绕玩家，但必须有世界内原因。
- 玩家可以成为大人物，也可以一辈子只是普通人。
- 世界没有义务给玩家救世使命。

## 1.3 没有玩家时世界仍能运行
- 世界可以先运行很多年再让玩家进入。
- NPC、国家、机构、经济、战争等可以自行发展。
- 玩家进入后加入已有历史。
- Narrative 从已有历史中寻找故事，不为迎接玩家重写过去。

---

# 2. 第一阶段施工哲学

用户明确纠正：第一版不应只证明一个单点能力。

第一版应采用：

> **Breadth-first Minimal Living World**

即：
- 所有主要系统第一版都先有最小骨架；
- 在一个非常小的世界中跑通完整闭环；
- 每块不求一开始做深，但必须互相连接；
- 完整闭环成功后再逐模块加深。

第一版至少应有一点点：
- 实体持续性；
- 因果传播；
- World Truth；
- 自然语言行动；
- Character capability；
- NPC knowledge/belief 差异；
- 机构/社会响应；
- Narrative opportunity；
- Dramatic Presentation Intent；
- AI Director 输出接口；
- persistence / history；
- 时间；
- 世界状态变化。

用户强调主线仍然是**搭架构**，不是先选一个 demo 就把架构缩成 demo。

---

# 3. Authority 与高层协调 AI

## 3.1 多 Authority
不同 AI / subsystem 分别负责不同 domain，并各自持续发展。

高层存在统一协调 AI / Orchestrator：
- 看全局；
- 负责调度；
- 管理依赖；
- 决定哪些系统需要被唤醒/提高精度；
- 决定何时中断时间压缩；
- 汇总各 Authority 已完成的裁决；
- 把结构化结果送给 Narrative / Director；
- 发现跨系统矛盾后要求对应 Authority 重新解析。

但它不拥有 domain truth。

核心：
> **Orchestrator resolves coordination, not domain truth.**
>
> **影响可以跨系统，Authority 不能跨系统。**

## 3.2 动态反馈网络
AWRSE 不是线性流水线，而是持续因果反馈网络。

例如：
`招募 -> 资金消耗 -> 组织压力 -> 成员不满 -> 背叛风险 -> 警方获情报 -> 调查 -> Narrative 发现机会 -> Director 埋伏笔 -> 玩家改变计划 -> 世界再次变化`

一个系统的结果会再次成为其他系统输入。

## 3.3 跨系统传播
用户确认：
- domain 结果应通过正式世界事件 / structured state change 传播；
- Orchestrator 负责选择需要通知/唤醒的相关系统；
- 重大变化保留因果来源；
- 不相关系统无须全部重算。

`AI_DERIVED_CANDIDATE: Causal Selective Propagation`

## 3.4 同一状态受多个系统作用
不由 Orchestrator 粗暴选“哪个系统赢”。

例：政府限价 + 市场供不应求：
- 法律明面维持限价；
- 正规市场可能缺货/排队/配给；
- 黑市价格因短缺而上涨；
- 腐败/走私/执法等继续产生二阶反馈。

不同 Authority 分别产生合法作用，再由对应 owner/resolver 合成真实状态。

---

# 4. World Truth / Knowledge / Belief / Audience / Presentation

必须明确分层：

- `World Truth`: 实际发生了什么
- `Character Knowledge`: 角色合法知道什么
- `Character Belief`: 角色当前相信什么
- `Audience Knowledge`: 观众/现实玩家被允许看到什么
- `Presentation`: Director 怎么拍/表现

规则：
- World Truth 只有一套。
- 不同玩家/NPC Knowledge 可以完全不同。
- Belief 可以与 Memory / World Truth 冲突。
- 一名玩家告诉另一名玩家本身是信息传播事件。
- AI Director 可以知道完整世界信息，但是否展示取决于 Presentation Policy。
- 观众知道不自动写入角色 Knowledge。

---

# 5. 游戏模式与电影模式

## 5.1 游戏模式
- 不展示角色完全不知道且不在其合法感知范围的远方重要事件。
- 镜头可以为了表现切向角色可见/可感知的 nearby action。
- 体验以角色知识边界为主要限制。

## 5.2 电影模式
- 可以展示角色不知道的重大世界事件。
- 可以制造“观众知道、角色不知道”的戏剧反差。
- 展示内容绝不能写回角色 Knowledge。

因此同一 World Truth 可由不同 Presentation Policy 呈现。

---

# 6. AI Director 与 AWRSE 的边界

用户确认：
- AWRSE 是 world truth authority。
- AI Director 可读取结构化世界状态、动作、因果、人物状态等。
- Director 不能为了镜头修改已发生的事实。
- AWRSE 内需要有一层判断：
  - 哪些前因后果值得表现；
  - 哪些是真实伏笔；
  - 哪些事件适合回收；
  - 观众应该知道多少；
  - 推荐表现强度。
- 具体镜头、剪辑、表演、节奏、具体脚本化表现交给独立 AI Director 项目。

`AI_DERIVED_CANDIDATE`：
- `Dramatic Presentation Intent`
- `Director Intent Packet`

## 6.1 Causal Foreshadowing
世界真实形成：
`邻居怀疑 -> 举报 -> 警方调查 -> 监视 -> 搜查 -> 逮捕`

Director 可以在逮捕前表现：
- 街角奇怪的人；
- 有人在观察；
- 陌生车辆；
- 邻居与陌生人交谈。

原则：
> 伏笔不能凭空制造未来。
> 世界先有真实因果，Director 再把早期迹象拍给观众看。

若误判源于警察能力不足，Director 应在表现上体现：
- 调查粗糙；
- 证据链没查完整；
- 忽略矛盾；
- 急于交差；
从而让观众看懂“为什么判错”。

`AI_DERIVED_CANDIDATE: Causal Foreshadowing`

## 6.2 Causal Payoff
小因可造成巨大历史结果。
例如：
`鞋坏 -> 士兵晚到 -> 命令未送达 -> 战役失败 -> 政权垮台`

若因果链具有强戏剧价值，AWRSE 应标注清楚前后因果，交给 Director 表现，而不是只交最终结论。

`AI_DERIVED_CANDIDATE: Causal Payoff Candidate`

---

# 7. Narrative Gravity

## 7.1 合法概率轻推
Narrative 可以在本来合法的可能空间内影响概率：
- 戏剧价值越高，可倾斜程度可更高；
- 必须有上限；
- 越高风险/越影响世界历史，允许改变越少；
- 宏观事件也可在合法范围内轻推，但不能硬造。

核心：
> **Narrative may bias possibility, but may not manufacture impossibility.**

约 30% 是用户举出的“一般更容易被用户明确感知”的经验参考，不是普适硬阈值。

## 7.2 Narrative Budget
需防止很多小倾斜长期累积成隐形操纵。

至少考虑：
- 按玩家；
- 按剧情线；
- 按世界级重大事件
分别管理预算。

Budget 用完：
- 世界自然事件继续；
- Narrative 概率加权暂停。

`AI_DERIVED_CANDIDATE`：
- `Narrative Probability Budget`
- `Narrative Influence Ledger`

后台记录：
- 原概率；
- 调整后概率；
- 原因；
- 戏剧目标；
- 世界依据。

普通玩家不必看到，Reviewer/系统必须可追踪。

## 7.3 玩家 Narrative Exposure Preference
玩家反复表示“我不想被外部世界卷进去”：
- 可降低主动 Narrative Exposure；
- 不永久贴标签；
- 后续主动寻求刺激时可升回；
- 行为模式可以形成 tacit candidate，但权重低于明确表达；
- 世界真实因果不能因此停止；
- 真正自然波及的重大事件仍可发生。

> 玩家偏好影响 Narrative Exposure，不影响 World Truth。

## 7.4 世界压力不等于 NPC 发任务
国家动乱可通过：
- 物价；
- 就业；
- 生存环境；
- 治安；
- 交通；
- 工作环境；
- 公共/休闲空间；
- 新闻/报纸/电视/公告；
- 邻居/商人/官府
逐渐影响玩家。

玩家可因此主动查询原因。

---

# 8. Authorial Direction 与未来

## 8.1 世界初始化
用户确认采用混合模式：
- 开局有剧本的大致方向 / 关键锚点；
- 具体世界内容依据世界设定自动生成；
- 未探索/未需要的细节可后续具体化。

候选：
`Authorial Direction + World Constraints + Generative Concretization`

## 8.2 未来事件不是铁轨
如果作者想推动某个未来剧情：
- 可以设置引导性未来目标/吸引子；
- 不是强制保证发生；
- 玩家改变发生条件时原则上可以避免；
- 应优先通过合法条件推动，而不是硬写未来事实。

候选：
`Authorial Future Attractor != Guaranteed Future Event`

这与当前 canonical `SoftDramaticAttractor` 方向兼容，应优先复用，不创建第二套 Narrative future truth。

---

# 9. 自然语言开放行动

## 9.1 Intent -> Capability -> Consequence
玩家提出从未预制的行动时：
- 不先问有没有预制玩法；
- 先判断当前世界规则是否允许；
- 再判断角色能力/资源/时间/空间/社会条件。

例：“建立地下杀手组织”需考虑：
- 号召力；
- 组织能力；
- 人脉；
- 金钱；
- 时间；
- 基地；
- 隐蔽；
- 法律；
- 警察/政府；
- 招募对象；
- 忠诚；
- 竞争势力。

世界以真实后果反馈。

`AI_DERIVED_CANDIDATE: Intent -> Capability -> Construction -> Consequence`

## 9.2 没给具体方法时
AI 可为角色生成最符合角色素质的常规方案。

低能力农民刺杀皇帝，不会因为大模型懂刺杀就自动获得大师计划。

> `AI intelligence != Character intelligence`

## 9.3 复杂连续动作
- 玩家可说整体目标或具体步骤；
- 每一步依据最新世界状态重判；
- 前一步失败时后续计划可失效/调整；
- 不因为玩家说完整句子就保证所有步骤成功。

## 9.4 新奇概念的可实现性受世界类型约束
例：“把人的记忆当货币”：
- 科幻/赛博世界如果已有神经接口、记忆提取等基础，可能性高；
- 写实现实世界可能性极低；
- 再结合角色身份、能力、技术、资源、社会、法律判断；
- AI 应以世界合理的方式反馈成功/失败，而不是统一的“创意成功率”。

候选原则：
> Genre / World Rules define the possibility envelope; character capability acts inside it.

若现有 world rule 根本无法表达一个本应支持的新机制，则作为 `OPEN_DECISION / MIDS / RULE_CANDIDATE` 返回设计层，而不是 runtime AI 自行修改世界法则。

---

# 10. 玩家控制与 NPC 自主

## 10.1 自己控制角色
玩家对自己当前控制角色拥有最终控制权。
即使极度违背人物性格，玩家仍能执行。

但角色表现可体现：
- 痛苦；
- 犹豫；
- 手抖；
- 内心冲突。

> `Personality influences expression, not player veto.`

## 10.2 其他角色
玩家不能直接控制其他 NPC。
可以提前下目标/命令，但具体执行受：
- 智力；
- 能力；
- 经验；
- 忠诚；
- 状态；
- 环境；
- 临场判断
约束。

NPC：
- 小调整可自主；
- 大方向改变可回报；
- 可以反对玩家；
- 可以认为计划太差。

---

# 11. NPC 目标、关系、记忆与认知

## 11.1 目标
NPC 可以同时有长期/中期/短期目标。
世界变化会动态重排目标。

NPC 可产生开发者未预设的新目标，但应来自：
- 经历；
- 性格；
- 当前世界。

## 11.2 关系
关系由多个维度共同形成：
- 真实互动；
- 性格/价值观；
- 社会身份/声望/阵营；
- 传闻；
- 当前利益。

“喜欢”“信任”“尊敬”“害怕”等不应被强迫压成单一总值。

## 11.3 Memory
- 重大记忆尽量不消失；
- 中等记忆逐渐模糊/难召回；
- 模糊应让玩家通过语言、迟疑、表演、镜头感知；
- 后续经历可重新提高旧记忆意义；
- 不能凭空恢复已经真实丢失的细节。

## 11.4 Belief
Memory 与 Belief 分离。
角色可以记得 A，但后来相信 B。

信念形成受角色认知风格影响：
- 理性角色更偏证据；
- 感性角色更偏自身记忆；
- 创伤、爱情、宗教、身份、群体压力等影响接受证据；
- 认知风格可成长；
- 不同领域可不同。

`AI_DERIVED_CANDIDATE: Character Epistemic Style`

## 11.5 智慧/侦查
高能力角色可：
- 更容易发现矛盾；
- 提出更好的问题；
- 连接证据；
- 生成调查路径。

但：
- 不能凭空生成事实；
- 低能力角色也可能偶然撞到关键证据。

Hardcore Mode 延后样品后再决定。

---

# 12. 机构、国家、经济与法律

## 12.1 机构
机构不是任务发放壳。
应有：
- 资源；
- 目标；
- 状态；
- 派系；
- 多 NPC/职位/制度共同决策；
- 长期政策；
- 成败；
- 学习。

## 12.2 国家
国家可以真实失败/灭亡：
- 财政崩溃；
- 军队解体；
- 政府消失；
- 新政权/军阀/社会结构出现。

不得为了保地图/剧情偷偷保护国家。

## 12.3 资源守恒
建立军队等重大实体必须有宏观来源：
- 人；
- 武器；
- 钱；
- 粮；
- 运输；
- 加入动机。

远方低精度区域不必模拟每个士兵，但宏观账必须成立。

`AI_DERIVED_CANDIDATE: Conservation with Resolution Scaling`

## 12.4 法律事实 ≠ 世界事实
用户已经确认：
- World Truth 记录真实犯罪有没有发生；
- 法律系统要基于证据形成嫌疑/认定；
- 判无罪不等于 World Truth 变成“没偷”；
- 新证据可改变认知/法律结果；
- 不同制度法律定义不同；
- 盘查、拘留、逮捕、定罪门槛不同；
- 战乱/独裁环境门槛可低；
- 执法者可违法、滥权、腐败、偷懒。

## 12.5 执法 NPC 会误判
同一份证据：
- 普通士兵可能看表面；
- 老刑警会查证据链；
- 能力高更容易发现冲突；
- 高能力仍可能错；
- 偏见、腐败、疲劳影响判断。

World Authority 知道真相，不等于执法 NPC 知道。

> `Authority Truth != NPC Inference`

若误判来自能力不足，应允许 AI Director 把这种“判断粗糙”表现出来。

## 12.6 Evidence
用户确认：
- 指纹、血迹、录像、信件、弹壳等证据属于真实世界的一部分；
- 可损毁、隐藏、伪造；
- 不同角色发现不同证据；
- 证据可靠度不同；
- AI 不能为了破案方便临时制造不存在的关键证据。

至少需要概念分离：
- World Fact
- Evidence
- Investigator Belief
- Legal Status / Judgment
- Social Belief

法律细节还未全部 MIDS，不应现在过度设计法庭系统。

---

# 13. 多人争夺与 Capability

## 13.1 时机优势
玩家对玩家争夺时：
- 更早出手形成连续 `timing advantage`；
- 越早优势越大，但不必胜；
- 与距离、反应、伤势、动作、技巧、武功体系、偷窃等共同作用。

当前例子中：
- 接入平台显示的正式时间作为时序证据；
- 不猜后台“真实点击时间”；
- 时间相同则 timing advantage 相同；
- 无法取得的比较参数默认相同，不编造差异。

## 13.2 方法特异能力
不使用单一战斗力决定所有动作。
特殊技巧可以改变比较维度。

## 13.3 接近区间
若双方不是断档差距：
可进入真实 contested interaction：
- 碰撞；
- 拉扯；
- 争抢；
- 搏斗；
- 偷窃；
- 威胁；
- 合作；
- 第三方介入。

`AI_DERIVED_CANDIDATE: CONTESTED_INTERACTION`

---

# 14. 时间与单机优先

## 14.1 Single Player First
当前首版优先单机。
多人/互联网版后续扩展。

## 14.2 单一 canonical timeline
世界只有一条 canonical timeline。
不同系统可有不同更新粒度，但映射到同一世界时间。

## 14.3 时间压缩
若玩家花三个月招募：
- 三个月真的经过；
- 其他系统照常演化；
- 重复/枯燥过程用导演压缩表现；
- 重大事件中断并把控制权还给玩家。

`AI_DERIVED_CANDIDATE: Temporal Compression with Decision Interrupts`

## 14.4 退出游戏
当前用户方向：
- 单机默认退出时世界冻结；
- 若现实离开很长，例如约半个月，可考虑推进世界时间；
- 精确阈值/补算算法不应现在写死，应留作 policy/open decision；
- 回来后应能对重要变化进行结构化摘要/表现。

---

# 15. 玩家死亡与存档

## 15.1 玩家角色死亡
死亡可以是真实永久 world event。
若世界本身存在复活机制，则按真实 world rule 执行。

死亡后玩家体验优先：
1. 优先由伙伴、子女、继承人等真实关系角色继续；
2. 没有合适继承路径时，可创建/选择新角色进入同一个继续发展的世界。

世界不会因为主角死亡删除。

## 15.2 Save/Load
首个样品先不以传统读档为基础。
后续根据真实体验决定是否增加。

`DEFERRED / NOT_IN_INITIAL_EXPERIENCE`

---

# 16. 模块化世界内核

用户确认：
- 所有世界共享一套核心；
- 不同世界按需加载 domain 模块；
- 运行过程中可合法加入新模块；
- 没启用的模块不能偷偷参与裁决；
- 所有模块服从统一 World Truth / Authority Meta-Laws。

候选：
> **Modular Living-World Kernel**

共同 core 候选能力：
- identity；
- world instance；
- canonical event；
- time；
- causality；
- authority；
- knowledge provenance；
- persistence/replay；
- action resolution boundary；
- orchestration；
- module registration / capability discovery。

可选 domain 示例：
- Economy
- Politics
- Law
- Disease
- Magic
- Cybernetics
- Religion
- Modern Finance
- Agriculture
- Warfare

具体 module registry / API 是工程候选，尚未 canonical。

---

# 17. Adaptive Simulation Fidelity 与 Deferred Concretization

## 17.1 Simulation LOD
世界不需要所有 NPC 永远满精度运行。

可分：
- 群体统计态；
- 低精度个体；
- 高精度持续角色。

进入重要因果链、与玩家有重要互动、形成长期关系等，可升级精度。

已经形成真实历史的实体不能因为离开视野就删除重抽。

`AI_DERIVED_CANDIDATE: Adaptive World Simulation LOD`

## 17.2 Deferred Concretization
远方区域可先保持宏观状态。
需要时才具体化：
- 必须服从已有历史/世界约束；
- 不得为了当前剧情倒改过去；
- 未观察、未产生后续依赖的细节可继续 UNKNOWN；
- Narrative 可从多个合法候选中偏向更有戏剧性的版本；
- 选择结合玩家近期体验、当前世界状态、已有约束；
- 候选与选择理由应可保留；
- 一旦被观察/被后续因果依赖则锁定程度提高。

用户强调：
Deferred Concretization 不是纯随机生成，而是“整体控制在约束内挑更适合当前体验、世界状态、戏剧性的合法版本”。

---

# 18. UNKNOWN 与随机

`UNKNOWN` 是合法世界状态。

如果：
- 已经发生并有历史证据 -> 不能重掷；
- 尚未确定且 world rule 允许随机 -> 可以可重放随机决定。

Narrative 只能在真正合法的未具体化空间参与选择。

---

# 19. 世界精度、群体与新实体生成

用户确认：
- 普通 NPC 可低精度/群体态存在；
- 重要 NPC 高精度持续存在；
- 普通人物进入重要因果链时升级；
- 新 NPC、组织、地点可在运行中真实出现；
- 新 NPC 要有人口来源；
- 新组织要经历形成过程；
- 新地点要有人口/资源/建设历史；
- Narrative 可建议，但不能凭空创建。

---

# 20. 地点与环境持续历史

## 20.1 地点
地点状态来自历史，不从初始地图模板自动恢复。
房子烧毁后会保持，除非有人真实维修/重建。

## 20.2 环境改变
砍森林可产生：
- 木材；
- 景观；
- 栖息地；
- 水土；
- 农业；
- 经济；
- NPC/机构反应。

## 20.3 建设
建设需：
- 土地；
- 材料；
- 人；
- 钱；
- 时间。
可受战争/缺钱等影响停工。

## 20.4 新地点
难民营可逐渐变成市场、聚落、镇子。
不是 Narrative 直接生成。

## 20.5 空间知识
`World Spatial Truth != Character Known Map`
可以有：
- 未知地点；
- 错误地图；
- 过期地图；
- 传闻路线。

## 20.6 地点社会身份
商业街、贫民区等应由经济、人口、治安、建筑、政策共同形成。
地点可拥有层叠历史，世界几十年后可真正改变玩家熟悉的地方。

---

# 21. 实体身份与物品连续性

## 21.1 唯一持续身份
用户明确希望每个实际独立物品拥有唯一持续身份。
后台可给随机稳定 ID（工程实现可用 UUID 等）。

用于：
- 道具；
- 武器；
- 服装；
- 重要材料；
- 证物等。

相同外观不等于相同实体。

`AI_DERIVED_CANDIDATE: PersistentEntityID`

## 21.2 聚合资源
普通批量物品可以聚合表示。
一旦某个物品进入独立重要因果链：
- 实例化；
- 获得独立身份；
- 历史持续。

## 21.3 Destroy / Split / Compose
已确认：
- 被摧毁的原实体 ID 保留历史，状态变 destroyed，不复用；
- 被拆开的部分获得新 ID；
- 多件材料组成新物体时，新物体获得新 ID；
- 不需要原子级追踪。

“拆/熔后的所有子实体是否必须完整保留 parent provenance”没有被用户完全确认，应保持候选/开放。

## 21.4 Possession / Ownership / Permission
必须分离：
- physical possession；
- legal/social ownership；
- shared/institutional ownership；
- custody；
- use permission；
- sell permission；
- worn/equipped state；
- spatial location。

小偷拿国王的剑：
- possession 可属于小偷；
- legal owner 仍可为国王；
- 黑市买家可能有不同 claim。

## 21.5 服装
两件同款衣服是不同实体：
- 各自污渍；
- 磨损；
- 修补；
- 染色；
- 历史。
Director 必须表现真实当前穿着那件。

`Possessed != Worn != Equipped`

## 21.6 藏匿
物品埋在树林：
- 有真实空间位置；
- 不再属于随身 inventory；
- 角色可记得位置；
- 他人可发现；
- 地形变化可影响。

## 21.7 社会价值
物品的物理属性不变，但历史可改变：
- 社会意义；
- 价格；
- 保护程度；
- 盗窃风险；
- Narrative价值。

---

# 22. 历史保存与可解释因果

用户确认：
- 重要 canonical event 长期保存；
- 小事件可压缩；
- 压缩不能破坏重要因果追溯；
- 与重要人物/物品/地点相关历史可保存更细；
- 很久以后仍应尽量回答：“为什么今天世界变成这样？”

重大状态应可追溯：
`谁做了什么 -> 消耗什么 -> 改变什么 -> 谁知道 -> 谁行动 -> 下一后果`

不是所有鸡毛蒜皮都需要同样精度。

---

# 23. 世界规则与类型

## 23.1 基础规则
底层 world rules 主要由开发者/世界设定定义。

## 23.2 世界运行可产生新制度/法律/发现
例如：
- 新法律；
- 新社会制度；
- 技术突破；
- 魔法研究发现；
但这些不是 runtime AI 任意修改 Meta-Laws。

## 23.3 类型世界
武侠、科幻、魔法、写实世界可加载不同扩展。
Narrative策略也可因类型变化。

但：
- World Truth；
- Authority；
- provenance；
- no-retcon
等 Meta-Laws 应保持。

---

# 24. 跨系统反馈与时间尺度

用户确认：
- 真实反馈循环允许存在；
- 如 `涨价 -> 囤积 -> 更短缺 -> 更涨价`；
- 按 canonical world time 逐步演化；
- 不能在一次调用中无限递归；
- 极端反馈可真的导致危机；
- Narrative 不能为了“剧情不好看”随意压制 world outcome。

不同 domain 可有不同 tick/更新节奏。
Orchestrator 可按因果依赖调度，互不依赖可并行，但必须可重放/一致。

---

# 25. 平凡人生是合法结果

如果玩家开酒馆十年：
- Narrative 可提供合法故事机会；
- 不需要强行制造灾难；
- 普通生活、人际、经营、时代变化本身可以有观赏性；
- 玩家主动寻求刺激时再提高 Exposure。

“没有宏大主线”不是系统失败。

---

# 26. 当前明确 Deferred / Later

1. `Hardcore Mode`：先有样品后再决定。
2. `Traditional Save/Load`：首版不作为基础。
3. `Multiplayer / Internet Version`：首版先做单机。
4. exact Narrative probability weights / thresholds：ruleset/policy。
5. long-absence world-advance 精确阈值/算法：open policy。
6. exact memory backend / decay math / relationship math：继续服从现有 OPEN_DECISION。
7. exact concurrency/arbitration algorithm：继续服从现有 `OD-CONCURRENCY-001`。
8. 法院、追溯法律等法律细节：暂不下钻，先保留高层分层。
9. 物品拆分/熔化后的完整 provenance 颗粒度：未完全确认。
10. multiplayer knowledge / network arbitration 的 runtime 细节：later phase。

---

# 27. 与当前 canonical architecture 的兼容方向

当前 canonical 已有的重要基础包括：
- stable machine ID；
- canonical event evidence；
- WorldInstance；
- ownership / possession / inventory / worn / equipped separation；
- ActorBaseProfile / SkillLedger / DerivedCapability / ActionDemandProfile；
- knowledge acquisition provenance；
- NPCEpisodicMemory / BeliefState；
- StoryBible / HardCausalAnchor / SoftDramaticAttractor / Storylet；
- Narrative Opportunity；
- AI Director downstream / renderer read-only；
- `NARRATIVE_NEED != PERMISSION_TO_CHANGE_WORLD_TRUTH`。

因此后续 architecture compilation 应优先：
- **扩展/明确现有 AF-A..H**
- **复用现有 authority**
- **不创建第二套 World Truth / Event Ledger / Character Ledger / Narrative Authority / Director Authority**

---

# 28. 高价值 Golden / Eval 候选

以下均为 candidate，不自动进入 canonical Golden registry：

1. 同时抢钥匙
   - timing advantage
   - method-specific capability
   - contested interaction
   - third party
2. 地下杀手组织
   - open intent
   - organization capability
   - law/evidence
   - police investigation
   - foreshadowing
3. 限价令与黑市
   - government policy
   - economic shortage
   - formal price vs actual market
   - corruption
4. Deferred town
   - macro history
   - later concretization
   - no-retcon
5. Persistent sword
   - ID
   - possession/ownership
   - evidence
   - social value
6. Forest removal
   - environment -> economy -> institutions
7. Butterfly history
   - small cause -> large consequence -> Director payoff
8. War-era tavern
   - opt-out
   - exposure preference
   - indirect world pressure
9. Player death succession
   - world continues
   - heir/partner/new character
10. Long absence return
   - frozen vs advanced policy
   - significant-change summary
11. False arrest
   - world truth / evidence / police belief / legal action
   - Director expresses low-skill misjudgment

---

# 29. Codex 架构施工原则

下一步应从 MIDS Discovery 进入 `ARCHITECTURE_COMPILATION`。

Codex 不应直接把本文逐字复制到 `ARCHITECTURE.md`，而应：

1. fresh reconcile canonical main；
2. 读取 `ARCHITECTURE.md`、machine contracts、Golden、Traceability；
3. 对本文每个设计意图做分类：
   - `ALREADY_CANONICAL`
   - `CANONICAL_CLARIFICATION`
   - `ARCHITECTURE_EXTENSION_CANDIDATE`
   - `OPEN_DECISION`
   - `RULESET/POLICY`
   - `LATER_PHASE`
4. 保持单一 authority；
5. 为真正架构缺口提出最小 contract/type additions；
6. 不把 tuning / product policy 写成永恒 architecture；
7. 为新增 invariant 提供 Golden candidate / negative case；
8. 只做 architecture/governance slice，不实现 runtime；
9. 不 self-review / Ready / merge。

---

# 30. 版本状态

版本：`v0.2`

覆盖范围：
- 原 v0.1 的 MIDS 第1~16轮主要确认内容；
- 后续语音确认的法律/证据高层规则；
- 总体架构回收；
- Architecture Closure；
- 第一阶段施工哲学；
- world initialization；
- future attractor；
- player-death succession；
- single-player offline policy；
- modular kernel；
- world history retention。

当前判断：
`DISCOVERY_SUFFICIENT_FOR_ARCHITECTURE_COMPILATION`

后续不再要求把整个宇宙所有细节问完。
新的关键矛盾在样品/架构实现中出现时，再重新启动 MIDS。
