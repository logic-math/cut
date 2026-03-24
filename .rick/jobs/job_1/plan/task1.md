# 依赖关系


# 任务名称
搭建 cut skills 技能包骨架与环境检测

# 任务目标
创建符合 Anthropic skills 规范的技能包目录结构，包含总入口 SKILL.md、配置文件模板、各子 skill 的目录骨架，以及运行前的环境依赖检测脚本。这是所有后续任务的基础。

# 关键结果
1. 完成 `cut/` 目录结构，包含所有子 skill 的空目录和占位文件，与 SPEC.md 定义完全一致
2. 完成 `cut/SKILL.md`（总入口，符合 Anthropic SKILL.md 规范，含 name/description/trigger 等字段）
3. 完成 `cut/cut-config.yaml`（服务商配置模板，含 tts/image/video/music/handraw 各项默认值）
4. 完成 `cut/scripts/check_env.py`（检测 FFmpeg、Python 版本、cairosvg、各 skill 依赖包，缺失时输出 `brew install` 或 `pip install` 命令）
5. workspace 目录约定：每次运行自动创建 `workspace/{project}/{timestamp}/`，防止重跑覆盖历史结果

# 测试方法
1. 运行 `python cut/scripts/check_env.py`，在 FFmpeg 未安装时输出 `brew install ffmpeg` 提示，已安装时输出 `✓ FFmpeg OK`；cairosvg 未安装时输出 `pip install cairosvg` 提示
2. 检查 `cut/SKILL.md` 包含有效的 YAML frontmatter（name, description 字段）
3. 检查 `cut/cut-config.yaml` 可被 Python yaml.safe_load() 正常解析，且包含 handraw 配置节
4. 检查目录结构与 SPEC.md 中定义的结构一致（通过 `find cut -type f` 验证）
5. 验证 workspace 创建逻辑：同一项目运行两次，生成两个不同 timestamp 子目录，互不覆盖
