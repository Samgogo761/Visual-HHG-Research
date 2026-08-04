# PROJECT_STATE — HHG-XR Lab

**最后更新：** 2026-08-04  
**建议对外称呼：** HHG-XR Lab **v0.3 pre-alpha** — 数据到 Unreal 的动态科学可视化原型  
**仓库：** https://github.com/Samgogo761/Visual-HHG-Research

---

## 1. 一句话状态

数据管线与 provenance 契约基本完成；Unreal 插件可加载真实 bundle 并画出 3D 能带；远端 Claude 分支已有 occupation 时间动画；**尚无完整四面板桌面 UI、尚无 XR、尚无统一 canonical 分支。**

> 不是 Phase 0，也不是完整 Phase 2 / XR demo / 游戏产品。

---

## 2. 阶段对照（相对 ROADMAP）

| ROADMAP 层级 | 真实进度 | 说明 |
|---|---|---|
| Phase 0 数据管线 | **基本完成** | converter / validator / schema / near-gap 修复 / 合成样本 |
| Phase 1 桌面 Unreal | **约 40%** | loader + Viewer Actor；缺 `.uproject` 正式宿主、缺四面板 UMG |
| Phase 2 k 空间动态 | **约 20%** | 远端 v0.3 用 `delta_n_cond(k,t)` 着色；非 band-resolved ρ |
| Phase 3 Niagara | 未开始 | — |
| Phase 4 XR / OpenXR | 未开始 | — |
| 游戏 / 自由世界 | 不在本仓范围 | 见 `DECISIONS.md` 第二/三层 |

官方顶层 `README.md` 仍写 “v0 / No XR build yet”——**偏旧**；以本文件为准。

---

## 3. 分支与版本断层（必须先处理）

| 引用 | 提交 / 版本 | 内容 |
|---|---|---|
| `origin/main` | `6513d6d`，插件约 **0.1.1** | loader 为主；README 与 PLAN 内部也不完全同步 |
| 本地 `claude/vigilant-cori-F1gmg` | `9aadffe`，插件 **0.2.0** | 静态 3D band surface Viewer |
| `origin/claude/vigilant-cori-F1gmg` | `140957e`，插件 **0.3.0** | occupation snapshot 动画（本地 **落后 1 commit**） |

`main` ↔ Claude 分支：**diverged**（相对约 ahead 3 / behind 2）。  
当前无开放 Issue / PR / Release / Tag（以 2026-08-04 核对为准）。

**Canonical 建议：** 暂不把 Claude 分支直接快进 `main`；先开恢复分支审查 v0.3，再合并。

---

## 4. 已打通的技术链路

```text
Quantum-light (Wannier-SBE / Fortran)
    → Et, Jt, HHG, bands, occupation_kt, coherence_kt, …
    → tools/convert_sbe_run.py
    → manifest.json + data_small.json (+ quicklook PNG)
    → unreal/HHGXRLab 插件 (JSON loader + AHHGXRBundleViewerActor)
    → UE 5.x 宿主工程（本地，通常不在本仓）
    → 3D band surface + provenance badge
    → [v0.3] occupation 颜色随 snapshot 变化
```

### 已有能力

- Python：转换、消毒路径、校验、quicklook、合成样本、23 项测试（需 pytest）
- Bundle schema：`hhgxr-demo-bundle-v0`
- `band_path`：Wannier90 长格式 reshape + `near_gap_band_indices`
- Unreal：`LoadBundle` / `DescribeBundle` / Viewer Actor（ProceduralMesh）
- 物理诚实约定：能带几何不随激光抖动，只变 occupation 相关颜色

### 明显缺口

- 完整四面板 UI：band path / E·A / J(t) / HHG
- 仓库内无 `.uproject`（宿主工程在本地）
- 无 CI、无 License 声明（若尚未添加）
- 无 T2=0.5 + 三导出齐全的最终 production baseline
- XR / Niagara / AI 导览未开始

---

## 5. 数据基线

| 数据集 | 角色 | 备注 |
|---|---|---|
| `data/samples/demo_bundle_minimal` | 仓库内合成样本 | `Model-based`，可提交 |
| `output_verify_obs_exports_20260611` | 当前真实验证跑 | `lg_cov` 40×40，**T2=1.0**，含 Et/occ/coh |
| `C:\tmp\hhgxr_first_real_bundle` | 本地转换产物 | 已通过 validator；勿提交 |
| `output_verify_obs_nb112_T2_0p5cycle` | **目录名不可信** | 见 `PROVENANCE_AUDIT.md` |
| 目标 production | **尚未落地** | `T2_cycles=0.5` + Et + occupation + coherence |

材料默认：bilayer CrI3 AFM；模型 Wannier-SBE；gauge 目标 `lg_cov`。

---

## 6. UE / 本地宿主（仓库外）

本仓只含插件目录 `unreal/HHGXRLab/`。  
宿主 `.uproject`、材质、Blueprint、编译缓存通常在本机其他路径——**换对话时需在 LOCAL_STATUS 里写明**。

已知用户曾在 **UE 5.7** 上验证过插件编译与 `DescribeBundle` / 3D 能带显示；材质顶点色接线处于进行中。  
（具体宿主路径以最新 `LOCAL_STATUS_*.md` 为准。）

---

## 7. 外部参照（差异化）

- **SALMON VR**（2026）：实空间电子密度 + 矢势 → Meta Quest / PC  
- **本项目差异化：** k-space / 能带 / occupation–coherence–current–HHG 因果链 + spin/valley/geometry + provenance

---

## 8. 相关文档索引

| 文档 | 内容 |
|---|---|
| `PLAN.md` | 使命、数据政策、验收清单（部分段落可能过时） |
| `docs/ROADMAP.md` | 分阶段目标与非目标 |
| `docs/DATA_SCHEMA.md` | bundle 字段 |
| `docs/PHYSICS_PROVENANCE.md` | 来源标签 |
| `docs/UNREAL_IMPORT.md` | Unreal 读取约定 |
| `docs/SOLVER_EXPORT_REQUESTS.md` | solver 导出项与第一次真实 bundle 物理审计 |
| `unreal/HHGXRLab/README.md` | 插件用法 |
