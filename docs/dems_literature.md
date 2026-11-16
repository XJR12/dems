# DEMS / EC-MS 文献核查：RuO₂ 酸性析氧数据如何判读

日期：2026-10-17。本文只汇总外部原始研究与方法论文，尚未据此判断本项目三组原始曲线。DEMS 不同构型（电极覆膜、薄层流动池、探针/芯片入口）的传质与采集效率不同；下述数值不能直接套入未知仪器。

## 可用于当前问题的结论

1. **m/z 32 是常规水中产出的主氧峰，但原始离子电流不是 OER 活性的排序尺。** Bruckenstein/Gadde 于 1971 年开创多孔电极在线质谱采气；1984 年提出 DEMS 的 Wolter/Heitbaum 在其特定多孔电极贴膜构型中证明，质量信号可随法拉第产物生成速率变化且足以跟随 CV；后来的 EC-MS 方法论文明确将实测强度分解为电极产物到入口的收集、入口到真空的传递和质谱灵敏度等因素。换样品而改变膜距、涂层厚度、气泡、流动、质谱调谐/真空背景时，绝对基线和峰高都可能改变。尤其不能从“4.5% 峰最高”直接推出其本征 OER 最好，也不能从“纯 RuO₂ 基线最高”推出其持续产氧最多。[^bruckenstein][^wolter][^trimarco]
2. **周期峰在 CV 下是预期现象；应对齐电位、电流和 m/z 32 的时间。** 原始 DEMS 就是用“质量谱循环伏安曲线”跟踪随电位变化的产物。实际电极到采样膜的扩散、流池滞留及真空系统响应会使质谱曲线相对电化学电流延迟并变宽；各样品传质条件变化会让峰值位置和峰高变化。Krempl 等测量 O₂/H₂ 生成的脉冲响应，证明质量信号通常不直接等于瞬时产物分电流，并用传质模型反卷积恢复动态速率。评判某个峰必须同时知道该时段的电位、扫描方向与电流，且要先测系统时滞/响应。[^wolter][^krempl]
3. **较高稳定基线与较小脉冲可同时出现，不能视为矛盾。** 可用概念模型 `S32(t)=B32(t)+K·[h* rO2](t)`：`B32` 是气路残氧/溶解氧/真空背景等背景，`rO2` 是瞬时 O₂ 生成速率，`h` 是该池体、流速、膜、气泡条件下的延迟及展宽响应，`K` 为检测灵敏度。背景与电位触发的增量是不同的量；相同生成量在更宽的响应里峰更矮、面积可相近。此式是依据原始方法论文的工作模型做出的分析表达，不是对当前三条曲线的已证实拟合。[^wolter][^krempl]
4. **优先比较各周期经背景扣除的完整峰面积/积分产氧，再比较峰高；定量还须校准。** 每一圈在 OER 电位窗内的 O₂ 量来自基线扣除后的 m/z 32 积分与该通道灵敏度/收集效率校准，积分窗口须覆盖响应尾巴；对应电荷量应使用 OER 部分而不是把双电层与 Ru 氧化还原电荷全算作 OER。可写 `n(O₂)=∫[S32−B32]dt / k32`（`k32` 由同构型的已知产氧量校准，单位依仪器定义）及 `FE_O2=4F·n(O₂)/Q_OER`。若没有同构型校准与同步电化学数据，只能做受限的相对比较，不宜报告绝对 FE。2026 年 Bondue 等的 RuO₂ 同位素 DEMS 方法论文实际逐圈积分 m/z 32/34、在变化背景上分辨短促 CV 峰，并将每圈比例放到 OER 电荷轴上分析，明确指出扫速与电位上限改变每圈采样尺度。[^bondue][^trimarco]
5. **不能把“产氧越多”直接等同于“催化剂越好”。** 活性是相同电位/过电位、相同负载与 iR 处理下的 OER 电流/产氧速率；选择性或法拉第效率是产氧对通过电荷的比例；稳定性还涉及 Ru 溶出/结构变化。RuO₂ 原始研究显示其活性与稳定性对表面预处理高度敏感，另一项 EQCM+ICP-MS 研究说明稳定性须独立监测质量损失；m/z 32 单条轨迹无法给出这三个维度。[^paoli][^frydendal]
6. **无 ¹⁸O 标记时，34/36 非零也应极弱，不能用其弱或无来判 AEM/LOM。** NIST 天然氧同位素近似分数为 ¹⁶O 0.99757、¹⁸O 0.00205。若随机组合，¹⁶O¹⁸O/¹⁶O₂ 约 `2p18/p16≈0.0041`，¹⁸O₂/¹⁶O₂ 约 `(p18/p16)^2≈4.2×10⁻⁶`；实际离子强度还受质量通道灵敏度、碎片/背景影响。这些是天然丰度的数量级，不是仪器检出下限。RuO₂ 晶格氧问题必须进行受控 ¹⁸O 标记、换液及对应空白/灵敏度验证；仅靠 m/z 32 和天然丰度 34/36 没有机理判别力。[^nist][^bondue]

## 针对“基线和峰高反向”的可检验解释

| 现象 | 文献支持的可能因素 | 本数据必须补的证据 |
|---|---|---|
| 纯 RuO₂ 基线高、CV 脉冲小 | 背景 O₂/残氧较高；或更宽/更慢的采样响应压低峰值；也可能是持续 OER 与每圈增量不同 | OCV/低电位背景、惰性气体/流速记录、与电流同步的相位、固定电位阶跃响应、逐圈积分面积；不能只凭图定因。[^trimarco][^wolter] |
| 4.5% Ce 基线低、脉冲高 | 较低背景配上较尖锐的瞬时响应；局部产氧集中；气泡形成/脱附或膜入口附近气体输运变化，均是待检验假设 | 完整峰面积、同圈 OER 电荷、流速及气泡可视记录、重复上/下扫。气泡会显著改变电极 OER 测量，但目前无证据断定它就是此图峰高的原因。[^trimarco][^bubble] |
| 3% Ce 阶梯式下移、形状复杂 | 缓慢背景漂移、溶解氧置换、流路/气泡/膜状况变化、样品表面演化都可造成非平稳曲线，现阶段无法区分 | 将无 OER 窗口拟合为逐圈的局部背景，原始基线单独作图；复查 m/z 28/40（若测了）、流速、腔室压力、CV 电流和电极状态。不可用一条全程常数基线强行扣除。[^trimarco][^bubble] |

上述三行是**排查假设**，不是对当前实验的原因判定。特别是气泡一项，原始的 OER 气泡研究证明电极表面覆盖可使测得的电化学活性严重失真；它并未证明本实验 DEMS 峰必由气泡造成。[^bubble]

## RuO₂ 晶格氧：原始研究并不一致

- Wohlfahrt-Mehrens/Heitbaum（1987）以同位素标记与在线 MS 研究 Ru/RuO₂，报告氧化物氧参与。Macounová 等（2009）在 0.1 M HClO₄ 中的 ¹⁸O-DEMS 报告反应随电位变化，高电位出现电解液与催化剂氧交换。[^wohlfahrt][^macounova]
- Stoerzinger 等（2017）对有取向的 RuO₂ 面、薄膜和颗粒做在线 EC-MS，在其酸/碱条件下均未发现可检测到的晶格氧交换；他们指出这与早期结果相异。[^stoerzinger]
- Bondue 等（2026）以 ¹⁸O 换液和模拟检测限核查 RuO₂ 纳米颗粒及 Ru；在其条件与模型假设下没有看到超出天然丰度的 34 信号或电荷轴上的衰减，并将晶格氧交换形成 O₂ 的比例上界估为 10% 左右。作者也展示，换液不彻底可制造看似随圈数衰减的 34 信号，并强调对水合/无定形表层，清晰的“晶格氧/吸附氧”界线可能失效。该上界**不能推广到所有 Ce 掺杂 RuO₂、所有电位和所有表面结构**。[^bondue]
- 因此，对本项目无同位素标记的 DEMS，只能讨论 O₂ 输出、与电流的耦合、随循环的变化；不能从 32 峰形推断“3% Ce 抑制 LOM”或“4.5% Ce 促进 LOM”。

## 判读顺序（供主分析调用）

1. 确认三组同一电解液、负载/面积、CV 电位上下限/扫速/循环数、膜/入口几何、流速、载气、采样顺序、质谱设置和 m/z 32 灵敏度；记录测试前后是否清洗、换液、除氧。
2. 将时间轴上的电位、法拉第电流、m/z 32 同步；找出每圈 OER 电位窗和相对延迟。若无同步日志，至少利用 CV 周期寻找相位，但不得擅自赋予绝对电位。
3. 保留原始信号，标记每圈低电位/无 OER 段的局部背景；检查阶梯变化在 m/z 28/40、压力或流速中是否同步出现。先画 `S32`、`B32`、`S32−B32` 三条图，避免把漂移吸收到“活性”里。
4. 逐圈取完整响应峰积分，连同峰高、峰宽、起峰电位、尾部和电化学 `Q_OER` 一起报告。面积若因阶梯基线而强依赖扣背景方案，给出合理背景方案的敏感性范围。
5. 若做过同仪器同构型校准，算绝对 O₂ 量与 FE；否则只在严格同构型且采样效率稳定的前提下给出“相对积分信号”，并与既有性能排序做相互核验。重复运行/互换测试顺序可检出顺序漂移。

## 原始来源

[^bruckenstein]: S. Bruckenstein and R. R. Gadde, “Use of a porous electrode for in situ mass spectrometric determination of volatile electrode reaction products,” *Journal of the American Chemical Society* 93, 793–794 (1971). DOI: [10.1021/ja00732a049](https://doi.org/10.1021/ja00732a049). 早期电化学在线质谱原始短文。
[^wolter]: O. Wolter and J. Heitbaum, “Differential Electrochemical Mass Spectroscopy (DEMS)—a New Method for the Study of Electrode Processes,” *Berichte der Bunsengesellschaft* 88, 2–6 (1984). DOI: [10.1002/bbpc.19840880103](https://doi.org/10.1002/bbpc.19840880103). 原论文摘要明确写明多孔工作电极、膜入口、质量强度与法拉第电流比例及 CV 时间响应。
[^trimarco]: D. B. Trimarco *et al.*, “Enabling real-time detection of electrochemical desorption phenomena with sub-monolayer sensitivity,” *Electrochimica Acta* 268, 520–530 (2018). DOI: [10.1016/j.electacta.2018.02.060](https://doi.org/10.1016/j.electacta.2018.02.060). 原论文比较 DEMS 与芯片 EC-MS 的入口/真空收集效率、响应时间和传质；其 100% 收集效率是特定芯片系统的结果，不能套用于一般 DEMS。
[^bondue]: C. J. Bondue *et al.*, “Evaluating Differential Electrochemical Mass Spectrometry as a Tool to Probe the Lattice Oxygen Exchange Mechanism of Oxygen Evolution at Transition Metal Oxide Catalysts,” *ChemCatChem* (2026). DOI: [10.1002/cctc.202501346](https://doi.org/10.1002/cctc.202501346). 开放原文给出 RuO₂ 0.5 M H₂SO₄、5 µL/s、10 mV/s 的 DEMS 范例、逐圈积分与换液伪影测试。
[^nist]: NIST Physical Measurement Laboratory, [Atomic Weights and Isotopic Compositions for Oxygen](https://physics.nist.gov/cgi-bin/Compositions/stand_alone.pl?ele=O), 官方同位素组成表：¹⁶O 0.99757、¹⁷O 0.00038、¹⁸O 0.00205。
[^bubble]: A. Logar *et al.*, “Bubble Trouble: Quantifying the Effects of Bubbles on the Electrochemical Interface,” *ACS Catalysis* 15, 6380–6385 (2025). DOI: [10.1021/acscatal.5c00144](https://doi.org/10.1021/acscatal.5c00144). 原始电极成像、电化学和模型表明 OER 气泡覆盖影响表观极化，支持将气泡视为必须排查的因素。
[^krempl]: K. Krempl *et al.*, “Dynamic Interfacial Reaction Rates from Electrochemistry–Mass Spectrometry,” *Analytical Chemistry* 93, 7022–7028 (2021). DOI: [10.1021/acs.analchem.1c00110](https://doi.org/10.1021/acs.analchem.1c00110). 原始开放论文实测 O₂/H₂ 脉冲响应，并提出质量信号是电极产物流率与系统响应函数的卷积；[作者原始数据与脚本](https://github.com/kkrempl/Dynamic-Interfacial-Reaction-Rates)。
[^paoli]: E. A. Paoli *et al.*, “Oxygen evolution on well-characterized mass-selected Ru and RuO₂ nanoparticles,” *Chemical Science* 6, 190–196 (2015; online 2014). DOI: [10.1039/C4SC02685C](https://doi.org/10.1039/C4SC02685C). 原始实验显示 RuO₂ 纳米颗粒活性与稳定性对表面预处理敏感。
[^frydendal]: R. Frydendal *et al.*, “Benchmarking the Stability of Oxygen Evolution Reaction Catalysts: The Importance of Monitoring Mass Losses,” *ChemElectroChem* (2014). DOI: [10.1002/celc.201402262](https://doi.org/10.1002/celc.201402262). 原始 EQCM/ICP-MS RuO₂ 研究，说明溶出/质量损失需要独立测量。
[^wohlfahrt]: M. Wohlfahrt-Mehrens and J. Heitbaum, “Oxygen evolution on Ru and RuO₂ electrodes studied using isotope labelling and on-line mass spectrometry,” *Journal of Electroanalytical Chemistry* 237, 251–260 (1987). DOI: [10.1016/0022-0728(87)85237-3](https://doi.org/10.1016/0022-0728(87)85237-3). 早期同位素原始实验。
[^macounova]: K. Macounová, M. Makarova and P. Krtil, “Oxygen evolution on nanocrystalline RuO₂ and Ru₀.₉Ni₀.₁O₂−δ electrodes—DEMS approach to reaction mechanism determination,” *Electrochemistry Communications* 11, 1865–1868 (2009). DOI: [10.1016/j.elecom.2009.08.004](https://doi.org/10.1016/j.elecom.2009.08.004). 其摘要直接报告电位依赖的氧交换。
[^stoerzinger]: K. A. Stoerzinger *et al.*, “Orientation-Dependent Oxygen Evolution on RuO₂ without Lattice Exchange,” *ACS Energy Letters* 2, 876–881 (2017). DOI: [10.1021/acsenergylett.7b00135](https://doi.org/10.1021/acsenergylett.7b00135). [作者机构存档原文](https://scholarlypublications.universiteitleiden.nl/access/item%3A2940066/view)。
