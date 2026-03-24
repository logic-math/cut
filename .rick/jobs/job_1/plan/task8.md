# 依赖关系
task2, task3, task4, task5, task6, task7

# 任务名称
端到端集成测试：用《程序员消亡史》验证完整流水线

# 任务目标
使用真实的《程序员消亡史：一个软工人的辩白》示例讲稿，走通从讲稿到最终视频的完整流水线，验证所有 skill 的协作正确性，发现并修复集成问题。同时完善顶层 SKILL.md 的使用文档和快速上手指南。

# 关键结果
1. 准备 500-1000 字的《程序员消亡史》示例讲稿（`examples/programmer_extinction.md`）
2. 完整运行流水线：draft-script → review（脚本）→ fetch-assets → gen-assets（至少1个 handraw_chart + 1个 handraw_illustration）→ review（素材）→ gen-tts → compose-video；验证每个阶段 pipeline_state 正确推进
3. 输出一个 1-2 分钟的完整示例视频（可包含少量 placeholder 素材，但流水线必须跑通）
4. 完善顶层 `cut/SKILL.md`（含完整使用教程、每个 skill 的调用方式、配置说明）
5. 完成 `cut/README.md` 快速上手指南（5分钟内让新用户跑通示例）

# 测试方法
1. 按 README.md 指引，在全新环境（仅有 Python 3.11 + macOS）从零运行，check_env.py 正确检测并提示缺失依赖
2. 运行完整流水线，最终生成 `workspace/programmer_extinction/output/final.mp4`
3. 用 ffprobe 验证输出视频时长 > 60s，包含音频，分辨率符合选择
4. 验证视频中至少包含：1段搜索到的视频素材、1张 AI 生成图片、1张 handraw_chart（SVG 方案）、1张 handraw_illustration（DALL-E 方案）、TTS 旁白音频
5. 将 README.md 交给未参与开发的人阅读，5分钟内能独立完成示例运行（可用性验收）
