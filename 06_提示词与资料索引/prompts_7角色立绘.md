# 七角色立绘提示词整理

共同正向前缀：

```text
masterpiece, best quality, high quality anime illustration, original character, single character, solo, full body, head to toe, centered character composition, complete horns, complete attached dragon tail, detailed eyes, detailed face, elegant anatomy, refined facial features, detailed maid uniform, intricate fabric folds, Victorian fantasy manor, warm candlelight, burgundy and ivory color palette, subtle cinematic lighting, clean silhouette, restrained background, shallow depth of field, consistent character design, polished cel shading, painterly details, visual novel character art, safe for public gallery
```

共同负面：

```text
worst quality, low quality, lowres, blurry, pixelated, jpeg artifacts, bad anatomy, bad proportions, malformed body, deformed, disfigured, extra arms, extra legs, extra fingers, missing fingers, fused fingers, bad hands, malformed hands, broken wrist, duplicated body parts, multiple people, crowd, two characters, cropped head, cropped horns, cropped feet, cropped tail, detached tail, floating tail, tail coming from wrong position, mismatched horns, asymmetrical eyes, cross-eyed, poorly drawn face, flat lighting, harsh neon lighting, cyberpunk neon, purple blue gradient, plain white background, plain black background, cluttered background, text, letters, subtitle, logo, watermark, signature, frame, UI, card border, official character, copyrighted character, existing anime character, explicit nudity, nipples, genitalia, sex act, fetish pose
```

本批次文件名和种子：

| 角色 | 输出文件 | 种子 | LoRA |
|---|---|---:|---|
| 管家 Hasuki | `01_hasuki_butler_dragonmaid_00001_.png` | 202608210701 | `dragonmaid_public_illustrious_v4\01_House_dragonmaid_illuXL_v1.safetensors` |
| 小红 Tillroo | `02_tilulu_kitchen_dragonmaid_00001_.png` | 202608210702 | `dragonmaid_public_illustrious_v4\02_Kitchen_dragonmaid_illuXL_v1.1.safetensors` |
| 小绿 Parla | `03_parlura_parlor_dragonmaid_00001_.png` | 202608210703 | `dragonmaid_public_illustrious_v4\03_Parlor_dragonmaid_illuXL_v1.1.safetensors` |
| 小蓝 Laundry | `04_laundry_dragonmaid_00001_.png` | 202608210704 | `dragonmaid_curated_v4\04_小蓝_Laundry-SFW-only-pilot20-r32.safetensors` |
| 小粉 Nasary | `05_nasali_nurse_dragonmaid_00001_.png` | 202608210705 | `dragonmaid_public_illustrious_v4\05_Nurse_dragonmaid_illuXL_v1.1.safetensors` |
| 小金 Latys | `06_elde_noble_dragonmaid_00001_.png` | 202608210706 | `dragonmaid_public_illustrious_v4\06_Latys_dragonmaid_illuXL_v2.safetensors` |
| 小黑 Chame | `07_chieim_chamber_dragonmaid_00001_.png` | 202608210707 | `dragonmaid_public_illustrious_v4\07_Chamber_dragonmaid_illuXL_v1.1.safetensors` |

模型参数：

```text
checkpoint: sdxl\waiIllustriousSDXL_v150.safetensors
size: 832x1216
sampler: dpmpp_2m
scheduler: karras
steps: 28
cfg: 5.0
denoise: 1.0
```
