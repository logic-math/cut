# 依赖关系
task3, task6

# 任务名称
实现 compose-video skill：FFmpeg 视频合成

# 任务目标
读取 script.json 和 review_result.json，按时间序列将所有素材（视频片段、图片、手绘图、旁白音频、背景音乐）通过 FFmpeg 合成为最终视频。支持字幕叠加，支持用户在运行前指定输出格式（分辨率、帧率、编码格式）。

# 关键结果
1. 完成 `skills/compose-video/scripts/compose.py`（核心合成脚本，生成 FFmpeg 命令序列并执行）
2. 支持素材类型：视频片段（直接使用）、图片（Ken Burns 效果或静止）、手绘图（渐显动画）
3. 素材时长对齐策略（必须处理）：
   - 视频素材时长 < 场景时长：循环播放（`-stream_loop -1`）
   - 视频素材时长 > 场景时长：截取素材中间段（跳过开头/结尾 10%，取中间部分）
   - 图片/手绘图：固定显示 scene.duration 秒，Ken Burns 缓动
4. 支持音频混合：旁白（主轨）+ 背景音乐（副轨，volume 参数控制，默认 0.3）；支持字幕（SRT 文件 → FFmpeg subtitles 滤镜叠加）
5. 运行前询问用户输出格式（分辨率：720p/1080p/4K；格式：mp4/mov；帧率：24/30fps），输出到 `workspace/{project}/{timestamp}/output/final.mp4`，完成后 pipeline_state 更新为 "composed"

# 测试方法
1. 用 5 场景的完整 script.json（含已填充的 asset_path）运行 compose.py，验证生成 final.mp4 文件
2. 用 ffprobe 验证输出视频：时长与脚本总时长误差 < 1s，分辨率正确，包含音频轨道
3. 验证字幕正确显示：在视频第 2 场景时间点截图，确认字幕文字与 script.json 一致
4. 测试时长对齐：准备一个 3s 素材用于 8s 场景（验证循环）、一个 30s 素材用于 5s 场景（验证截取中间段），用 ffprobe 确认输出段落时长正确
5. 验证背景音乐音量控制：用 ffmpeg volumedetect 分析输出，确认旁白音量明显高于背景音乐
