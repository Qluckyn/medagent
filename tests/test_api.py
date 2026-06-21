"""MedAgent 快速测试脚本

使用方法:
1. 确保 .env 文件已配置好 LLM API Key
2. 启动后端: python -m uvicorn medagent.main:app --host 127.0.0.1 --port 8000
3. 运行本脚本: python tests/test_api.py
"""

import json
from pathlib import Path

import httpx

API_BASE = "http://127.0.0.1:8000"


def test_health():
    resp = httpx.get(f"{API_BASE}/api/health")
    print(f"Health: {resp.json()}")
    assert resp.status_code == 200


def test_schema():
    resp = httpx.get(f"{API_BASE}/api/schema")
    schema = resp.json()
    print(f"Schema required fields: {schema.get('required', [])}")
    assert "core_symptoms" in schema.get("required", [])


def test_analyze():
    sample_path = Path(__file__).parent / "sample_patient.json"
    with open(sample_path, "r", encoding="utf-8") as f:
        patient_data = json.load(f)

    print("\n🔄 发送分析请求...")
    resp = httpx.post(
        f"{API_BASE}/api/analyze",
        json={"patient_data": patient_data},
        timeout=300,
    )
    result = resp.json()

    print(f"Success: {result['success']}")
    print(f"Report ID: {result['report_id']}")

    if result["success"] and result.get("report"):
        report = result["report"]
        print("\n📋 报告摘要:")
        diag = report.get("diagnosis", {})
        print(f"  诊断分型: {diag.get('diabetes_type', 'N/A')}")
        bs = report.get("blood_sugar_assessment", {})
        print(f"  HbA1c评估: {bs.get('hba1c_status', 'N/A')[:50]}...")
        tx = report.get("treatment_plan", {})
        print(f"  降糖方案: {tx.get('glucose_lowering_plan', 'N/A')[:50]}...")
    else:
        print(f"Error: {result.get('error')}")
        if result.get("missing_fields"):
            print(f"Missing: {result['missing_fields']}")

    return result


if __name__ == "__main__":
    test_health()
    test_schema()
    test_analyze()
    print("\n✅ 测试完成!")
