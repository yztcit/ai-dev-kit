---
id: split-plans-exec-reference
kind: technique
triggers: ["计划先分 exec 和 reference", "先判定计划类型", "reference 不该按 exec 清理"]
scope: universal
verified_at: 2026-11-19
strength: hypothesis
---

## 情境
当一条计划既可能是执行稿，也可能是资料稿时。

## 做法
- 先判断计划属于 `exec` 还是 `reference`。
- `exec` 负责推进，完成后可以收敛、替换或归档。
- `reference` 负责保留知识，不要按执行稿的节奏误删。

## 反例
如果条目只是临时想法、从未形成可执行计划，就不要硬塞进这条分法里，先补全语义再处理。

## 来源
经验总结
