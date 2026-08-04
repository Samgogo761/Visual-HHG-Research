# DECISIONS — 已拍板的定位与边界

**最后更新：** 2026-08-04  
这些决策用于防止 scope creep，并连接「科研工具」与「游戏 / XR 梦想」。

---

## D1. 仓库身份

**本仓是：** 物理可信、数据驱动的科学空间交互原型（HHG-XR Lab）。  
**本仓不是：** VR 游戏产品、实时 SBE solver、SAO 式自由世界平台。

继续做的理由：有差异化（k-space 因果链 + provenance），且可作为 Unreal / XR / AI 空间交互的硬地基。  
不继续做成大众游戏的理由：玩法未设计；科研可信度会被污染；外部已有 SALMON VR 证明「仅进 VR」不够新。

---

## D2. 三层价值（分层，不混仓目标）

| 层 | 名称 | 目标 | 与本仓关系 |
|---|---|---|---|
| 1 | **HHG-XR Lab** | 真实数据、provenance、k-space、HHG、occupation/coherence、可交互查看 | **本仓核心，优先保护** |
| 2 | **Attosecond Observatory / 阿秒观测站** | 实验室场景、任务、谜题、受约束的 AI 助教 | 第二层体验；可后挂 |
| 3 | **AI + XR 空间世界** | AI 角色、自然语言操控、跨设备 XR、多材料 | 长期；在 1–2 稳定后 |

梦想映射：茅场式「可信可交互世界」≈ 层 1 的规则与诚实 + 层 2/3 的体验；**不是**直接做 Full Dive BCI。

---

## D3. 物理可视化诚实规则

1. 每个视觉量必须有 provenance（`Data-driven` / reconstructed / unavailable 等）。  
2. 能带几何默认静态；occupation / coherence 驱动颜色或辅通道，**不**为戏剧效果让带结构随激光频率抖动。  
3. 未导出的物理量不得由 AI 或 UI「编造显示」。  
4. 验证跑（T2=1.0）与 production 基线（目标 T2=0.5）必须在 `dataset_name` / confidence 中区分。

---

## D4. 技术优先级

```text
physics provenance
  > 仓库卫生与分支统一
  > 可复现数据转换
  > 桌面纵向切片（E → occ → J → HHG）
  > 阿秒观测站包装
  > OpenXR / Niagara / 生成式世界
```

引擎侧：当前以 **UE 5.7** 复验为准；不必立即升 5.8，但路线保留 OpenXR。

---

## D5. 数据政策（不变）

- 永不提交原始 `*.dat` / `*.tb` / `*.hr` / 大型 `*.npz` / 私有绝对路径  
- 公开 manifest 使用 `<LOCAL_SBE_RUN_DIR>` 等占位符  
- 合成样本可进仓；真实生产数据只留本机或受控存储  

---

## D6. 与外部 AI 审计的关系

2026-08 两份外部 AI 审计大体正确，但：

- 关于 `output_verify_obs_nb112_T2_0p5cycle` 是否误标：**以本机 `input.nml` 实测为准**（见 `PROVENANCE_AUDIT.md`）。  
- 以后以本目录文件为「唯一状态真相」，旧聊天仅作背景。
