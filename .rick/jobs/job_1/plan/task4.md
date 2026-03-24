# 依赖关系
task1

# 任务名称
实现 fetch-assets skill：素材搜索（视频/图片/音乐）

# 任务目标
实现从免费素材库（Pexels、Pixabay、Jamendo）自动搜索视频、图片、背景音乐的功能。读取 script.json 中每个场景的 keywords，调用对应 API 搜索候选素材，将候选结果写入 script.json 供人工审核选择。每类素材支持多个 provider 按优先级依次尝试。

# 关键结果
1. 完成 `skills/fetch-assets/scripts/fetch_video.py`（Pexels/Pixabay API，按关键词搜索，返回候选列表）
2. 完成 `skills/fetch-assets/scripts/fetch_image.py`（同上，搜索图片）
3. 完成 `skills/fetch-assets/scripts/fetch_music.py`（Jamendo API 搜索，支持 mood/genre 过滤；Pixabay 作为备选）
4. 每个场景搜索返回 3-5 个候选素材（含缩略图URL、时长、许可证信息），写入 script.json 的 `candidates` 字段
5. 完成 `skills/fetch-assets/SKILL.md`（含 API Key 配置说明）

# 测试方法
1. 用关键词 "programmer computer coding" 调用 Pexels API，验证返回至少 3 个视频候选，包含 url、duration、thumbnail 字段
2. 用关键词 "calm ambient" 调用 Jamendo API，验证返回至少 3 个音乐候选，包含 name、artist、duration、download_url 字段
3. 模拟 Pexels API 返回空结果，验证自动 fallback 到 Pixabay
4. 验证 API Key 未配置时给出明确提示（包含如何获取 API Key 的说明）
5. 对完整的 10 场景 script.json 运行全量搜索，验证每个场景的 candidates 字段被正确填充
