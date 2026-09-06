# 龙女仆公开模型推荐提示词 Note

> 说明：这些是本机已下载公开 LoRA 的作者触发词/归档说明中记录的推荐词，不是《游戏王》官方发布的 AI 提示词。项目补充的发色、角、尾巴和服装词单独列出，避免混淆来源。

## 通用底模与建议

- 底模：`sdxl\waiIllustriousSDXL_v150.safetensors`
- 人形 LoRA 起步权重：模型 `0.68–0.78`，CLIP `0.60–0.70`
- 先写角色触发词，再写动作和神态；不要让长场景词抢角色身份。
- 单角色优先使用 `solo, 1girl`。多人图必须使用区域蒙版或分角色生成。

## 七个人形角色

| 中文名 | 公开模型触发词 | 项目身份补充词 |
|---|---|---|
| 管家 | `hasuki_dmaid, adult house dragonmaid` | `glasses, long dark brown hair, black curved horns, black formal maid uniform, white apron, attached dark tail` |
| 小红 | `kitchen dragonmaid` | `adult woman, long straight red hair, cyan blue eyes, turquoise branching dragon horns, thick red dragon tail, brown long-sleeved maid dress, white ruffled bib apron, turquoise cuffs` |
| 小绿 | `parlor dragonmaid` | `adult woman, short green hair, twin-tail silhouette, green horns, leafy green tail, black and white maid uniform` |
| 小蓝 | `laundry dragonmaid` | `young blue-haired dragon girl, short blue hair, small blue horns, blue and white laundry uniform, fluffy blue tail, child-safe, fully covered` |
| 小粉 | `nurse dragonmaid` | `adult woman, pink hair, curved horns, pink nurse maid uniform, attached pink tail` |
| 小金 | `dragonmaid latys`；自训身份词：`latys_dmaid` | `adult noble maid, blonde hair, elegant bangs, golden horns, elegant maid dress, attached golden tail` |
| 小黑 | `chamber dragonmaid` | `adult woman, long white hair, black horns, black and white bedroom maid uniform, attached dark tail` |

## 六种龙形态

| 人形对应 | 龙形名称/触发词 | 备注 |
|---|---|---|
| 管家 | `dragonmaid sheou` | 融合龙形；避免卡框、卡图背景 |
| 小红 | `dragonmaid tinkhec` | 红黑龙体、青色角与装甲点缀 |
| 小绿 | `dragonmaid lorpar` | 绿色植物/羽翼结构 |
| 小蓝 | `dragonmaid nudyarl` | 毛茸茸的东方龙形；永久只做 SFW |
| 小粉 | `dragonmaid ernus` | 粉色西方龙形 |
| 小黑 | `dragonmaid cehrmba` | 深色装甲龙、青色点缀、完整翼尾 |

小金 Latys 当前没有官方对应龙形态，不要硬套其他角色的龙形 LoRA。

## CG 正面词骨架

```text
masterpiece, best quality, amazing quality,
finished 2D anime visual novel event CG,
consistent clean anime style, clean lineart, crisp cel shading,
solo, 1girl,
[角色触发词], [项目身份补充词],
[动作], [眉眼和嘴部神态], [手与道具接触],
correct horns, naturally attached tail, costume fidelity
```

## 常用负面词

```text
duplicate person, clone, multiple girls, independent dragon,
card frame, trading card border, readable text, speech bubble,
wrong hair color, wrong horn color, missing horns,
detached tail, floating tail, extra tail,
bad hands, extra fingers, extra limbs, broken anatomy,
inconsistent style, photorealistic, 3d render, oversaturated
```

## 多角色使用方法

不要把两个强角色 LoRA 全局串联。正确顺序是：

```text
统一底模
→ 角色 A 区域蒙版 + A LoRA + A 参考图
→ 角色 B 区域蒙版 + B LoRA + B 参考图
→ OpenPose/Depth 约束
→ 低去噪统一光影
→ 局部修复角、尾巴、服装和手部接触
```
