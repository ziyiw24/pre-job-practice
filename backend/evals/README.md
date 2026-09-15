# 上岗练评测

```bash
python -m evals.run_training_eval --dataset tests/fixtures/training_cases --mode baseline
python -m evals.run_training_eval --dataset tests/fixtures/training_cases --mode agent
```

当前按项目所有者要求使用确定性 mock provider：20 段材料、100 题，输出成功率、Schema 失败率、证据失败率、引用准确率、数字保真率和 P95 延迟。mock 的 token 与成本固定为 0；它无法证明真实模型的答案唯一率、场景有效率或店长可接受率。这些指标必须在配置真实 Key 并由店长填写 `HumanQuestionJudgment` 后才能作为上线证据，不得伪造。
