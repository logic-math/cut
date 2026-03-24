# 依赖关系
task1

# 任务名称
实现 TTS 服务抽象层与 gen-audio-tts skill

# 任务目标
实现 TTS（文字转语音）的依赖倒置架构：定义统一的 TTS Provider Protocol，实现 edge_tts（默认，免费）、openai、elevenlabs 三个适配器，通过 cut-config.yaml 切换。gen-audio-tts skill 读取 script.json 中每个场景的旁白，批量生成 MP3 音频文件。

# 关键结果
1. 完成 `skills/gen-assets/scripts/providers/tts_base.py`（Python Protocol 定义：`synthesize(text, output_path, voice) -> None`）
2. 完成三个 TTS 适配器：`tts_edge.py`（edge-tts，免费）、`tts_openai.py`、`tts_elevenlabs.py`
3. 完成 `skills/gen-assets/scripts/gen_tts.py`（读取 config 选择 provider，遍历 script.json 所有场景生成旁白音频）
4. 音频文件保存到 `workspace/{project}/assets/narration/scene_01.mp3` 等路径，并更新 script.json 中的 `audio.narration_path` 字段
5. 完成 `skills/gen-assets/SKILL.md` 中 TTS 部分的使用说明

# 测试方法
1. 使用 edge_tts provider，对 5 个场景的旁白文字生成 MP3，验证文件存在且可播放（`ffprobe` 检查）
2. 切换 config 为 openai provider（需设置 OPENAI_API_KEY），验证同样接口调用成功
3. 验证 script.json 中 `audio.narration_path` 字段在生成后被正确填充
4. 测试缺少 API Key 时给出明确错误提示（而非 Python 堆栈）
5. 验证中文文字（普通话）和英文文字均可正常合成
