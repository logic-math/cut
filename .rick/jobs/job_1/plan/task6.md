# 依赖关系
task4, task5

# 任务名称
实现 review-assets skill：HTML 交互审核界面

# 任务目标
生成一个本地 HTML 页面，让用户对每个场景的候选素材进行可视化审核：预览视频/图片/音乐候选，选择采用哪个，或标记为"需要 AI 生成"。用户操作完成后，审核结果直接写回 script.json（更新 selected_candidate 和 status 字段），作为后续合成的依据。

# 关键结果
1. 完成 `skills/review-assets/scripts/generate_review.py`（读取 script.json，生成 review.html 到 workspace/{project}/{timestamp}/ 目录）
2. 完成 `skills/review-assets/scripts/review.html`（纯 HTML+JS，无需服务器，支持：视频内联预览、图片预览、音频播放、单选候选项、标记"需AI生成"、一键保存）
3. 保存时直接更新 script.json 中对应 scene 的 `visual.status`（approved 或 generating）、`visual.selected_candidate`、`audio.music.status` 字段；同时更新顶层 `pipeline_state` 为 "assets_reviewed"
4. 完成 `skills/review-assets/SKILL.md`（含使用流程说明）
5. 支持两种审核模式：脚本审核（task2 后，审核旁白/画面描述文字）和素材审核（task4/5 后，审核实际媒体文件）

# 测试方法
1. 用 10 场景的 script.json（含 candidates 数组）生成 review.html，在浏览器中打开，验证每个场景显示候选素材缩略图/预览
2. 在 HTML 页面中选择每个场景的素材，点击保存，验证 script.json 中 visual.status 更新为 "approved"，visual.selected_candidate 为选中索引
3. 验证视频候选可以内联播放（HTML5 video 标签）、音频候选可以试听
4. 标记 3 个场景为"需AI生成"，验证 script.json 中对应 visual.status 为 "generating"
5. 验证 pipeline_state 在保存后更新为 "assets_reviewed"，重新打开页面可恢复上次选择状态
