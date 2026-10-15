# 拆书资源接入原创小说

## 使用时机

用户要求使用已有拆书结论，或当前简报、卷纲、章节计划、审校问题适合从已有机制学习时，读取本文件。参考资源提供创作方法，不提供本书人物事实、时间线或正史；本书已确认定位、世界硬规则、人物动机及连续性优先。

本文件只用于 `adaptation_mode: original_mechanism_transfer`。用户说“仿写”但没有说明模式时，先展示模式选项，不创建正文或正式章节清单；沿用原作姓名、角色事实或世界设定时改走同人路由。

先从本书当前需求出发，例如“让主角主动推动揭示”“增加关系选择的代价”“让章末问题有行动压力”，再用已有 `analysis_retrieval.py` 检索机制和相关笔记。检索命中只是候选，Codex 判断相关性和改造距离。没有适合的机制时直接说明，不为了使用拆书而强行加入桥段。

## 从笔记到机制

先检查 `analysis-state.yaml`、来源与覆盖地图；`source.scope` 是分析窗口，不代表已经全部读完。可增加 `source.read_scope` 表达实际已读范围；读到新的范围时同步更新覆盖地图。没有结构化已读范围时回看地图和笔记，不计算虚假的完成百分比。

保留已有文字 `pattern-cards.md`。需要接入生成时，再把紧凑、可复用结论写入同一分析工作区的 `pattern-cards.yaml`；细节和短证据仍在原 Markdown，勿重复大段来源。已有文字卡不自动变成“已校验机制”。机制可只适用于已读的一小段，不要求全书拆完。

```yaml
schema_version: 1
source:
  fingerprint: "sha256:<与 analysis-state.yaml 一致>"
  scope: "第1-50章" # 与状态记录一致的分析窗口
  coverage: sampled
cards:
  - id: PATTERN-001
    title: 让揭示成为主角的主动选择
    status: ready
    scope: "第1-3章" # 真正支持此机制的已读范围
    core_promise: 本书希望读者持续获得的核心题材或心理回报
    stimulus_object: 触发该回报的关系、对象或问题
    viewing_position: 主角或读者处于看见、听见、误认、协助、缺席或事后核验中的哪一处
    psychological_progression: 本章机制如何改变欲望、羞耻、比较、归属、恐惧或其他心理压力
    return_attachment: 事件后由什么选择、关系确认或代价暂时收束回报
    problem: 信息揭示只有旁观，没有人物行动
    mechanism: 让主角为了眼前目标主动验证线索，验证结果带来新风险
    prerequisites: [存在可行动的线索, 主角有承担风险的理由]
    payoff: 读者同时获得答案与下一步期待
    failure_modes: [验证没有代价, 揭示与主角目标无关]
    forbidden_elements: [原作专名与独特设定, 标志性桥段, 原句表达]
    evidence:
      - path: notes/segment-001.md
        sha256: "<该笔记文件字节的 SHA-256>"
        anchor: "证据与边界" # 可选，不含 #
```

每张机制卡必须说明核心阅读承诺、问题、运作机制、前提、回报、失败方式、禁止元素和证据。`stimulus_object`、`viewing_position`、`psychological_progression`、`return_attachment` 是按题材选用的维度；无对应机制时省略，不强填关系或依恋解释。选用后须有证据支持。

旧版机制卡缺少核心承诺或其他必填字段时，先补齐并重新核对证据指纹，再锁定章节参考；校验失败时不得把旧卡当作已确认机制继续装入上下文。

写卡前回读证据。登记为 `stale`、`blocked`、`missing` 或 `in_progress` 的证据不得接入；未登记的旧笔记仍可通过文件指纹核对，但应说明状态登记缺口。脚本只验证结构、来源与版本，机制是否有效、有无反例仍由 Codex 按证据判断。

```text
python scripts/analysis_reference.py inspect analyses/<名称>
```

此命令只读取，返回机制可用性及整个清单的 `registry_sha256`。清单、来源窗口或证据变化后必须重新核对，不自动覆盖用户编辑，也不把索引缓存作为证据。

## 映射到本书

简报与卷纲阶段：把机制转成这本书自己的故事发动机、卷职责、冲突升级或阅读回报，并在相应计划中记录机制 ID 与改造依据。仍遵循既有高影响开书选择和里程碑确认，不用参考书替用户决定本书定位。

章节阶段：通常选 1–3 张卡。为每张说明本章用途、满足哪些前提、怎样改变人物目标/阻力/代价/结果、哪些源作元素不采用，以及审校如何判断是否有效。避免只有“换姓名”“换职业”的表面变化。

写入本书的 `context-packages/chapter-XXX.references.yaml`：

```yaml
schema_version: 1
chapter: 1
max_chars: 2200
items:
  - analysis_workspace: "C:/writing/analyses/参考作品"
    pattern_id: PATTERN-001
    registry_sha256: "<inspect 返回的清单指纹>"
    use_for: 让本章调查动作直接推进主角目标
    adaptation: 主角为保住自己的证据资格主动核验旧档，核验导致自身权限暴露；人物、制度、风险和结果均由本书设定产生
    avoid: [原作的具体道具, 原作的揭示顺序与场景组合]
    success_check: 主角是否做出有代价的选择，发现是否改变下一步行动
```

绝对来源路径由用户明确指定或已授权工作区提供，不全盘搜索用户目录。清单可编辑；整个机制清单变化也会要求重新核对锁定指纹。选择适合的机制由 Codex 完成，脚本不从计划关键词自动选卡，不自动承认新版本。

## 装配、失效与审校

```text
python scripts/analysis_reference.py validate novels/<名称> --chapter 1
python scripts/novelctl.py context novels/<名称> --chapter 1 --output context-packages/chapter-001.md
```

`novelctl context` 自动读取对应章节的参考清单，兼容旧 Markdown 连续性与结构化连续性。参考部分默认额外最多 2200 字符，独立于已有权威上下文预算；可通过清单的 `max_chars` 显式调整。这是字符预算，不是模型 Token。超限会要求缩减选卡或压缩机制，不截掉前提、禁止元素和审校条件，也不为参考材料减少本书上下文预算。

来源、清单或证据不一致时，上下文装配以及章节计划/正文/修订/审校/修复步骤的开始与完成会拒绝采用过期参考；检查失败发生在状态写入前。已验收正文和连续性不因此自动改写。回读变动、更新机制和本书改造，再重新锁定指纹；清单撤除后该章不使用拆书参考。

审校中增加一个简短“参考机制效果”段落：机制 ID、实际采用位置、目标效果是否出现、前提是否满足、是否与本书约束冲突、是否存在过度相似或强塞痕迹。未采用的机制记明原因；不要仅凭列出来源就判定质量提升。审校结论仍走已有 `accepted/repair_required/stop_for_replan` 合同，参考结论不进入本书事实台账。

阅读台只展示资料、核验机制及准备可复制请求。用户将请求交给 Codex 后，才按本书现有流程生成清单、上下文和正文；阅读页面不调用模型或写入工作区。
