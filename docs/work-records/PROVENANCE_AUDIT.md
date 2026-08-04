# PROVENANCE_AUDIT — 数据目录命名 vs 真实参数

**审计日期：** 2026-08-04  
**方法：** 直接读取本机 `input.nml`，对照仓库 `PLAN.md` 表述。

对把物理可信度放在首位的项目，**命名错误优先于视觉问题**。

---

## 1. 核对结果

### A. `output_verify_obs_exports_20260611`（可信）

| 项 | 值 |
|---|---|
| 路径 | `...\新SBEs\data\output_verify_obs_exports_20260611\` |
| `gauge_method` | `lg_cov` |
| `nkx` / `nky` | 40 / 40 |
| `wvl_nm` / `ncyc` | 3200 / 4.0 |
| `T2_cycles` | **1.0** |
| 导出 | 含 `Et.dat`、`occupation_kt.dat`、`coherence_kt.dat` 等 |
| 角色 | 导出接口验证跑（verify_obs），**不是**最终 production |

与 PLAN / SOLVER_EXPORT_REQUESTS 描述一致。

### B. `output_verify_obs_nb112_T2_0p5cycle`（目录名误导）

| 项 | PLAN.md 写法 | 本机 `input.nml` 实测（2026-08-04） |
|---|---|---|
| T2 | `T2_cycles = 0.5` | **`T2_cycles = 1.0`** |
| gauge | `matrix_vg` | **`lg_cov`** |
| k 网格 | 46×46 | **40×40** |

**结论：目录名与 PLAN 段落均不可当作真相；必须以该目录内 `input.nml` / 日志为准。**  
早期「目录误标」判断成立；仅凭 PLAN 反驳误标的说法不成立。

---

## 2. 本地真实 bundle（转换产物）

路径：`C:\tmp\hhgxr_first_real_bundle`

| 字段 | 值 |
|---|---|
| `dataset_name` | `verify_obs_exports_20260611_T2_1cycle` |
| `source_class` | Data-driven |
| `gauge_method` | lg_cov |
| `field.source` | raw_solver_output |
| dimensions | nt=5045, 40×40, n_bands=112, n_valence=84, 52 occ/coh snapshots |
| `band_path.layout` | `wannier90_long`（修复后） |
| `near_gap_band_indices` | 典型为 gap 附近约 20 条（如 72–91） |
| 体积 | data_small ≈ 5.9 MB（band_path 修复后） |
| validator | 通过 |

物理抽检（2026-06 已记入 `docs/SOLVER_EXPORT_REQUESTS.md`）：

- E(t)：3200 nm × 4-cycle，跨度 ~42.7 fs，|E| 峰 ~21.3 fs  
- HHG：低阶奇次衰减；高阶峰 ~253H  
- δn_cond：t=0 为 0，脉冲后鼓起，峰值滞后于 |E|

---

## 3. 待办（写入 NEXT_ACTIONS A5/A7）

1. 更正 `PLAN.md` 中关于 `output_verify_obs_nb112_T2_0p5cycle` 的描述，或给目录重命名 / 加 `README_LOCAL.txt` 警告。  
2. 在任何对外材料中，禁止仅凭目录名假设 T2=0.5。  
3. 单独跑通真正的 **T2=0.5 + 三导出** production baseline，并用新目录名避免再次混淆。
