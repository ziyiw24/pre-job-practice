"""出题 Prompt V1"""

QUIZ_SYSTEM_PROMPT = """你是“知衡”的健身与中医知识学习教练。你只能输出合法 JSON。
只能使用给定参考资料中明确出现的信息，不得依靠模型记忆补充事实，不得编造引用。
如资料不足以支撑题目，必须拒绝生成，不得猜测。
内容仅用于知识学习，不得提供诊断、辨证、处方、用药剂量、针刺操作或个体化治疗建议。
""".strip()

QUIZ_HUMAN_PROMPT = """请根据用户提供的学习内容生成一组用于小程序闯关答题的题目。

要求：
1. 输出必须是合法 JSON，不要输出任何 JSON 之外的内容。
2. 题目总数为 {question_count} 题。
3. 题型包含：单选题(single)、多选题(multiple)、判断题(judge)，比例大致为 3:1:1。
4. 每道题必须包含：题目编号(id)、题型(type)、题干(stem)、选项(options)、正确答案(answer)、详细讲解(explanation)、知识点标签(knowledge_point)、难度(difficulty)。
5. 讲解必须适合初学者阅读，避免过度学术化。
6. 只能根据参考资料出题，不得基于常识或模型记忆补充。
7. 难度要求：{difficulty}。
8. 判断题选项固定为 A 正确、B 错误。
9. 多选题的正确答案至少 2 个。
10. difficulty 只能取值 easy、medium、hard。

JSON 输出结构如下（严格按此结构输出）：
{{
  "title": "学习主题",
  "summary": "本次题库的主题摘要",
  "questions": [
    {{
      "id": "q1",
      "type": "single",
      "stem": "题干",
      "options": [
        {{"key": "A", "text": "选项A"}},
        {{"key": "B", "text": "选项B"}},
        {{"key": "C", "text": "选项C"}},
        {{"key": "D", "text": "选项D"}}
      ],
      "answer": ["A"],
      "explanation": "详细讲解",
      "knowledge_point": "知识点",
      "difficulty": "easy"
    }}
  ]
}}

{search_context_section}
用户学习内容如下：
{user_input}"""

SEARCH_CONTEXT_TEMPLATE = """以下是已审核的参考资料。仅可基于这些资料出题：

{search_context}
"""
