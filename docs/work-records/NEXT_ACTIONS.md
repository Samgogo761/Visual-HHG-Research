# NEXT_ACTIONS — 下一步待办

**最后更新：** 2026-08-04  
原则：**先同步与封账，再扩视觉；先桌面因果链，再 XR / 游戏包装。**

状态标记：`[ ]` 未做 · `[~]` 进行中 · `[x]` 完成

---

## A. 恢复与封账（当前最高优先级）

- [ ] **A1** 从 `origin/claude/vigilant-cori-F1gmg` 取回 **v0.3.0**（`140957e`），在新分支审查（建议名：`recovery/2026-08`），**不要直接改 `main`**
- [ ] **A2** 本地 `git pull` / merge 后确认插件 `VersionName` 变为 `0.3.0`，occupation 控件可见
- [ ] **A3** 用 `C:\tmp\hhgxr_first_real_bundle`（或重跑 converter）在 UE 5.7 验证：
  - 能带曲面加载
  - provenance badge：`Data-driven | lg_cov | field: raw solver`
  - Play 下 occupation 动画：导带变亮、价带变暗，峰值附近鼓起
- [ ] **A4** 修正文档漂移：顶层 `README.md`、`PLAN.md` 与本目录状态对齐；标明当前是 v0.3 pre-alpha
- [ ] **A5** 处理 provenance 误标（见 `PROVENANCE_AUDIT.md`）：`output_verify_obs_nb112_T2_0p5cycle` 目录名与真实 `T2=1.0` 不一致
- [ ] **A6** 明确唯一 canonical 参数集（k40 vs k46、nb104 vs full112、gauge、T2），写进 `PROJECT_STATE.md`
- [ ] **A7** 规划并执行一次 **T2=0.5 + Et + occupation + coherence** 的 production baseline 重跑；保存 input.nml / log / 哈希 / bundle
- [ ] **A8** 补齐工程卫生：Python 依赖声明、CI（至少 pytest + validate）、License；修「缺 matplotlib 仍声明 quicklook」类问题

---

## B. 完整桌面纵向切片（Phase 1 收尾）

目标体验（可录屏）：

```text
激光 E(t)/A(t) → k 空间 Δn_cond → J(t) → HHG 谱
```

- [ ] **B1** 仓库内或旁路建立可复现的宿主工程说明（`.uproject` 是否进仓另议；至少写清本地路径）
- [ ] **B2** 四面板 UI：band path（near-gap）/ field / current / HHG
- [ ] **B3** 点击 HHG 峰显示 harmonic order / ω
- [ ] **B4** 时间轴 scrub 与 occupation / field 联动
- [ ] **B5** 截图 + 短录屏 + 最小用户测试清单
- [ ] **B6** 二维图表保持清晰；三维仅用于能带 / occupation 空间关系

---

## C. 可选：阿秒观测站包装（第二层产品）

在 B 完成后另开体验层（可同仓子目录或新仓）：

- [ ] **C1** 场景叙事：未来实验室 / 观测站
- [ ] **C2** 受 provenance 约束的 AI 讲解员（不得编造未导出物理量）
- [ ] **C3** 轻量任务 / 谜题（调偏振、看占据、认谐波）

---

## D. 更后：XR 与扩展（第三层）

- [ ] **D1** OpenXR / PCVR 最小头显构建（先别追 Android XR）
- [ ] **D2** Niagara（仅当 2D/3D 面板已证明叙事清楚）
- [ ] **D3** band-resolved occupation / 量子光统计（依赖 solver 导出）

---

## 明确不做（现在）

- 不把本仓做成 SAO 式自由世界 / 社交平台
- 不提交原始 `*.dat` / Wannier TB / 私有绝对路径
- 不为好看而让能带几何随激光频率抖动
- 在 production baseline 落地前，不对外宣称「最终物理基线」

---

## 建议执行顺序（最短路径）

1. A1–A3（恢复 v0.3 + UE 复验）  
2. A4–A5（文档与 provenance）  
3. A7（T2=0.5 production）  
4. B1–B5（桌面纵向切片）  
5. 再考虑 C / D  
