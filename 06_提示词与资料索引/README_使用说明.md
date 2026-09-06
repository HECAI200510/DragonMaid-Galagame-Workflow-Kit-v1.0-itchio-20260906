# 龙女仆七角色 LoRA 存档包

## 推荐底模

`sdxl/waiIllustriousSDXL_v150.safetensors`

## 人形态推荐配置

| 角色 | LoRA | 推荐权重 | 主要触发词 | 状态 |
|---|---|---:|---|---|
| 管家 | `01_House_Hasuki.safetensors` | 0.68–0.76 | `hasuki_dmaid, adult house dragonmaid` | 当前旧推荐，眼镜和管家身份较稳 |
| 小红 | `02_Kitchen_Tillroo.safetensors` | 0.68–0.78 | `kitchen dragonmaid` | 公开 Illustrious，红发和青角较稳 |
| 小绿 | `03_Parlor_Parla.safetensors` | 0.68–0.76 | `parlor dragonmaid` | 公开 Illustrious |
| 小蓝 | `04_Laundry_SFW_ONLY.safetensors` | 0.68–0.76 | `laundry dragonmaid` | 永久仅 SFW |
| 小粉 | `05_Nurse_Nasary.safetensors` | 0.68–0.78 | `nurse dragonmaid` | 公开 Illustrious |
| 小金 | `06_Latys.safetensors` | 0.72–0.82 | `dragonmaid latys` | 当前公开候选，仍需注意发型 |
| 小黑 | `07_Chamber_Chame.safetensors` | 0.70–0.80 | `chamber dragonmaid` | 公开 Illustrious |

## 去除“油腻感”推荐

正向风格前缀：

```text
clean anime visual novel CG, matte skin, soft cel shading, flat controlled highlights, pastel color palette, low saturation, clean lineart, anime screenshot, natural body proportions
```

负向：

```text
oily skin, glossy skin, wet skin, shiny skin, plastic skin, greasy highlights, oversaturated, heavy bloom, harsh contrast, hyperrealistic skin, exaggerated breasts, inflated body
```

建议 LoRA 从 `0.68–0.76` 开始，不要默认拉到 0.9。CFG 建议 4.2–4.8。不要同时堆叠 `amazing quality`、`very aesthetic`、`cinematic glossy lighting` 和多个 NSFW 风格 LoRA。

## 龙形态预留

`DragonForm_预留_未最终验收` 中是当前可调用候选，不代表最终定版。小金没有官方对应龙形态。

- 管家：`dragonmaid sheou`
- 小红：`dragonmaid tinkhec`
- 小绿：`dragonmaid lorpar`
- 小蓝：`dragonmaid nudyarl`（当前由 Nurse v1.1 内置数据提供，仅 SFW）
- 小粉：`dragonmaid ernus`
- 小黑：`dragonmaid stern`

多人图不要直接叠加多个 LoRA。当前四人矩形分层拼接方案已判失败，不应作为成品工作流。
