"""验证模型定义和数据校验是否正常工作"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from medagent.models.schemas import PatientData, GraphState
from medagent.agents.intake import validate_required_fields


def test_sample_data():
    sample_path = Path(__file__).parent / "sample_patient.json"
    with open(sample_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    patient = PatientData(**data)
    patient.compute_derived_fields()

    print(f"✅ PatientData 解析成功")
    print(f"   姓名: {patient.patient_name}")
    print(f"   年龄: {patient.age}")
    print(f"   BMI: {patient.physical_exam.bmi}")
    print(f"   腰臀比: {patient.physical_exam.waist_hip_ratio}")
    print(f"   空腹血糖: {patient.clinical_tests.blood_sugar.fasting_glucose} mmol/L")
    print(f"   HbA1c: {patient.clinical_tests.blood_sugar.hba1c}%")

    missing = validate_required_fields(patient.model_dump())
    if missing:
        print(f"\n⚠️ 缺少必填字段 ({len(missing)}):")
        for f in missing:
            print(f"   - {f}")
    else:
        print(f"\n✅ 所有必填字段校验通过!")

    print(f"\n✅ GraphState 创建成功")
    state = GraphState(patient_data=patient, intake_valid=True)
    print(f"   intake_valid: {state.intake_valid}")
    print(f"   patient_data loaded: {state.patient_data is not None}")


def test_missing_fields():
    incomplete_data = {
        "core_symptoms": {
            "triad_symptoms": {},
            "hypoglycemia_reaction": "无",
        },
        "medical_history": {
            "prior_glucose_history": "无",
            "steroid_diuretic_use": "无",
        },
        "past_history": {
            "diagnosed_diseases": "无",
            "allergy_history": "无",
        },
        "physical_exam": {
            "height_cm": 170,
            "weight_kg": 70,
            "waist_cm": 85,
            "hip_cm": 90,
            "systolic_bp": 120,
            "diastolic_bp": 80,
            "pulse_rate": 72,
        },
        "clinical_tests": {
            "blood_sugar": {
                "fasting_glucose": 7.0,
                "hba1c": 7.5,
                "hypoglycemia_frequency": "无",
                "medication_glucose_response": "无",
            },
            "insulin": {
                "fasting_insulin": 10.0,
                "fasting_c_peptide": 1.5,
            },
            "metabolic": {},
            "urine": {"urinalysis": "正常"},
            "antibody": {"gad_antibody": "阴性"},
        },
        "medications": {
            "oral_medications": "二甲双胍",
            "insulin_therapy": "无",
            "glp1_therapy": "无",
            "other_medications": "无",
        },
        "lifestyle": {
            "diet_staple": "米饭",
            "diet_regularity": "规律",
            "exercise_leisure": "散步",
        },
        "family_history": {
            "diabetes_in_relatives": "母亲糖尿病",
            "other_family_diseases": "父亲高血压",
        },
    }

    patient = PatientData(**incomplete_data)
    missing = validate_required_fields(patient.model_dump())
    print(f"\n{'='*50}")
    print(f"不完整数据测试:")
    print(f"  缺少字段数: {len(missing)}")
    for f in missing:
        print(f"  - {f}")


if __name__ == "__main__":
    test_sample_data()
    test_missing_fields()
    print(f"\n{'='*50}")
    print("所有测试通过!")
