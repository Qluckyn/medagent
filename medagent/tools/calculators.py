"""临床计算器 - 确定性计算工具"""

import math
from langchain_core.tools import tool


@tool
def calc_bmi(height_cm: float, weight_kg: float) -> str:
    """计算BMI(体质指数)并给出分类。

    Args:
        height_cm: 身高，单位厘米
        weight_kg: 体重，单位千克
    """
    height_m = height_cm / 100
    bmi = round(weight_kg / (height_m ** 2), 1)

    if bmi < 18.5:
        category = "偏瘦"
    elif bmi < 24:
        category = "正常"
    elif bmi < 28:
        category = "超重"
    else:
        category = "肥胖"

    return f"BMI = {bmi} kg/m²，分类: {category}（中国标准: <18.5偏瘦, 18.5-23.9正常, 24-27.9超重, ≥28肥胖）"


@tool
def calc_waist_hip_ratio(waist_cm: float, hip_cm: float, gender: str = "男") -> str:
    """计算腰臀比(WHR)并判断是否中心性肥胖。

    Args:
        waist_cm: 腰围，单位厘米
        hip_cm: 臀围，单位厘米
        gender: 性别，"男"或"女"
    """
    whr = round(waist_cm / hip_cm, 2)

    if gender == "男":
        central_obesity_waist = waist_cm >= 90
        central_obesity_whr = whr > 0.9
    else:
        central_obesity_waist = waist_cm >= 85
        central_obesity_whr = whr > 0.85

    result = f"腰臀比(WHR) = {whr}，腰围 = {waist_cm}cm\n"
    if central_obesity_waist or central_obesity_whr:
        result += f"判定: 中心性肥胖（{gender}性标准: 腰围≥{'90' if gender == '男' else '85'}cm 或 WHR>{'0.9' if gender == '男' else '0.85'}）"
    else:
        result += "判定: 未达到中心性肥胖标准"

    return result


@tool
def calc_homa_ir(fasting_glucose_mmol: float, fasting_insulin_uu: float) -> str:
    """计算HOMA-IR(胰岛素抵抗指数)。

    Args:
        fasting_glucose_mmol: 空腹血糖，单位mmol/L
        fasting_insulin_uu: 空腹胰岛素，单位μU/mL
    """
    homa_ir = round(fasting_glucose_mmol * fasting_insulin_uu / 22.5, 2)

    if homa_ir <= 1.0:
        interpretation = "胰岛素敏感性良好"
    elif homa_ir <= 2.5:
        interpretation = "正常范围"
    elif homa_ir <= 4.0:
        interpretation = "轻度胰岛素抵抗"
    elif homa_ir <= 6.0:
        interpretation = "中度胰岛素抵抗"
    else:
        interpretation = "重度胰岛素抵抗"

    return f"HOMA-IR = {fasting_glucose_mmol} × {fasting_insulin_uu} / 22.5 = {homa_ir}\n判读: {interpretation}（正常<2.5，≥2.5提示胰岛素抵抗）"


@tool
def calc_homa_beta(fasting_glucose_mmol: float, fasting_insulin_uu: float) -> str:
    """计算HOMA-β(β细胞功能指数)。

    Args:
        fasting_glucose_mmol: 空腹血糖，单位mmol/L
        fasting_insulin_uu: 空腹胰岛素，单位μU/mL
    """
    denominator = fasting_glucose_mmol - 3.5
    if denominator <= 0:
        return "HOMA-β 无法计算: 空腹血糖≤3.5mmol/L，公式不适用"

    homa_beta = round(20 * fasting_insulin_uu / denominator, 1)

    if homa_beta >= 100:
        interpretation = "β细胞功能正常"
    elif homa_beta >= 60:
        interpretation = "β细胞功能轻度减退"
    elif homa_beta >= 30:
        interpretation = "β细胞功能中度减退"
    else:
        interpretation = "β细胞功能重度减退"

    return f"HOMA-β = 20 × {fasting_insulin_uu} / ({fasting_glucose_mmol} - 3.5) = {homa_beta}\n判读: {interpretation}（正常≥100）"


@tool
def calc_egfr(creatinine_umol: float, age: int, gender: str = "男") -> str:
    """使用CKD-EPI公式计算eGFR(估算肾小球滤过率)。

    Args:
        creatinine_umol: 血肌酐，单位μmol/L
        age: 年龄
        gender: 性别，"男"或"女"
    """
    # Convert μmol/L to mg/dL
    scr = creatinine_umol / 88.4

    if gender == "女":
        if scr <= 0.7:
            egfr = 144 * (scr / 0.7) ** (-0.329) * (0.993 ** age)
        else:
            egfr = 144 * (scr / 0.7) ** (-1.209) * (0.993 ** age)
    else:
        if scr <= 0.9:
            egfr = 141 * (scr / 0.9) ** (-0.411) * (0.993 ** age)
        else:
            egfr = 141 * (scr / 0.9) ** (-1.209) * (0.993 ** age)

    egfr = round(egfr, 1)

    if egfr >= 90:
        stage = "G1(正常或偏高)"
    elif egfr >= 60:
        stage = "G2(轻度下降)"
    elif egfr >= 45:
        stage = "G3a(轻中度下降)"
    elif egfr >= 30:
        stage = "G3b(中重度下降)"
    elif egfr >= 15:
        stage = "G4(重度下降)"
    else:
        stage = "G5(肾衰竭)"

    return f"eGFR = {egfr} mL/min/1.73m²（CKD-EPI公式）\nCKD分期: {stage}"


@tool
def calc_tir(glucose_readings: list[float]) -> str:
    """根据血糖读数列表计算TIR/TAR/TBR。

    Args:
        glucose_readings: 血糖读数列表，单位mmol/L（可以是SMBG点值或CGM数据）
    """
    if not glucose_readings:
        return "无血糖数据，无法计算"

    total = len(glucose_readings)
    in_range = sum(1 for g in glucose_readings if 3.9 <= g <= 10.0)
    above = sum(1 for g in glucose_readings if g > 10.0)
    below = sum(1 for g in glucose_readings if g < 3.9)
    very_high = sum(1 for g in glucose_readings if g > 13.9)
    very_low = sum(1 for g in glucose_readings if g < 3.0)

    tir = round(in_range / total * 100, 1)
    tar = round(above / total * 100, 1)
    tbr = round(below / total * 100, 1)

    result = f"基于 {total} 个血糖读数:\n"
    result += f"  TIR(3.9-10.0): {tir}%（目标>70%）{'✓达标' if tir > 70 else '✗未达标'}\n"
    result += f"  TAR(>10.0):    {tar}%（目标<25%）{'✓达标' if tar < 25 else '✗未达标'}\n"
    result += f"  TBR(<3.9):     {tbr}%（目标<4%）{'✓达标' if tbr < 4 else '✗未达标'}\n"
    if very_high > 0:
        result += f"  极高血糖(>13.9): {round(very_high/total*100,1)}%（目标<5%）\n"
    if very_low > 0:
        result += f"  极低血糖(<3.0): {round(very_low/total*100,1)}%（目标<1%）\n"
    result += f"  平均血糖: {round(sum(glucose_readings)/total, 1)} mmol/L"

    return result
