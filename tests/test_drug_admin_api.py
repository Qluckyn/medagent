"""Lightweight examples for the drug admin API.

Usage:
1. Ensure MySQL drug knowledge base is configured and initialized
2. Start backend:
   python -m uvicorn medagent.main:app --host 127.0.0.1 --port 8000
3. Run this script:
   python tests/test_drug_admin_api.py
"""

import uuid

import httpx

API_BASE = "http://127.0.0.1:8000"


def build_payload() -> dict:
    suffix = uuid.uuid4().hex[:8]
    return {
        "name": f"测试药物-{suffix}",
        "category": "测试分类",
        "aliases": [f"别名-{suffix}"],
        "indications": ["2型糖尿病测试适应症"],
        "contraindications": {"egfr<30": "eGFR<30 禁用"},
        "dose_range": "1片 qd",
        "side_effects": ["轻度恶心"],
        "notes": "仅用于接口联调测试",
    }


def main():
    payload = build_payload()

    created = httpx.post(f"{API_BASE}/api/drugs", json=payload, timeout=30)
    created.raise_for_status()
    drug = created.json()
    drug_id = drug["id"]
    print("Created:", drug_id, drug["name"])

    detail = httpx.get(f"{API_BASE}/api/drugs/{drug_id}", timeout=30)
    detail.raise_for_status()
    print("Fetched:", detail.json()["name"])

    listing = httpx.get(f"{API_BASE}/api/drugs", timeout=30)
    listing.raise_for_status()
    print("List size:", len(listing.json()))

    payload["notes"] = "更新后的备注"
    updated = httpx.put(f"{API_BASE}/api/drugs/{drug_id}", json=payload, timeout=30)
    updated.raise_for_status()
    print("Updated notes:", updated.json()["notes"])

    deleted = httpx.delete(f"{API_BASE}/api/drugs/{drug_id}", timeout=30)
    deleted.raise_for_status()
    print("Deleted:", deleted.json())


if __name__ == "__main__":
    main()
