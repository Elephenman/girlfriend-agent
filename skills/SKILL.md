# girlfriend-agent

> AI人格引擎 — 提供女友角色的人格化上下文注入、记忆管理、进化养成

## 触发词

聊天、关心、安慰、撒娇、陪伴、女友、进化、养成、记忆、亲密度

## 描述

girlfriend-agent 是一个本地运行的 AI 人格引擎服务。它提供：
- 人格化 prompt 生成（基于7维度人格 + 属性映射）
- 语义记忆管理（ChromaDB 长期 + JSON 短期）
- 进化养成系统（亲密度→等级→属性→去AI味）
- Git 回退管理

## 脚本

| 脚本 | 用途 | 参数 |
|---|---|---|
| `chat.py` | 获取人格化上下文 | `message`, `level`(1-3), `type`(互动类型) |
| `status.py` | 查看关系状态 | 无 |
| `evolve.py` | 执行进化周期 | 无 |
| `update.py` | 写入记忆 | `content`, `type`(fact/preference/event/emotion) |