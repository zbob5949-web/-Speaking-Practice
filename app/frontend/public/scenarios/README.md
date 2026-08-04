# 场景卡片图片

6 张场景图片放在本目录,映射关系如下(文件名即实际文件名):

| 场景 id | 图片文件 |
|---|---|
| `airport-check-in`(机场值机) | `机场.webp` |
| `hotel-check-in`(酒店入住) | `酒店.webp` |
| `restaurant-order`(餐厅点餐) | `餐厅.webp` |
| `job-interview`(求职面试) | `面试卡通图.webp` |
| `doctor-visit`(看医生) | `门诊.jpg` |
| `shopping-return`(购物退货) | `购物.webp` |

说明:

- 映射定义在 `frontend/src/components/ScenarioPicker.tsx` 的 `SCENARIO_IMAGES`。
- **三种难度(beginner / intermediate / advanced)场景相同**,映射按场景 id 关联,同一场景三个难度自动复用同一张图,无需重复图片。
- 图片以 `cover` 模式裁切填充卡片媒体区(高 74px),居中显示。
- 图片缺失或加载失败时,卡片自动回退为分类渐变色,不影响布局。
- 建议尺寸:横向图、宽高比约 3:2(如 600×400),避免过度裁切。
