"""MedAgent 演示脚本

展示: 患者数据输入 → 7个Agent协同 + 工具调用 → 完整诊疗报告

运行: python demo.py
"""

import json
import time
from pathlib import Path

# 全局工具调用计数（演示用）
TOOL_LOG = []


def patch_tool_tracing():
    """给 run_with_tools 打补丁，实时打印工具调用。"""
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
    from medagent.agents import _base
    from medagent.config import get_llm

    def traced(system_prompt, user_content, tools):
        llm = get_llm()
        tool_map = {t.name: t for t in tools}
        llm_with_tools = llm.bind_tools(tools)
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]
        for _ in range(_base.MAX_TOOL_ITERATIONS):
            response = llm_with_tools.invoke(messages)
            messages.append(response)
            content = response.content or ""

            tcs = list(getattr(response, "tool_calls", None) or [])
            if not tcs:
                tcs = _base._parse_xml_tool_calls(content)

            if tcs:
                for tc in tcs:
                    args_str = json.dumps(tc["args"], ensure_ascii=False)
                    if len(args_str) > 60:
                        args_str = args_str[:60] + "...}"
                    print(f"      🔧 {tc['name']}({args_str})")
                    TOOL_LOG.append(tc["name"])
                    tool = tool_map.get(tc["name"])
                    try:
                        result = tool.invoke(tc["args"]) if tool else "未知工具"
                    except Exception as e:
                        result = f"出错: {e}"
                    messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
                continue

            if _base._has_json_output(content):
                return content

            messages.append(HumanMessage(content=_base._JSON_NUDGE))

        messages.append(HumanMessage(content=_base._JSON_NUDGE))
        return get_llm().invoke(messages).content or ""

    _base.run_with_tools = traced

    # reload agents to bind patched function
    import importlib
    import medagent.agents.blood_sugar
    import medagent.agents.complication
    import medagent.agents.diagnosis
    import medagent.agents.insulin_function
    import medagent.agents.treatment
    for m in [
        medagent.agents.diagnosis,
        medagent.agents.blood_sugar,
        medagent.agents.insulin_function,
        medagent.agents.complication,
        medagent.agents.treatment,
    ]:
        importlib.reload(m)


def hr(char="─", width=70):
    print(char * width)


def section(title):
    print()
    hr("═")
    print(f"  {title}")
    hr("═")


def main():
    section("MedAgent 糖尿病诊疗智能Agent系统 - 演示")

    # 1. 加载患者数据
    sample_path = Path(__file__).parent / "tests" / "sample_patient.json"
    with open(sample_path, encoding="utf-8") as f:
        patient_data = json.load(f)

    print(f"\n📋 患者: {patient_data['patient_name']}, {patient_data['age']}岁 {patient_data['gender']}")
    print(f"   主诉: 多饮多尿3月，发现血糖升高2年")
    print(f"   关键指标:")
    bs = patient_data["clinical_tests"]["blood_sugar"]
    ins = patient_data["clinical_tests"]["insulin"]
    pe = patient_data["physical_exam"]
    print(f"     空腹血糖 {bs['fasting_glucose']} mmol/L | HbA1c {bs['hba1c']}%")
    print(f"     空腹胰岛素 {ins['fasting_insulin']} μU/mL | 空腹C肽 {ins['fasting_c_peptide']} ng/mL")
    print(f"     血压 {pe['systolic_bp']}/{pe['diastolic_bp']} mmHg | 身高{pe['height_cm']} 体重{pe['weight_kg']}")
    print(f"     现用药: 二甲双胍 + 氨氯地平 + 阿托伐他汀")

    # 2. 启用工具追踪
    patch_tool_tracing()

    # 3. 运行分析
    section("多Agent协同分析 (实时工具调用)")
    print()
    print("  [Pipeline] intake → 并行(诊断/血糖/胰岛素) → 并发症 → 治疗 → 报告\n")

    from medagent.graph.workflow import run_analysis

    start = time.time()
    result = run_analysis(patient_data_dict=patient_data)
    elapsed = time.time() - start

    # 4. 输出报告
    section("诊疗报告")

    diag = result.get("diagnosis_result") or {}
    bs_a = result.get("blood_sugar_assessment") or {}
    ins_a = result.get("insulin_assessment") or {}
    comp = result.get("complication_assessment") or {}
    tx = result.get("treatment_plan") or {}

    print("\n【一、临床数据评估】\n")
    print(f"◆ 诊断分型: {diag.get('diabetes_type', 'N/A')}")
    print(f"  依据: {diag.get('typing_rationale', '')[:120]}...")

    print(f"\n◆ 血糖评估:")
    print(f"  TIR: {(bs_a.get('tir') or 'N/A')[:60]}")
    print(f"  HbA1c: {(bs_a.get('hba1c_status') or 'N/A')[:80]}")

    print(f"\n◆ 胰岛素功能:")
    print(f"  曲线分析: {ins_a.get('curve_analysis', '')[:100]}")

    print(f"\n◆ 并发症评估:")
    print(f"  微血管: {comp.get('microvascular', '')[:80]}")
    print(f"  指标异常: {comp.get('abnormal_indicators', '')[:80]}")

    print("\n【二、治疗建议】\n")
    print(f"◆ 降糖方案: {tx.get('glucose_lowering_plan', '')[:150]}...")
    print(f"\n◆ 禁忌症分析: {tx.get('contraindication_analysis', '')[:120]}...")
    print(f"\n◆ 生活方式: {tx.get('lifestyle_intervention', '')[:100]}...")

    # 5. 统计
    section("本次运行统计")
    print(f"\n  ⏱️  总耗时: {elapsed:.1f}s")
    print(f"  🔧 工具调用: {len(TOOL_LOG)} 次")
    from collections import Counter
    for name, cnt in Counter(TOOL_LOG).most_common():
        print(f"       {name}: {cnt}")

    # 必输出完整性
    required = {
        "诊断分型": diag.get("diabetes_type"),
        "血糖评估": bs_a.get("hba1c_status"),
        "胰岛素功能": ins_a.get("curve_analysis"),
        "并发症": comp.get("microvascular"),
        "治疗方案": tx.get("glucose_lowering_plan"),
        "最终报告": result.get("final_report"),
    }
    passed = sum(1 for v in required.values() if v)
    print(f"\n  ✅ 必输出完整性: {passed}/{len(required)}")

    # 保存完整报告
    out_path = Path(__file__).parent / "tests" / "demo_output.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result.get("final_report"), f, ensure_ascii=False, indent=2)
    print(f"  📄 完整报告已保存: {out_path}")
    print()


if __name__ == "__main__":
    main()
