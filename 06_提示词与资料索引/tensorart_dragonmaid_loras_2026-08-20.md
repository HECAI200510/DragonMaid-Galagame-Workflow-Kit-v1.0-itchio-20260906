# Tensor.Art：Yu-Gi-Oh / Dragonmaid XL LoRA 调查（2026-08-20）

> 范围：仅记录 Tensor.Art 原始模型页、作者页或其明确标注的 Civitai 原始链接。未下载任何模型。  
> “多概念”表示一个 LoRA 文件可分别触发多个角色；不等于页面已经展示了可靠的双人同框。

## 最重要的直接证据

1. **小粉＋小蓝确实是同一个公开 LoRA 里的两个独立角色概念，不是简单叠两个 LoRA。**
   - [Nurse Dragonmaid illus/PonyXL](https://tensor.art/models/854191781594537428) 是 Tensor.Art 标注的 Original，作者 Sqquirtle0007。
   - 页面明确列出角色 1 `nurse dragonmaid`、角色 2 `laundry dragonmaid`，还分别列出龙形态 `dragonmaid ernus` 与 `dragonmaid nudyarl`。
   - 推荐权重 `0.7-1`；Illustrious 与 PonyXL 两个版本。
   - Illustrious 页面许可：可在线使用、可作训练底模、无需署名、允许分享合并及改许可；页面同时勾选生成内容/生成服务/模型或合并的商业使用。
   - **未发现该页明确展示两人同时出现在同一张图的 2girls 示例；当前可验证的示例主要是分别触发小粉或小蓝。**

2. **同一作者还有其他“一个文件含两个角色”的 Dragonmaid LoRA。**
   - [Parlor Dragonmaid Pony/illusXL](https://tensor.art/models/854189432247467611)：角色 1 小绿，角色 2 小蓝；小绿还含 `dragonmaid lorpar` 龙形态。推荐权重 `0.7-1`。页面许可允许在线使用、训练、免署名、分享合并与商业使用。
   - [Chamber Dragonmaid illus/PonyXL](https://tensor.art/models/854190007773094413)：角色 1 小黑，角色 2 Latys（小金）；小黑还含 `dragonmaid stern` 龙形态。推荐权重 `0.7-1`。该直链当前落在 Pony 版本页，但说明同时列出 illusXL 标签。
   - 这些页面证明作者的做法是**真正的多概念训练/发布**，不是把两个成品 LoRA 在推理时硬叠。

3. **多概念 LoRA 仍不保证多人同框。**
   - [Vanellope and Taffyta together](https://tensor.art/models/949409255557985103) 是非游戏王但非常直接的对照：作者明确说它为了让两个角色同图而训练，适合不能用区域提示的人；同时明确承认会牺牲一点质量和提示词服从性。
   - 因此，多概念文件最可靠的价值首先是“角色概念集中管理与单独触发”；要稳定同框，仍需专门同框训练图、明确 `2girls` 标签或区域控制。

## Dragonmaid / Yu-Gi-Oh XL 候选

| 模型 | 角色/形态 | 底模 | 触发词/推荐权重 | 下载与许可状态 | 多人证据 |
|---|---|---|---|---|---|
| [Nurse Dragonmaid illus/PonyXL](https://tensor.art/models/854191781594537428) | 小粉＋小蓝；两者龙形态 | Illustrious / PonyXL | `nurse dragonmaid`, `laundry dragonmaid`, `dragonmaid ernus`, `dragonmaid nudyarl`; 0.7–1 | Tensor Original；页面允许在线、训练、合并与商业使用 | **多概念直接证据**；未找到明确 2girls 同框示例 |
| [Parlor Dragonmaid Pony/illusXL](https://tensor.art/models/854189432247467611) | 小绿＋小蓝；小绿龙形态 | Pony / Illustrious | `parlor dragonmaid`, `laundry dragonmaid`, `dragonmaid lorpar`; 0.7–1 | Tensor Original/作者页；许可宽松 | **多概念直接证据**；示例检索到的是分别单人触发 |
| [Chamber Dragonmaid illus/PonyXL](https://tensor.art/models/854190007773094413) | 小黑＋小金；小黑龙形态 | Pony / Illustrious 标签说明 | `chamber dragonmaid`, `Dragonmaid Latys`, `dragonmaid stern`; 0.7–1 | 页面允许在线、训练、合并与商业使用 | **多概念直接证据**；未找到可靠同框示例 |
| [House Dragonmaid illus/PonyXL](https://tensor.art/models/854190961255776766) | 管家人形＋`dragonmaid sheou` 龙形 | Pony / Illustrious | `House Dragonmaid`; 0.7–1 | Tensor 页可在线使用；商业生成/服务/合并被勾选 | 单角色多形态，不是多人 |
| [Kitchen Dragonmaid PonyXL](https://tensor.art/models/835926147901430304) | 小红人形 | Pony | `kitchen dragonmaid` | Tensor 明确标注为 [Civitai 638206](https://civitai.com/models/638206/yu-gi-oh-kitchen-dragonmaid-ponyxl) 的转载；转载页限定交流学习、不可商用 | 单角色 |
| [Laundry Dragonmaid Anima v0.1](https://tensor.art/models/981359559148890618/laundry-dragonmaid-yu-gi-oh) | 小蓝人形 | Anima | `laundr1maid`; 建议附 `multicolored hair, twintails, dragon tail, wa maid, kimono, knee boots, fingerless gloves, fang` | Tensor 明确标注为 [Civitai 2501500](https://civitai.com/models/2501500/laundry-dragonmaid-yu-gi-oh?modelVersionId=2811953) 转载；不可商用 | 单角色；页面称初步版但服饰跟踪较好 |
| [Nurse Dragonmaid IllustriousXL（bsinky）](https://tensor.art/models/954622413847425291) | 小粉人形 | IllustriousXL-v01 | 页面列完整外观标签；未给权重 | Tensor Original；页面许可宽松 | 单角色；全身 paw shoes 不稳定是作者明示 |
| [Yu-Gi-Oh Yummy + 15 others](https://tensor.art/models/952002798403199604/yu-gi-oh-yummy-series-5-characters-15-charact) | 20 个游戏王概念，含小蓝 | Illustrious | 各角色独立标签；0.7+ | Tensor 明确标注 [Civitai 1996953](https://civitai.com/models/1996953/yu-gi-oh-yummy-series-5-characters-15-characters-others-illusxl) 转载；不可商用 | **20 概念直接证据**；作者也明示非人角色较难，未证明多角色同框 |
| [Lady of Faith & Doriado](https://tensor.art/models/878087664295780487) | 两名游戏王角色 | Illustrious | `yugioh_card_for_lady_of_faith` / `yugioh_card_for_doriado`; 0.7 | Tensor Original；页面许可宽松；示例底模 WAI-NSFW-illustrious-SDXL V14 | 真双概念；未找到明确同框示例 |
| [Yu-Gi-Oh card art SDXL](https://tensor.art/models/782326893077666010) | 游戏王卡图风格，不是角色身份 | SDXL 1.0 | `glowing, yugioh style, yugioh monster, duel monster` | 页面称 14,000 张 caption 图、9055 steps、2 epochs，并给 ComfyUI 自定义节点链接 | 适合卡图/怪兽风格，不适合解决人形角色身份；可能带卡框/卡图污染 |

## 页面示例参数（直接证据）

- [House Dragonmaid Pony 示例](https://tensor.art/images/832554942179857217?model_id=832554980826174998)：LoRA 0.76、Euler a、30 steps、CFG 5.5、Clip skip 2、832×1216。
- [Chamber Dragonmaid Illustrious 示例](https://tensor.art/images/854190423311166763?model_id=854190424384924607)：LoRA 0.73、Euler a、30 steps、CFG 5.5、Clip skip 2、1024×1360。该示例同时写 `1girl` 与 `1other`，展示的是人形＋龙形概念，而不是两名女仆。
- [Parlor Dragonmaid Pony 示例](https://tensor.art/images/854189433321177597?model_id=854189432247467611)：LoRA 0.8、Euler a、30 steps、CFG 7、Clip skip 2、832×1216。
- [同一个 Parlor LoRA 触发 Laundry 的示例](https://tensor.art/images/854189433321177593?model_id=854189432247467611)：页面记录 LoRA 0.84，提示词改为 `laundry dragonmaid`；这直接证明同一权重文件可切换角色，但示例仍是 `1girl, solo`。

## 结论

- 小粉 LoRA 之所以能很好地生成小蓝，核心不是两人“长得像”，而是该公开权重**本来就联合训练了两个独立触发概念**；页面甚至为两者各自列了服装和龙形态标签。
- 外观相近（马卡龙配色、同系列女仆、角翼尾巴语汇一致）可能降低联合训练难度，但也会增加串发色/串服装风险；不是主要成功原因。
- 公开页能证明“一个文件收纳多个概念”很常见，但目前查到的 Dragonmaid 页面没有可靠证明“直接输入两个触发词就稳定产出高保真双人同框”。
- 最值得复现的是：**每个角色独立 trigger + 单人训练图占主导 + 少量高质量双人同框图明确标 `2girls` 与两角色 trigger**。这与简单拼接成品 LoRA 或将七套权重硬叠不同。

## 证据等级说明

- 表中模型页、版本、触发词、权限、示例参数：页面直接证据。
- “转载不可商用”：Tensor.Art 转载页直接声明。
- “小粉＋小蓝效果好是联合训练而非长相相似”：由同一模型页同时列出两套角色/服饰/龙形态触发词推断，属于强推断；作者没有公开训练集配比。
- “适合用少量双人图增强同框”：基于多概念训练的一般工程判断；这些模型页没有公开完整训练集或 captions，不能宣称已验证其具体配方。
