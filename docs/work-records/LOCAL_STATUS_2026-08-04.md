# LOCAL_STATUS — 2026-08-04

本机快照。换机器或隔月后，用同结构新建 `LOCAL_STATUS_YYYY-MM-DD.md`。

---

## Git

```text
Repo:     C:\Users\26507\Documents\New_SBEs\Visual-HHG-Research
Remote:   https://github.com/Samgogo761/Visual-HHG-Research.git
Branch:   claude/vigilant-cori-F1gmg
HEAD:     9aadffe  (plugin v0.2.0 — static band viewer)
origin/claude/... : 140957e  (plugin v0.3.0 — occupation animation)  [LOCAL BEHIND 1]
origin/main:        6513d6d  (plugin ~0.1.1 after PR merges)
main ↔ claude:      diverged (~ ahead 3 / behind 2)
Working tree:       clean at snapshot time (docs/work-records may be new untracked)
```

最近相关提交（本地可见）：

```text
9aadffe Add AHHGXRBundleViewerActor: drop-in 3D band surface viewer (v0.2.0)
3318abc Add DescribeBundle one-call helper; document the VisualStudioTools RulesError
236f42a Make HHGXRLab plugin build on UE 5.4 / 5.5 / 5.6 / 5.7
b5e94ee Add HHGXRLab UE 5.3+ plugin (USTRUCT spec + JSON loader, no .uproject)
131dc13 Fix Wannier90 long-format band_path reader; add near-gap render hint
9216633 Wire coherence_kt.dat into the converter; mark solver Items 0/1/2 done
```

远端多出的关键提交：

```text
140957e Animate band colors by delta_n_cond(k,t) over occupation snapshots (v0.3.0)
```

---

## Python / 工具链

| 项 | 状态 |
|---|---|
| `tools/convert_sbe_run.py` | 可用；含 Wannier90 long + near-gap |
| `tools/validate_demo_bundle.py` | 真实 bundle 通过 |
| pytest | 本机曾测 **23 passed**（需安装 pytest） |
| matplotlib | quicklook 生成需要；缺失时 PNG 可能不写但仍可能声明 |

---

## 真实 bundle（本机）

```text
C:\tmp\hhgxr_first_real_bundle\
  manifest.json       (~2 KB)
  data_small.json     (~5.9 MB)
  quicklook_summary.png
```

- `dataset_name`: `verify_obs_exports_20260611_T2_1cycle`
- `field.source`: `raw_solver_output`
- `band_path.layout`: `wannier90_long`
- available_modules: 含 current / HHG / band_path / occupation / coherence / field / solver_output_Et_At 等（约 13 项）

源 run：

```text
C:\Users\26507\Documents\量子光研究\新SBEs\data\output_verify_obs_exports_20260611
```

Wannier band：

```text
C:\Users\26507\Documents\量子光研究\wannier\CrI3_band.dat
```

重跑命令（PowerShell 单行）：

```powershell
python tools/convert_sbe_run.py --run-dir "C:\Users\26507\Documents\量子光研究\新SBEs\data\output_verify_obs_exports_20260611" --band-path "C:\Users\26507\Documents\量子光研究\wannier\CrI3_band.dat" --out-dir "C:\tmp\hhgxr_first_real_bundle" --dataset-name "verify_obs_exports_20260611_T2_1cycle" --selected-bands 80:90 --confidence "verify_obs export-interface run (T2_cycles=1.0); final production baseline will be T2_cycles=0.5"
python tools/validate_demo_bundle.py --bundle "C:\tmp\hhgxr_first_real_bundle"
```

---

## Unreal（仓库内）

```text
unreal/HHGXRLab/          # 插件 only，无 .uproject
VersionName (local HEAD): 0.2.0
VersionName (origin tip): 0.3.0
```

宿主工程、材质、Blueprint：**不在本仓**。  
用户侧曾用 **UE 5.7** 验证编译 / DescribeBundle / 3D 能带；顶点色材质接线曾进行中。  
请在下方「本地资产备忘」补全路径（本人填写）：

```text
Host .uproject:     <待填，例如 D:\UE\HHGXRHost\HHGXRHost.uproject>
Surface material:   <待填资产名>
Last UE build OK:   <日期 / 是否成功>
```

---

## 已知坑（本机）

1. 本地分支落后远端 v0.3 —— 先 pull/审查再谈新功能。  
2. `output_verify_obs_nb112_T2_0p5cycle` 名不副实（实测 T2=1.0, lg_cov, 40×40）。  
3. 顶层 README 仍自称 Phase 0 —— 以 `docs/work-records/` 为准。  
4. 终端粘贴多行命令时可能断行失败 —— 用上文单行或脚本文件。  

---

## 快照后建议的第一动作

见 `NEXT_ACTIONS.md` → **A1–A3**。
