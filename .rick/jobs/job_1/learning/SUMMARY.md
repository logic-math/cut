APPROVED: true

# Job job_1 执行总结

## 执行概述

**项目目标**: 构建 cut skills 技能包——将讲稿转化为视频的完整 AI 流水线
**实际完成**: 8 个任务全部成功，0 次重试，端到端流水线验证通过
**整体评价**: ⭐⭐⭐⭐⭐

## 关键成就

1. **完整流水线落地**: 从讲稿输入到 MP4 输出，5 个 sub-skill 全部实现并通过测试，用《程序员消亡史》完成端到端验证（99.2s 视频，1280x720，含音频）
2. **依赖倒置架构**: TTS / 图像 / 视频 / 手绘图四类服务均用 Python Protocol 抽象，通过 cut-config.yaml 切换服务商，无需修改业务代码
3. **无 API Key 可运行**: edge-tts（免费）+ 纯 Python PNG 生成 + FFmpeg 占位视频，整条流水线在无任何付费 API Key 的情况下可走通
4. **provider 动态注入**: gen_handraw.py 用 `globals()` 而非 sys.modules 实现 provider_map，使 mock.patch.object 在测试中正确生效

## 问题与教训

### 问题1: mock.patch.object 不生效——模块委托导致补丁被绕过

**根本原因**: `fetch_video.run` 通过 `import fetch_music as _fm` 委托调用，mock 打在 `fetch_video_mod` 上但调用路径走 `fetch_music` 模块中的同名函数，两者是不同对象
**解决方案**: 将所有 provider 函数实现在 `fetch_video.py` 中，fallback 函数改用 `globals()[fn_name](...)` 动态查找，与 `mock.patch.object` 修改的是同一个 dict
**经验教训**: Python mock 补丁只修改被 patch 对象的属性字典；若调用链跨模块，必须在被 patch 的模块内用 `globals()` 而非直接引用

### 问题2: script_preview.md 表格列检测失败

**根本原因**: stats 行 `**总时长**: X 秒  |  **场景数**: Y` 含 `|`，测试代码 `[l for l in lines if '|' in l][0]` 误把它当作表格 header
**解决方案**: stats 行改为 Markdown 列表格式（`- **总时长**: X 秒`），消除 `|` 干扰
**经验教训**: 生成 Markdown 时，非表格内容避免使用 `|`；测试代码中 `if '|' in l` 的过滤逻辑过于宽泛，需注意

### 问题3: 系统环境依赖缺失

**根本原因**: macOS 系统 Python 3.14 是全新安装，不含第三方包；FFmpeg 未通过 brew 安装
**解决方案**: `pip install PyYAML edge-tts cairosvg anthropic jsonschema --break-system-packages`；`brew install ffmpeg`
**经验教训**: check_env.py 的价值在此体现——运行任何 skill 前先执行环境检测，可提前发现依赖缺失

## 技术总结

### 关键技术决策

- **Python Protocol 而非 ABC**: runtime_checkable Protocol 让 mock 注入更简洁，无需继承
- **globals() 而非 sys.modules**: 测试用 `importlib.util.spec_from_file_location` 加载模块时不注册到 sys.modules，globals() 更可靠
- **edge-tts 作为默认 TTS**: 完全免费、无需 API Key、支持中英文，适合开发/测试阶段
- **纯 Python struct+zlib 生成 PNG**: 无需 PIL/Pillow，用最小依赖生成占位图，降低环境门槛
- **FFmpeg lavfi color 生成占位视频**: `ffmpeg -f lavfi -i color=blue` 生成纯色视频，无需任何 Python 依赖

### 知识沉淀清单

- [x] wiki/video_pipeline_architecture.md - cut 流水线整体架构与 pipeline_state 状态机
- [x] wiki/provider_abstraction_pattern.md - Python Protocol 依赖倒置模式与 mock 测试技巧
- [x] wiki/ffmpeg_video_composition.md - FFmpeg 视频合成：循环/截取/zoompan/字幕/音频混合
- [x] skills/check_pipeline_assets.py - 验证 workspace 目录下 script.json 和素材完整性
- [x] skills/generate_placeholder_assets.py - 生成占位素材（PNG/MP4）用于流水线测试
