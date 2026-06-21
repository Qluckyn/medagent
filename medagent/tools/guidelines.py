"""指南规则引擎 - 基于临床指南的硬编码决策规则"""

from langchain_core.tools import tool


@tool
def get_glucose_target(age: int, has_severe_complications: bool = False,
                       has_hypoglycemia_risk: bool = False,
                       is_pregnant: bool = False,
                       is_newly_diagnosed: bool = False) -> str:
    """根据患者特征确定个体化血糖控制目标。

    Args:
        age: 患者年龄
        has_severe_complications: 是否有严重并发症/合并症
        has_hypoglycemia_risk: 是否有高低血糖风险
        is_pregnant: 是否妊娠
        is_newly_diagnosed: 是否新诊断
    """
    if is_pregnant:
        return ("妊娠期血糖目标:\n"
                "  空腹: <5.3 mmol/L\n"
                "  餐后1h: <7.8 mmol/L\n"
                "  餐后2h: <6.7 mmol/L\n"
                "  HbA1c: <6.0%（避免低血糖前提下）")

    if age >= 65 or has_severe_complications or has_hypoglycemia_risk:
        return ("老年/高危患者血糖目标(宽松):\n"
                "  空腹: <8.0 mmol/L\n"
                "  餐后2h: <12.0 mmol/L\n"
                "  HbA1c: <8.0%\n"
                "  注意: 避免低血糖优先于达标")

    if is_newly_diagnosed and age < 60:
        return ("年轻/新诊断患者血糖目标(严格):\n"
                "  空腹: 4.4-6.1 mmol/L\n"
                "  餐后2h: <7.8 mmol/L\n"
                "  HbA1c: <6.5%\n"
                "  TIR: >70%")

    return ("一般成人血糖目标:\n"
            "  空腹: 4.4-7.0 mmol/L\n"
            "  餐后2h: <10.0 mmol/L\n"
            "  HbA1c: <7.0%\n"
            "  TIR: >70%，TBR: <4%，TAR: <25%")


@tool
def get_bp_target(has_diabetes: bool = True, has_ckd: bool = False,
                  has_proteinuria: bool = False, age: int = 55) -> str:
    """根据患者条件确定血压控制目标。

    Args:
        has_diabetes: 是否有糖尿病
        has_ckd: 是否有慢性肾病
        has_proteinuria: 是否有蛋白尿
        age: 年龄
    """
    if age >= 80:
        return ("≥80岁高龄患者血压目标:\n"
                "  <150/90 mmHg\n"
                "  首选药物: CCB或小剂量利尿剂")

    if has_diabetes and has_ckd and has_proteinuria:
        return ("糖尿病+CKD+蛋白尿患者血压目标:\n"
                "  <130/80 mmHg（可耐受则<125/75）\n"
                "  首选: ACEI/ARB（肾保护+降尿蛋白）\n"
                "  联合: CCB/利尿剂")

    if has_diabetes:
        return ("糖尿病患者血压目标:\n"
                "  <130/80 mmHg\n"
                "  首选: ACEI/ARB（推荐，有靶器官保护）\n"
                "  联合: CCB(氨氯地平) 或 噻嗪类利尿剂\n"
                "  注意: β受体阻滞剂可能掩盖低血糖症状")

    return "一般成人血压目标: <140/90 mmHg"


@tool
def get_lipid_target(has_ascvd: bool = False, has_diabetes: bool = True,
                     age: int = 55, has_ckd: bool = False,
                     cv_risk_factors: int = 0) -> str:
    """根据心血管风险确定血脂控制目标。

    Args:
        has_ascvd: 是否已确诊动脉粥样硬化性心血管病
        has_diabetes: 是否有糖尿病
        age: 年龄
        has_ckd: 是否有CKD
        cv_risk_factors: 其他心血管危险因素数量(高血压/吸烟/肥胖/家族史等)
    """
    if has_ascvd:
        return ("极高危(已确诊ASCVD)血脂目标:\n"
                "  LDL-C: <1.4 mmol/L 且较基线降幅≥50%\n"
                "  非HDL-C: <2.2 mmol/L\n"
                "  首选: 高强度他汀(阿托伐他汀40-80mg或瑞舒伐他汀20mg)\n"
                "  不达标加用: 依折麦布10mg 或 PCSK9抑制剂")

    if has_diabetes and (cv_risk_factors >= 2 or has_ckd or age >= 60):
        return ("高危(糖尿病+多重危险因素)血脂目标:\n"
                "  LDL-C: <1.8 mmol/L\n"
                "  非HDL-C: <2.6 mmol/L\n"
                "  TG: <1.7 mmol/L\n"
                "  首选: 中等强度他汀(阿托伐他汀10-20mg)\n"
                "  TG>2.3: 加强生活方式，>5.6: 贝特类")

    if has_diabetes:
        return ("中危(糖尿病无其他高危因素)血脂目标:\n"
                "  LDL-C: <2.6 mmol/L\n"
                "  TG: <1.7 mmol/L\n"
                "  首选: 中等强度他汀")

    return "一般人群: LDL-C <3.4 mmol/L"


@tool
def classify_ckd_stage(egfr: float, uacr: float = 0) -> str:
    """根据eGFR和UACR进行CKD分期和风险分层。

    Args:
        egfr: eGFR值(mL/min/1.73m²)
        uacr: 尿白蛋白/肌酐比(mg/g)，默认0表示未检
    """
    # eGFR分期
    if egfr >= 90:
        g_stage = "G1(正常或偏高, ≥90)"
    elif egfr >= 60:
        g_stage = "G2(轻度下降, 60-89)"
    elif egfr >= 45:
        g_stage = "G3a(轻中度下降, 45-59)"
    elif egfr >= 30:
        g_stage = "G3b(中重度下降, 30-44)"
    elif egfr >= 15:
        g_stage = "G4(重度下降, 15-29)"
    else:
        g_stage = "G5(肾衰竭, <15)"

    # UACR分期
    if uacr < 30:
        a_stage = "A1(正常, <30)"
        albuminuria = "正常"
    elif uacr < 300:
        a_stage = "A2(微量白蛋白尿, 30-300)"
        albuminuria = "微量白蛋白尿(早期DKD)"
    else:
        a_stage = "A3(大量白蛋白尿, >300)"
        albuminuria = "大量白蛋白尿(临床DKD)"

    # 风险分层
    risk_matrix = {
        ("G1", "A1"): "低风险", ("G1", "A2"): "中风险", ("G1", "A3"): "高风险",
        ("G2", "A1"): "低风险", ("G2", "A2"): "中风险", ("G2", "A3"): "高风险",
        ("G3a", "A1"): "中风险", ("G3a", "A2"): "高风险", ("G3a", "A3"): "极高风险",
        ("G3b", "A1"): "高风险", ("G3b", "A2"): "极高风险", ("G3b", "A3"): "极高风险",
        ("G4", "A1"): "极高风险", ("G4", "A2"): "极高风险", ("G4", "A3"): "极高风险",
        ("G5", "A1"): "极高风险", ("G5", "A2"): "极高风险", ("G5", "A3"): "极高风险",
    }

    g_key = g_stage.split("(")[0]
    a_key = a_stage.split("(")[0]
    risk = risk_matrix.get((g_key, a_key), "未知")

    result = (f"CKD分期:\n"
              f"  eGFR: {egfr} → {g_stage}\n"
              f"  UACR: {uacr} mg/g → {a_stage}\n"
              f"  白蛋白尿状态: {albuminuria}\n"
              f"  综合风险: {risk}\n")

    if risk in ["高风险", "极高风险"]:
        result += "  建议: 转诊肾内科，强化RAAS阻断，考虑SGLT2i肾保护"
    elif risk == "中风险":
        result += "  建议: 每3-6个月复查eGFR和UACR，优化血糖血压控制"
    else:
        result += "  建议: 每年复查"

    return result


@tool
def classify_dr_stage(has_microaneurysm: bool = False, has_hemorrhage: bool = False,
                      has_hard_exudate: bool = False, has_neovascularization: bool = False,
                      has_macular_edema: bool = False, is_normal: bool = True) -> str:
    """根据眼底检查结果对糖尿病视网膜病变分级。

    Args:
        has_microaneurysm: 有无微血管瘤
        has_hemorrhage: 有无出血
        has_hard_exudate: 有无硬性渗出
        has_neovascularization: 有无新生血管
        has_macular_edema: 有无黄斑水肿
        is_normal: 眼底是否正常
    """
    if is_normal and not any([has_microaneurysm, has_hemorrhage, has_hard_exudate,
                              has_neovascularization, has_macular_edema]):
        return ("视网膜病变分级: 无DR\n"
                "建议: 每年复查眼底")

    if has_neovascularization:
        stage = "增殖性糖尿病视网膜病变(PDR)"
        action = "⚠️ 紧急转诊眼科，考虑激光光凝或抗VEGF治疗"
    elif has_hemorrhage and has_hard_exudate:
        stage = "中-重度非增殖性DR(NPDR)"
        action = "转诊眼科，每3-6个月复查"
    elif has_microaneurysm:
        stage = "轻度非增殖性DR(NPDR)"
        action = "每6-12个月复查眼底"
    else:
        stage = "疑似早期DR"
        action = "建议散瞳眼底照相确认"

    result = f"视网膜病变分级: {stage}\n"
    if has_macular_edema:
        result += "合并: 糖尿病黄斑水肿(DME)\n"
        action = "⚠️ 紧急转诊眼科，抗VEGF治疗"
    result += f"处置建议: {action}"

    return result
