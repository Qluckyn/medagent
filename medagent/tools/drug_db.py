"""药物知识库 - 糖尿病相关药物禁忌症、相互作用、基本信息"""

import json
from langchain_core.tools import tool

DRUG_DATABASE = {
    "二甲双胍": {
        "category": "双胍类",
        "indications": ["2型糖尿病一线用药", "胰岛素抵抗", "多囊卵巢综合征(超适应症)"],
        "contraindications": {
            "egfr<30": "eGFR<30 mL/min禁用",
            "egfr_30_45": "eGFR 30-45需减量至500mg/日",
            "severe_liver": "严重肝功能不全禁用",
            "alcoholism": "酗酒禁用(乳酸酸中毒风险)",
            "heart_failure_acute": "急性或失代偿性心衰禁用",
            "hypoxia": "组织缺氧状态禁用",
            "contrast_media": "碘造影剂使用前后48h停用",
        },
        "dose_range": "500-2000mg/日，分2-3次",
        "side_effects": ["胃肠反应(腹泻、恶心)", "维生素B12缺乏(长期)", "乳酸酸中毒(罕见)"],
        "notes": "缓释片可减少胃肠反应；不引起低血糖；有轻度减重效果",
    },
    "达格列净": {
        "category": "SGLT2抑制剂",
        "indications": ["2型糖尿病", "心力衰竭", "慢性肾脏病"],
        "contraindications": {
            "egfr<20": "eGFR<20降糖效果差（但心肾保护可继续至透析）",
            "type1_dm": "1型糖尿病慎用(DKA风险)",
            "recurrent_uti": "反复泌尿生殖系统感染者慎用",
            "volume_depletion": "严重血容量不足/低血压慎用",
        },
        "dose_range": "10mg qd",
        "side_effects": ["泌尿生殖系统感染", "多尿", "低血压", "酮症酸中毒(罕见)"],
        "notes": "有心血管和肾保护证据；有减重和降压作用；老年人注意脱水",
    },
    "恩格列净": {
        "category": "SGLT2抑制剂",
        "indications": ["2型糖尿病", "心力衰竭", "慢性肾脏病"],
        "contraindications": {
            "egfr<20": "eGFR<20降糖效果差",
            "type1_dm": "1型糖尿病慎用",
            "recurrent_uti": "反复感染者慎用",
        },
        "dose_range": "10-25mg qd",
        "side_effects": ["泌尿生殖感染", "多尿", "低血压"],
        "notes": "EMPA-REG OUTCOME证实心血管获益；可与二甲双胍联用",
    },
    "利拉鲁肽": {
        "category": "GLP-1受体激动剂",
        "indications": ["2型糖尿病", "肥胖症"],
        "contraindications": {
            "mtc_family": "个人或家族甲状腺髓样癌(MTC)史禁用",
            "men2": "多发性内分泌腺瘤2型(MEN2)禁用",
            "pancreatitis": "急性胰腺炎禁用",
            "severe_gi": "严重胃肠疾病(胃轻瘫)慎用",
        },
        "dose_range": "0.6mg起始，1-2周增至1.2mg，最大1.8mg qd",
        "side_effects": ["恶心、呕吐(初期多见)", "腹泻", "胰腺炎(罕见)", "胆囊疾病"],
        "notes": "有心血管获益(LEADER研究)；显著减重；注射给药",
    },
    "司美格鲁肽": {
        "category": "GLP-1受体激动剂",
        "indications": ["2型糖尿病", "肥胖症", "心血管风险降低"],
        "contraindications": {
            "mtc_family": "个人或家族MTC史禁用",
            "men2": "MEN2禁用",
            "pancreatitis": "急性胰腺炎禁用",
        },
        "dose_range": "0.25mg起始，每4周递增，维持0.5-1mg 每周一次",
        "side_effects": ["恶心、呕吐", "腹泻", "便秘"],
        "notes": "每周一次皮下注射；也有口服剂型(14mg qd)；减重效果显著",
    },
    "西格列汀": {
        "category": "DPP-4抑制剂",
        "indications": ["2型糖尿病"],
        "contraindications": {
            "pancreatitis_history": "有胰腺炎病史者慎用",
            "egfr_30_50": "eGFR 30-50减量至50mg qd",
            "egfr<30": "eGFR<30减量至25mg qd",
        },
        "dose_range": "100mg qd（肾功能正常）",
        "side_effects": ["鼻咽炎", "头痛", "胰腺炎(罕见)"],
        "notes": "不引起低血糖；体重中性；口服方便；可与多数降糖药联用",
    },
    "格列美脲": {
        "category": "磺脲类",
        "indications": ["2型糖尿病"],
        "contraindications": {
            "type1_dm": "1型糖尿病禁用",
            "dka": "糖尿病酮症酸中毒禁用",
            "severe_liver": "严重肝功能不全禁用",
            "severe_renal": "严重肾功能不全禁用(eGFR<30)",
            "sulfa_allergy": "磺胺类过敏禁用",
            "pregnancy": "妊娠期禁用",
        },
        "dose_range": "1-4mg qd",
        "side_effects": ["低血糖", "体重增加", "皮疹"],
        "notes": "低血糖风险高，老年人慎用；需规律进餐",
    },
    "格列齐特": {
        "category": "磺脲类",
        "indications": ["2型糖尿病"],
        "contraindications": {
            "type1_dm": "1型糖尿病禁用",
            "severe_liver": "严重肝功能不全禁用",
            "severe_renal": "严重肾功能不全禁用",
            "sulfa_allergy": "磺胺类过敏禁用",
        },
        "dose_range": "缓释片30-120mg qd",
        "side_effects": ["低血糖", "体重增加"],
        "notes": "缓释片低血糖风险相对较低；ADVANCE研究用药",
    },
    "格列吡嗪": {
        "category": "磺脲类",
        "indications": ["2型糖尿病"],
        "contraindications": {
            "type1_dm": "1型糖尿病禁用",
            "dka": "糖尿病酮症酸中毒禁用",
            "severe_liver": "严重肝功能不全禁用",
            "severe_renal": "严重肾功能不全禁用",
            "sulfa_allergy": "磺胺类过敏禁用",
        },
        "dose_range": "普通片2.5-5mg起始，最大30mg/日；控释片5-10mg qd",
        "side_effects": ["低血糖", "体重增加"],
        "notes": "短效，低血糖风险存在；餐前30分钟服用；老年人慎用",
    },
    "瑞格列奈": {
        "category": "格列奈类(餐时血糖调节剂)",
        "indications": ["2型糖尿病(以餐后血糖升高为主)"],
        "contraindications": {
            "type1_dm": "1型糖尿病禁用",
            "dka": "糖尿病酮症酸中毒禁用",
            "severe_liver": "严重肝功能不全禁用",
        },
        "dose_range": "0.5-4mg 餐前，每日随餐次给药，最大16mg/日",
        "side_effects": ["低血糖(较磺脲类轻)", "体重增加"],
        "notes": "起效快、作用短；'进餐服药，不进餐不服药'；肾功能不全可用",
    },
    "阿卡波糖": {
        "category": "α-糖苷酶抑制剂",
        "indications": ["2型糖尿病(以餐后血糖升高为主)", "糖耐量异常"],
        "contraindications": {
            "ibd": "炎症性肠病、肠梗阻禁用",
            "egfr<25": "eGFR<25禁用",
            "cirrhosis": "肝硬化慎用",
        },
        "dose_range": "50mg起始 tid，逐渐增至100mg tid，随第一口主食嚼服",
        "side_effects": ["腹胀、排气增多", "腹泻", "肝酶升高(大剂量)"],
        "notes": "不引起低血糖(单用)；需随餐嚼服；低血糖时须用葡萄糖而非蔗糖纠正；适合高碳水饮食人群",
    },
    "吡格列酮": {
        "category": "噻唑烷二酮类(TZD)",
        "indications": ["2型糖尿病(胰岛素抵抗明显)"],
        "contraindications": {
            "heart_failure": "心功能不全(NYHA II级以上)禁用",
            "bladder_cancer": "活动性膀胱癌禁用",
            "severe_liver": "活动性肝病或ALT>2.5倍上限禁用",
            "edema": "严重水肿慎用",
        },
        "dose_range": "15-45mg qd",
        "side_effects": ["水肿", "体重增加", "心衰风险", "骨折风险(女性)", "膀胱癌风险争议"],
        "notes": "改善胰岛素抵抗；不引起低血糖；起效慢(数周)；心衰和水肿患者禁用",
    },
    "维格列汀": {
        "category": "DPP-4抑制剂",
        "indications": ["2型糖尿病"],
        "contraindications": {
            "severe_liver": "肝功能不全(ALT/AST>3倍上限)禁用",
            "egfr<50": "中重度肾功能不全减量至50mg qd",
        },
        "dose_range": "50mg bid（肾功能正常）",
        "side_effects": ["鼻咽炎", "头痛", "肝酶升高(需监测)"],
        "notes": "不引起低血糖；体重中性；用药前及用药中需查肝功能",
    },
    "利格列汀": {
        "category": "DPP-4抑制剂",
        "indications": ["2型糖尿病"],
        "contraindications": {
            "pancreatitis_history": "有胰腺炎病史者慎用",
        },
        "dose_range": "5mg qd",
        "side_effects": ["鼻咽炎", "胰腺炎(罕见)"],
        "notes": "主要经胆道排泄，肾功能不全无需调量(肾病患者优选的DPP-4i)；不引起低血糖",
    },
    "恩格列净二甲双胍": {
        "category": "复方制剂(SGLT2i+双胍)",
        "indications": ["2型糖尿病(需联合治疗)"],
        "contraindications": {
            "egfr<30": "eGFR<30禁用(二甲双胍成分)",
            "severe_liver": "严重肝功能不全禁用",
        },
        "dose_range": "按二甲双胍和恩格列净各自剂量组合，bid",
        "side_effects": ["胃肠反应", "泌尿生殖感染", "低血压"],
        "notes": "固定复方提高依从性；禁忌症需同时考虑两种成分",
    },
    "甘精胰岛素": {
        "category": "基础胰岛素(长效)",
        "indications": ["1型糖尿病", "2型糖尿病(口服药控制不佳)"],
        "contraindications": {
            "insulin_allergy": "对胰岛素过敏禁用",
            "hypoglycemia_active": "低血糖发作时禁用",
        },
        "dose_range": "起始0.1-0.2U/kg/日，睡前注射，每3天调量2-4U",
        "side_effects": ["低血糖", "体重增加", "注射部位反应"],
        "notes": "24小时平稳无峰；每日一次；可与口服药联用",
    },
    "门冬胰岛素": {
        "category": "餐时胰岛素(速效)",
        "indications": ["1型糖尿病", "2型糖尿病(餐后血糖控制)"],
        "contraindications": {
            "insulin_allergy": "对胰岛素过敏禁用",
        },
        "dose_range": "餐前即刻注射，剂量个体化",
        "side_effects": ["低血糖", "体重增加"],
        "notes": "起效快(10-20min)；可餐前或餐后即刻注射",
    },
    "阿托伐他汀": {
        "category": "他汀类(调脂)",
        "indications": ["高胆固醇血症", "动脉粥样硬化性心血管病预防"],
        "contraindications": {
            "active_liver": "活动性肝病或ALT持续升高>3倍正常上限禁用",
            "pregnancy": "妊娠及哺乳期禁用",
            "myopathy": "肌病禁用",
        },
        "dose_range": "10-80mg qn",
        "side_effects": ["肌痛", "肝酶升高", "消化不良"],
        "notes": "LDL-C每降低1mmol/L，ASCVD风险降低22%；需定期查肝功和CK",
    },
    "缬沙坦": {
        "category": "ARB(降压)",
        "indications": ["高血压", "糖尿病肾病", "心力衰竭"],
        "contraindications": {
            "pregnancy": "妊娠期禁用",
            "bilateral_ras": "双侧肾动脉狭窄禁用",
            "hyperkalemia": "高钾血症禁用(K>5.5mmol/L)",
            "severe_renal": "严重肾功能不全慎用",
        },
        "dose_range": "80-160mg qd",
        "side_effects": ["高钾血症", "肾功能下降(需监测)", "头晕"],
        "notes": "有肾保护作用；糖尿病合并高血压首选ACEI/ARB；不能与ACEI合用",
    },
    "别嘌醇": {
        "category": "黄嘌呤氧化酶抑制剂(降尿酸)",
        "indications": ["痛风", "高尿酸血症"],
        "contraindications": {
            "hla_b5801": "HLA-B*5801阳性者禁用(严重超敏反应)",
            "severe_renal": "eGFR<30慎用需减量",
            "acute_gout": "急性痛风发作期不宜起始",
        },
        "dose_range": "100mg起始，逐渐增至300mg qd",
        "side_effects": ["皮疹", "超敏反应(重症药疹)", "肝功异常"],
        "notes": "起始前建议查HLA-B*5801基因；从小剂量起始",
    },
    "非布司他": {
        "category": "黄嘌呤氧化酶抑制剂(降尿酸)",
        "indications": ["痛风", "高尿酸血症"],
        "contraindications": {
            "azathioprine": "与硫唑嘌呤/巯嘌呤合用禁忌",
            "cv_history": "有心血管病史者慎用(CARES研究)",
        },
        "dose_range": "20-40mg qd，最大80mg",
        "side_effects": ["肝功异常", "恶心", "关节痛"],
        "notes": "不需要查HLA-B*5801；轻中度肾功能不全不需调量",
    },
}

DRUG_INTERACTIONS = [
    {"drugs": ["二甲双胍", "碘造影剂"], "interaction": "乳酸酸中毒风险增加，造影前后48h停用二甲双胍"},
    {"drugs": ["磺脲类", "氟康唑"], "interaction": "氟康唑抑制CYP2C9，增强磺脲类降糖作用，低血糖风险增加"},
    {"drugs": ["ACEI/ARB", "保钾利尿剂"], "interaction": "高钾血症风险增加，需监测血钾"},
    {"drugs": ["他汀类", "吉非贝齐"], "interaction": "横纹肌溶解风险增加，避免合用（非诺贝特相对安全）"},
    {"drugs": ["二甲双胍", "酒精"], "interaction": "增加乳酸酸中毒风险"},
    {"drugs": ["SGLT2i", "利尿剂"], "interaction": "低血压和脱水风险增加，需调整利尿剂剂量"},
    {"drugs": ["GLP-1RA", "磺脲类"], "interaction": "低血糖风险增加，建议减少磺脲类剂量"},
    {"drugs": ["缬沙坦", "贝那普利"], "interaction": "ARB+ACEI双重RAAS阻断，禁止合用（高钾、肾功能恶化）"},
    {"drugs": ["别嘌醇", "硫唑嘌呤"], "interaction": "别嘌醇抑制硫唑嘌呤代谢，骨髓抑制风险，禁止合用"},
]



def _find_builtin_drug(drug_name: str) -> tuple[str, dict] | None:
    info = DRUG_DATABASE.get(drug_name)
    if info:
        return drug_name, info

    for key, val in DRUG_DATABASE.items():
        if drug_name in key or key in drug_name:
            return key, val
    return None


def _find_mysql_drug(drug_name: str) -> tuple[str, dict] | None:
    try:
        from medagent.storage.drug_repository import find_drug_by_name

        return find_drug_by_name(drug_name)
    except Exception:
        return None


def _find_drug(drug_name: str) -> tuple[str, dict] | None:
    return _find_mysql_drug(drug_name) or _find_builtin_drug(drug_name)


def _known_drug_names() -> list[str]:
    try:
        from medagent.storage.drug_repository import list_drug_names

        names = list_drug_names()
        if names:
            return names
    except Exception:
        pass
    return list(DRUG_DATABASE.keys())


def _mysql_interactions(drug_list: list[str]) -> list[dict] | None:
    try:
        from medagent.storage.drug_repository import find_interactions

        return find_interactions(drug_list)
    except Exception:
        return None


def _builtin_interactions(drug_list: list[str]) -> list[dict]:
    found_interactions = []
    for interaction in DRUG_INTERACTIONS:
        match_count = 0
        for drug in interaction["drugs"]:
            for patient_drug in drug_list:
                if drug in patient_drug or patient_drug in drug:
                    match_count += 1
                    break
        if match_count >= 2:
            found_interactions.append(interaction)
    return found_interactions


def _format_interactions(interactions: list[dict]) -> list[str]:
    return [
        f"⚠️ {' + '.join(interaction['drugs'])}: {interaction['interaction']}"
        for interaction in interactions
    ]


@tool
def get_drug_info(drug_name: str) -> str:
    """查询药物基本信息（适应症、剂量、注意事项）。

    Args:
        drug_name: 药物名称（如"二甲双胍"、"达格列净"）
    """
    found = _find_drug(drug_name)
    if not found:
        return f"未找到药物「{drug_name}」的信息。数据库收录: {', '.join(_known_drug_names())}"

    matched_name, info = found
    result = f"【{matched_name}】({info['category']})\n"
    result += f"适应症: {'; '.join(info['indications'])}\n"
    result += f"剂量范围: {info['dose_range']}\n"
    result += f"主要不良反应: {'; '.join(info['side_effects'])}\n"
    result += f"备注: {info['notes']}"
    return result


@tool
def check_contraindications(drug_name: str, egfr: float = 999, alt_ratio: float = 1.0,
                            has_allergy_sulfa: bool = False, is_pregnant: bool = False,
                            has_heart_failure: bool = False, has_pancreatitis: bool = False,
                            has_type1: bool = False) -> str:
    """检查药物禁忌症是否适用于该患者。

    Args:
        drug_name: 药物名称
        egfr: 患者eGFR值(mL/min/1.73m²)，默认999表示未知
        alt_ratio: ALT是正常上限的倍数，默认1.0
        has_allergy_sulfa: 是否磺胺类过敏
        is_pregnant: 是否妊娠
        has_heart_failure: 是否有心衰
        has_pancreatitis: 是否有胰腺炎史
        has_type1: 是否1型糖尿病
    """
    found = _find_drug(drug_name)
    if not found:
        return f"未找到药物「{drug_name}」"

    matched_name, info = found
    warnings = []
    contraindicated = False

    contras = info["contraindications"]
    if "egfr<30" in contras and egfr < 30:
        warnings.append(f"⛔ 禁忌: {contras['egfr<30']}")
        contraindicated = True
    if "egfr<20" in contras and egfr < 20:
        warnings.append(f"⛔ 禁忌: {contras['egfr<20']}")
        contraindicated = True
    if "egfr<25" in contras and egfr < 25:
        warnings.append(f"⛔ 禁忌: {contras['egfr<25']}")
        contraindicated = True
    if "egfr<50" in contras and egfr < 50:
        warnings.append(f"⚠️ 需减量: {contras['egfr<50']}")
    if "severe_renal" in contras and egfr < 30:
        warnings.append(f"⛔ 禁忌: {contras['severe_renal']}")
        contraindicated = True
    if "egfr_30_45" in contras and 30 <= egfr < 45:
        warnings.append(f"⚠️ 需减量: {contras['egfr_30_45']}")
    if "egfr_30_50" in contras and 30 <= egfr < 50:
        warnings.append(f"⚠️ 需减量: {contras['egfr_30_50']}")
    if "severe_liver" in contras and alt_ratio > 3:
        warnings.append(f"⛔ 禁忌: {contras['severe_liver']}")
        contraindicated = True
    if "active_liver" in contras and alt_ratio > 3:
        warnings.append(f"⛔ 禁忌: {contras['active_liver']}")
        contraindicated = True
    if "sulfa_allergy" in contras and has_allergy_sulfa:
        warnings.append(f"⛔ 禁忌: {contras['sulfa_allergy']}")
        contraindicated = True
    if "pregnancy" in contras and is_pregnant:
        warnings.append(f"⛔ 禁忌: {contras['pregnancy']}")
        contraindicated = True
    if "pancreatitis" in contras and has_pancreatitis:
        warnings.append(f"⛔ 禁忌: {contras['pancreatitis']}")
        contraindicated = True
    if "type1_dm" in contras and has_type1:
        warnings.append(f"⚠️ 慎用: {contras['type1_dm']}")
    if "heart_failure_acute" in contras and has_heart_failure:
        warnings.append(f"⛔ 禁忌: {contras['heart_failure_acute']}")
        contraindicated = True
    if "heart_failure" in contras and has_heart_failure:
        warnings.append(f"⛔ 禁忌: {contras['heart_failure']}")
        contraindicated = True

    if not warnings:
        return f"✅ {matched_name}: 未发现禁忌症，可安全使用"

    status = "⛔ 禁忌" if contraindicated else "⚠️ 需注意"
    return f"{status} {matched_name}:\n" + "\n".join(warnings)


@tool
def check_drug_interactions(drug_list: list[str]) -> str:
    """检查药物列表之间的相互作用。

    Args:
        drug_list: 患者当前使用的药物名称列表
    """
    interactions = _mysql_interactions(drug_list)
    if interactions is None:
        interactions = _builtin_interactions(drug_list)

    found_interactions = _format_interactions(interactions)
    if not found_interactions:
        return f"✅ 未发现 {', '.join(drug_list)} 之间的相互作用"

    return f"药物相互作用检查({len(found_interactions)}项):\n" + "\n".join(found_interactions)

