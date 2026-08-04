# 工作记录入口（先看这里）

本文件夹是 **HHG-XR Lab / Visual-HHG-Research** 的交接与状态快照。
隔几个月、换 AI、换电脑时，**先打开本目录**，不必翻旧聊天。

| 文件 | 用途 |
|------|------|
| [PROJECT_STATE.md](./PROJECT_STATE.md) | 项目当前阶段、分支、能力边界（可进 Git） |
| [NEXT_ACTIONS.md](./NEXT_ACTIONS.md) | 按优先级排列的下一步待办 |
| [DECISIONS.md](./DECISIONS.md) | 已拍板的定位与产品分层（科研 / 观测站 / XR） |
| [LOCAL_STATUS_2026-08-04.md](./LOCAL_STATUS_2026-08-04.md) | 2026-08-04 本机实测快照（路径、版本、验证结果） |
| [PROVENANCE_AUDIT.md](./PROVENANCE_AUDIT.md) | 物理数据目录命名与真实参数对照（含误标） |

## 30 秒结论

> **身份：** 物理可信的数据驱动空间交互原型（不是 VR 游戏仓）。  
> **阶段：** HHG-XR Lab **v0.3 pre-alpha**（数据底座完成 + Unreal 接入 + occupation 动画代码在远端分支）。  
> **最大风险：** `main` / Claude 分支 / 本地 / 文档不同步。  
> **下一步：** 恢复分支 → 取回 v0.3 → 修正 provenance → 再做完整桌面纵向切片。

## 相关仓库与本地路径

- GitHub：https://github.com/Samgogo761/Visual-HHG-Research
- 本仓本地：`C:\Users\26507\Documents\New_SBEs\Visual-HHG-Research`
- Solver：https://github.com/Samgogo761/Quantum-light
- 当前真实验证 bundle：`C:\tmp\hhgxr_first_real_bundle`
- SBE 源数据（勿提交）：`C:\Users\26507\Documents\量子光研究\新SBEs\data\`

## 更新规则

换里程碑时：

1. 改 `PROJECT_STATE.md` 顶部的「最后更新」与阶段表。
2. 新增或覆盖一份 `LOCAL_STATUS_YYYY-MM-DD.md`。
3. 勾掉 `NEXT_ACTIONS.md` 已完成项，补新项。
