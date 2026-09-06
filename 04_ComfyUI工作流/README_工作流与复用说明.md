# 龙女仆 Unity/RPG CG 正确基线整理（2026-08-29）

本包从 `Unity_RPG_AssetPack_20260806/正确基线_精选70真实工作流与模型` 反查生成链路，未采用顶层六个仅用于尺寸/后处理的模板冒充真实生图流。

## 固定基线

- Checkpoint：`sdxl\waiIllustriousSDXL_v150.safetensors`
- LoRA 权重：Model `0.78` / CLIP `0.72`
- Sampler：`dpmpp_2m_sde`
- Scheduler：`karras`
- Steps：`28`
- CFG：`4.8`
- 分辨率：`1216 × 832`（保持原 832×1216 的像素量，改成事件 CG 横构图）
- 输出：`D:/DMT-AI-Studio/output/DragonMaid/Unity_RPG_CG_20260829`
- 内容：全 SFW；小蓝只使用全年龄、非恋爱、完全遮盖场景。

## 目录

- `01_原始六套通用模板`：原资产包顶层通用模板，仅负责立绘/脸图/像素尺寸。
- `02_真实工作流_每角色代表`：原精选 70 中逐图 API 流的每角色代表。
- `03_新CG_API_七角色各10`：本次可直接通过 ComfyUI API 运行的 70 个工作流。
- `提示词_七角色各10.md`：逐图正向提示词。
- `参数清单.csv`：每图模型、LoRA、权重、种子及输出前缀。

## 复用原则

先锁定 checkpoint、角色 LoRA、权重和服饰身份词；每张只替换动作、神态、镜头和少量环境接触。多人图不要直接叠多个全局 LoRA，应另走区域控制或分人生成后合成。
