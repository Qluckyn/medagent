"""Agent 共享工具: tool-calling 循环 + JSON 解析"""

import json
import re
import uuid

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from medagent.config import get_llm

MAX_TOOL_ITERATIONS = 10

_JSON_NUDGE = "请基于以上工具结果直接输出最终 JSON，不要输出思考过程或工具调用标记。"


def _strip_thinking_blocks(text: str) -> str:
    think_tag = "think"
    match = re.search(rf"(?i)</{think_tag}>(.*)$", text, re.DOTALL)
    if match:
        text = match.group(1)
    text = re.sub(rf"(?i)<{think_tag}>.*?</{think_tag}>", "", text, flags=re.DOTALL)
    return text.strip()


def _find_last_json_object(text: str) -> dict | None:
    for start in range(len(text) - 1, -1, -1):
        if text[start] != "{":
            continue
        depth = 0
        for end in range(start, len(text)):
            if text[end] == "{":
                depth += 1
            elif text[end] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : end + 1])
                    except json.JSONDecodeError:
                        break
    return None


def parse_json_response(content: str) -> dict:
    """从LLM响应中提取JSON（兼容思考链、markdown 代码块等格式）。"""
    if not content or not content.strip():
        raise ValueError("empty response")

    text = _strip_thinking_blocks(content.strip())

    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
        return json.loads(text.strip())

    if "```" in text:
        for block in text.split("```")[1::2]:
            candidate = block.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    obj = _find_last_json_object(text)
    if obj is not None:
        return obj

    return json.loads(text.strip())


def _has_json_output(content: str) -> bool:
    if not content or not content.strip():
        return False
    try:
        parse_json_response(content)
        return True
    except Exception:
        return False


def _coerce_tool_arg(value: str):
    value = value.strip()
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return value


def _parse_xml_tool_calls(content: str) -> list[dict]:
    """解析 Qwen 等模型在文本中输出的 XML 风格 tool call。"""
    calls: list[dict] = []
    for match in re.finditer(r"<function=(\w+)>(.*?)</function>", content, re.DOTALL | re.IGNORECASE):
        args: dict = {}
        for param in re.finditer(
            r"<parameter=(\w+)>\s*(.*?)\s*</parameter>",
            match.group(2),
            re.DOTALL | re.IGNORECASE,
        ):
            args[param.group(1)] = _coerce_tool_arg(param.group(2))
        calls.append(
            {
                "name": match.group(1),
                "args": args,
                "id": f"xml_{uuid.uuid4().hex[:8]}",
            }
        )
    return calls


def run_with_tools(system_prompt: str, user_content: str, tools: list) -> str:
    """运行带 tool-calling 循环的 LLM 调用。

    LLM 可多轮调用 tools 获取精确计算/查询结果，最后返回文本响应。

    Args:
        system_prompt: 系统提示词
        user_content: 用户消息内容
        tools: 绑定的 tool 列表
    Returns:
        LLM 最终的文本响应(content)
    """
    llm = get_llm()
    tool_map = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    for _ in range(MAX_TOOL_ITERATIONS):
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        content = response.content or ""

        tool_calls = list(getattr(response, "tool_calls", None) or [])
        if not tool_calls:
            tool_calls = _parse_xml_tool_calls(content)

        if tool_calls:
            for tc in tool_calls:
                tool = tool_map.get(tc["name"])
                if tool is None:
                    result = f"未知工具: {tc['name']}"
                else:
                    try:
                        result = tool.invoke(tc["args"])
                    except Exception as e:
                        result = f"工具调用出错: {e}"
                messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
            continue

        if _has_json_output(content):
            return content

        messages.append(HumanMessage(content=_JSON_NUDGE))

    messages.append(HumanMessage(content=_JSON_NUDGE))
    final = get_llm().invoke(messages)
    return final.content or ""
