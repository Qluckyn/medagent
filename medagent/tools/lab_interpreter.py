"""检验值判读器 - 按性别年龄判断化验结果是否异常"""

from langchain_core.tools import tool

LAB_REFERENCES = {
    "fasting_glucose": {
        "name": "空腹血糖",
        "unit": "mmol/L",
        "normal": (3.9, 6.1),
        "prediabetes": (6.1, 7.0),
        "diabetes": (7.0, None),
        "low": (None, 3.9),
        "interpretation": {
            "low": "低血糖，需排除胰岛素瘤、药物过量等",
            "normal": "空腹血糖正常",
            "prediabetes": "空腹血糖受损(IFG)，糖尿病前期",
            "diabetes": "达到糖尿病诊断标准(≥7.0)",
        },
    },
    "hba1c": {
        "name": "糖化血红蛋白",
        "unit": "%",
        "normal": (4.0, 5.7),
        "prediabetes": (5.7, 6.5),
        "diabetes": (6.5, None),
        "interpretation": {
            "normal": "HbA1c正常",
            "prediabetes": "糖尿病前期(5.7-6.4%)",
            "diabetes": "达到糖尿病诊断标准(≥6.5%)",
        },
    },
    "total_cholesterol": {
        "name": "总胆固醇",
        "unit": "mmol/L",
        "normal": (0, 5.2),
        "borderline": (5.2, 6.2),
        "high": (6.2, None),
        "interpretation": {
            "normal": "总胆固醇正常",
            "borderline": "边缘升高",
            "high": "高胆固醇血症",
        },
    },
    "triglycerides": {
        "name": "甘油三酯",
        "unit": "mmol/L",
        "normal": (0, 1.7),
        "borderline": (1.7, 2.3),
        "high": (2.3, 5.6),
        "very_high": (5.6, None),
        "interpretation": {
            "normal": "甘油三酯正常",
            "borderline": "边缘升高",
            "high": "高甘油三酯血症",
            "very_high": "重度高甘油三酯(>5.6有胰腺炎风险)",
        },
    },
    "ldl_cholesterol": {
        "name": "低密度脂蛋白胆固醇",
        "unit": "mmol/L",
        "normal": (0, 3.4),
        "borderline": (3.4, 4.1),
        "high": (4.1, None),
        "interpretation": {
            "normal": "LDL-C正常(一般人群标准，糖尿病患者目标更低)",
            "borderline": "边缘升高",
            "high": "明显升高，需强化他汀治疗",
        },
    },
    "hdl_cholesterol": {
        "name": "高密度脂蛋白胆固醇",
        "unit": "mmol/L",
        "male_normal": (1.04, None),
        "female_normal": (1.17, None),
        "interpretation": {
            "low": "HDL-C偏低，心血管保护因素不足",
            "normal": "HDL-C正常",
        },
    },
    "alt": {
        "name": "谷丙转氨酶",
        "unit": "U/L",
        "male_normal": (0, 40),
        "female_normal": (0, 35),
        "mild_high": (40, 120),
        "moderate_high": (120, 400),
        "severe_high": (400, None),
        "interpretation": {
            "normal": "ALT正常",
            "mild_high": "轻度升高(1-3倍)，考虑脂肪肝、药物性",
            "moderate_high": "中度升高(3-10倍)，需排除肝炎、药物肝损",
            "severe_high": "重度升高(>10倍)，急性肝损伤，需紧急处理",
        },
    },
    "ast": {
        "name": "谷草转氨酶",
        "unit": "U/L",
        "normal": (0, 40),
        "interpretation": {"normal": "AST正常", "high": "AST升高，提示肝细胞损伤，需结合ALT、病史评估"},
    },
    "creatinine": {
        "name": "肌酐",
        "unit": "μmol/L",
        "male_normal": (57, 111),
        "female_normal": (44, 97),
        "interpretation": {
            "normal": "肌酐正常",
            "high": "肌酐升高，提示肾功能下降",
            "low": "肌酐偏低，可能为肌肉量少",
        },
    },
    "uric_acid": {
        "name": "尿酸",
        "unit": "μmol/L",
        "male_normal": (150, 420),
        "female_normal": (100, 360),
        "interpretation": {
            "normal": "尿酸正常",
            "high": "高尿酸血症，有痛风和肾结石风险，需控制饮食",
        },
    },
    "uacr": {
        "name": "尿白蛋白/肌酐比",
        "unit": "mg/g",
        "normal": (0, 30),
        "microalbuminuria": (30, 300),
        "macroalbuminuria": (300, None),
        "interpretation": {
            "normal": "UACR正常，无糖尿病肾病证据",
            "microalbuminuria": "微量白蛋白尿(早期糖尿病肾病，需ACEI/ARB+SGLT2i)",
            "macroalbuminuria": "大量白蛋白尿(临床糖尿病肾病，需强化治疗+转诊肾内科)",
        },
    },
}


@tool
def interpret_lab(test_name: str, value: float, age: int = 55, gender: str = "男") -> str:
    """判读化验结果是否异常，给出临床意义。

    Args:
        test_name: 检验项目名(fasting_glucose/hba1c/total_cholesterol/triglycerides/ldl_cholesterol/hdl_cholesterol/alt/ast/creatinine/uric_acid/uacr)
        value: 检验值
        age: 年龄
        gender: 性别
    """
    ref = LAB_REFERENCES.get(test_name)
    if not ref:
        available = ", ".join(LAB_REFERENCES.keys())
        return f"未找到「{test_name}」。可查询: {available}"

    name = ref["name"]
    unit = ref["unit"]
    result = f"【{name}】{value} {unit}\n"

    # HDL-C 特殊处理（性别相关且判断方向相反）
    if test_name == "hdl_cholesterol":
        threshold = ref["male_normal"][0] if gender == "男" else ref["female_normal"][0]
        if value < threshold:
            result += f"判读: ↓ 偏低（{gender}性正常≥{threshold}）\n"
            result += f"意义: {ref['interpretation']['low']}"
        else:
            result += f"判读: 正常（{gender}性正常≥{threshold}）\n"
            result += f"意义: {ref['interpretation']['normal']}"
        return result

    # ALT、AST、肌酐、尿酸 性别相关或单侧升高判断（value > high 才算升高，正常上限值不误判）
    if test_name in ["alt", "ast", "creatinine", "uric_acid"]:
        normal_key = f"{'male' if gender == '男' else 'female'}_normal"
        normal_range = ref.get(normal_key, ref.get("normal"))
        if normal_range:
            low, high = normal_range
            if value < low:
                result += f"判读: ↓ 偏低（{gender}性正常 {low}-{high}）\n"
                result += f"意义: {ref['interpretation'].get('low', '偏低')}"
            elif value > high:
                # 对于ALT进一步分级
                if test_name == "alt":
                    if value <= 120:
                        level = "mild_high"
                    elif value <= 400:
                        level = "moderate_high"
                    else:
                        level = "severe_high"
                    result += f"判读: ↑ 升高（{gender}性正常<{high}）\n"
                    result += f"意义: {ref['interpretation'].get(level, '升高')}"
                else:
                    result += f"判读: ↑ 升高（{gender}性正常 {low}-{high}）\n"
                    result += f"意义: {ref['interpretation'].get('high', '升高')}"
            else:
                result += f"判读: ✓ 正常（{gender}性正常 {low}-{high}）\n"
                result += f"意义: {ref['interpretation']['normal']}"
            return result

    # 通用逻辑：按区间匹配
    matched = False
    for key, interp in ref["interpretation"].items():
        range_val = ref.get(key)
        if range_val and isinstance(range_val, tuple) and len(range_val) == 2:
            low, high = range_val
            low = low if low is not None else float("-inf")
            high = high if high is not None else float("inf")
            if low <= value < high:
                arrow = "↑" if key not in ["normal", "low"] else ("↓" if key == "low" else "✓")
                result += f"判读: {arrow} {interp}\n"
                matched = True
                break

    if not matched:
        # 如果最高区间是(X, None)且value >= X
        for key in reversed(list(ref["interpretation"].keys())):
            range_val = ref.get(key)
            if range_val and isinstance(range_val, tuple):
                low, high = range_val
                if high is None and value >= (low or 0):
                    result += f"判读: ↑ {ref['interpretation'][key]}\n"
                    matched = True
                    break

    if not matched:
        normal = ref.get("normal")
        if normal:
            result += f"参考范围: {normal[0]}-{normal[1]} {unit}\n"

    return result
