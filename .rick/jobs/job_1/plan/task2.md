# 依赖关系
task1

# 任务名称
实现 draft-script skill：讲稿转视听脚本

# 任务目标
实现核心转化 skill：将用户的文字讲稿（Markdown/TXT）转化为结构化视听脚本（JSON格式）。Claude 分析讲稿内容，自动切分场景，为每个场景生成旁白、画面描述、字幕、音乐氛围描述，输出符合 SPEC 中定义的 script.json 格式。

# 关键结果
1. 完成 `skills/draft-script/SKILL.md`（含触发词、使用说明、参数说明）
2. 完成 `skills/draft-script/scripts/draft_script.py`（调用 Claude API 完成讲稿分析和脚本生成）
3. 完成 `skills/draft-script/references/script_schema.json`（JSON Schema 定义，与 SPEC.md 中结构完全一致，含 pipeline_state、status、candidates 等字段）
4. 脚本输出到 `workspace/{project}/{timestamp}/script.json`（pipeline_state 初始为 "draft"），并同时生成人类可读的 `script_preview.md`（表格形式展示每个场景）
5. 生成的 visual.keywords **必须为英文**（Claude 在生成时自动翻译），以保证 Pexels/Pixabay 搜索质量；visual.type 从 `video|image|handraw_chart|handraw_illustration` 中选择
6. 支持命令行参数：`--input 讲稿路径 --project 项目名 --lang zh`

# 测试方法
1. 使用《程序员消亡史》500字示例讲稿作为输入，运行 `python draft_script.py --input sample.md --project test`
2. 验证输出的 `script.json` 通过 JSON Schema 验证（`jsonschema` 库），pipeline_state 为 "draft"
3. 验证所有 scene 的 visual.keywords 均为英文单词（无中文字符）
4. 验证 `script_preview.md` 可正常渲染为 Markdown 表格（包含场景编号、时长、旁白摘要、画面描述、visual.type 列）
5. 测试边界：输入超过 3000 字的讲稿，验证场景数量合理（10-30个场景），总时长估算合理
