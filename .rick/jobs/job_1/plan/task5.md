# 依赖关系
task1

# 任务名称
实现 gen-assets skill：AI 素材生成（图片/视频/手绘图）

# 任务目标
当素材搜索结果不满意时，通过 AI 生成素材。实现图片生成、视频生成、手绘图生成三类能力，均采用依赖倒置架构（Protocol 抽象层），可通过配置切换服务商，后续可无缝扩展新 provider。

手绘图分两个子类型，路由策略：
- `handraw_chart`（数据图表/流程图）→ `handraw_chart_svg.py`：LLM 生成 SVG → cairosvg 转 PNG，纯 Python，无需 Node.js
- `handraw_illustration`（插图/示意图）→ `handraw_illus_dalle.py`：DALL-E 3 + 手绘风格 prompt，美感最优

# 关键结果
1. 完成图片生成抽象层 `providers/image_base.py`（Protocol: `generate(prompt, output_path, size) -> None`）及 `image_dalle3.py`、`image_sdiffusion.py` 两个适配器
2. 完成视频生成抽象层 `providers/video_base.py` 及 `video_runway.py` 适配器（异步轮询任务完成）
3. 完成手绘图抽象层 `providers/handraw_base.py`（Protocol: `generate(description, output_path) -> None`），及两个适配器：
   - `handraw_chart_svg.py`：Claude → SVG（rough 手绘风格）→ cairosvg → PNG
   - `handraw_illus_dalle.py`：DALL-E 3，固定 prompt 后缀 `"hand-drawn illustration, sketch style, black ink on white, rough lines"`
4. 完成 `gen_handraw.py` 入口：读取 scene 的 `visual.type`，路由到对应 handraw provider；provider 名称通过 config 配置，新增 provider 只需实现 Protocol 并注册到 config
5. 完成 `gen_image.py`、`gen_video.py` 入口脚本（读取 config，调用对应 provider，保存到 `assets/{type}/` 目录，更新 script.json 中对应 scene 的 `visual.status` 为 "ready" 和 `visual.asset_path`）
6. 完成 `skills/gen-assets/SKILL.md`（含各服务商 API Key 配置说明、费用参考、如何扩展新 provider 的说明）

# 测试方法
1. 用 DALL-E 3 生成一张 "programmer at desk, cinematic lighting" 图片，验证文件存在且为有效 PNG/JPG，script.json 中对应 scene 的 visual.status 更新为 "ready"
2. 用 Runway ML 生成一个 5 秒 "code scrolling on screen" 视频片段，验证文件存在且 ffprobe 可读取时长
3. 用 `handraw_chart` 类型生成 "程序员数量逐年下降趋势折线图"，验证输出为有效 PNG，图中包含折线和坐标轴，无需 Node.js 环境
4. 用 `handraw_illustration` 类型生成 "AI 机器人取代程序员的示意图"，验证输出为有效 PNG 且具备手绘插图风格
5. 切换 image provider 从 dalle3 到 stable_diffusion，验证接口调用成功；新增一个 mock provider 实现 handraw_base Protocol，验证无需修改 gen_handraw.py 即可运行
