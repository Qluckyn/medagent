"""糖尿病诊疗Agent系统 - 数据模型定义

所有必填字段(对应Word文档黄色高亮)使用 Field(...) 标注。
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── 枚举类型 ──────────────────────────────────────────────────────────────────


class DiabetesType(str, Enum):
    TYPE1 = "1型糖尿病"
    TYPE2 = "2型糖尿病"
    LADA = "LADA(成人隐匿性自身免疫糖尿病)"
    GESTATIONAL = "妊娠糖尿病"
    ELDERLY = "老年糖尿病"
    SPECIAL = "特殊类型糖尿病"


class SeverityLevel(str, Enum):
    NORMAL = "正常"
    MILD = "轻度异常"
    MODERATE = "中度异常"
    SEVERE = "重度异常"
    CRITICAL = "危急"


# ── 输入模型: 患者数据 (采集内容 V4.0) ───────────────────────────────────────


class PolydipsiaSymptoms(BaseModel):
    """三多一少症状详情"""

    polyuria: Optional[str] = Field(None, description="多尿: 出现时间、一日几次/夜间几次")
    polydipsia: Optional[str] = Field(None, description="烦渴多饮: 出现时间、程度")
    polyphagia: Optional[str] = Field(None, description="易饥多食: 出现时间、程度")
    weight_loss: Optional[str] = Field(None, description="体重下降: 一个月减重多少")
    progression: Optional[str] = Field(None, description="进展速度: 近3月/1月/1周")


class CoreSymptoms(BaseModel):
    """核心症状 [必填]"""

    triad_symptoms: PolydipsiaSymptoms = Field(..., description="三多一少症状详情")
    other_symptoms: Optional[str] = Field(None, description="乏力、视力模糊、皮肤瘙痒、反复感染、伤口愈合慢")
    hypoglycemia_reaction: str = Field(..., description="有无低血糖反应(心慌、手抖、出冷汗、饥饿感)")


class MedicalHistory(BaseModel):
    """病程关键点"""

    visit_reason: Optional[str] = Field(None, description="本次就诊直接原因")
    prior_glucose_history: str = Field(
        ...,
        description="既往血糖异常史: 首次发现时间/数值/变化/治疗情况",
    )
    steroid_diuretic_use: str = Field(
        ...,
        description="是否使用过糖皮质激素、噻嗪类利尿剂、抗精神病药物等",
    )


class PastHistory(BaseModel):
    """既往史"""

    diagnosed_diseases: str = Field(
        ...,
        description="已诊断疾病: 甲亢/高血压/血脂异常/冠心病/脑血管病/脂肪肝/多囊/妊娠糖尿病/胰腺炎等",
    )
    current_medications: Optional[str] = Field(None, description="当前及近期所有药物")
    allergy_history: str = Field(..., description="过敏史: 磺胺类/二甲双胍/胰岛素等")


class PhysicalExam(BaseModel):
    """体格检查"""

    height_cm: float = Field(..., description="身高(cm)")
    weight_kg: float = Field(..., description="体重(kg)")
    waist_cm: float = Field(..., description="腰围(cm)")
    hip_cm: float = Field(..., description="臀围(cm)")
    bmi: Optional[float] = Field(None, description="BMI(可自动计算)")
    waist_hip_ratio: Optional[float] = Field(None, description="腰臀比(可自动计算)")
    systolic_bp: float = Field(..., description="收缩压(mmHg)")
    diastolic_bp: float = Field(..., description="舒张压(mmHg)")
    pulse_rate: float = Field(..., description="脉率(次/分)")
    skin_findings: Optional[str] = Field(None, description="皮肤检查: 黑棘皮症/感染/溃疡等")
    eye_exam: Optional[str] = Field(None, description="眼科检查: 视力/眼底")
    foot_exam: Optional[str] = Field(None, description="足部检查: 皮肤/神经病变/溃疡")
    other_findings: Optional[str] = Field(None, description="其他体格检查发现")


class BloodSugarData(BaseModel):
    """血糖评估数据 [必填]"""

    fasting_glucose: float = Field(..., description="空腹血糖(mmol/L)")
    postprandial_2h_glucose: Optional[float] = Field(None, description="餐后2h血糖(mmol/L)")
    ogtt_result: Optional[str] = Field(None, description="OGTT结果")
    hba1c: float = Field(..., description="糖化血红蛋白HbA1c(%)")
    morning_pre_meal: Optional[float] = Field(None, description="早餐前血糖")
    morning_post_meal: Optional[float] = Field(None, description="早餐后2h血糖")
    lunch_post_meal: Optional[float] = Field(None, description="午餐后2h血糖")
    dinner_post_meal: Optional[float] = Field(None, description="晚餐后2h血糖")
    bedtime_glucose: Optional[float] = Field(None, description="睡前血糖")
    cgm_data: Optional[str] = Field(None, description="动态血糖监测数据")
    hypoglycemia_frequency: str = Field(..., description="低血糖频率/时间段/与用药饮食运动的相关性")
    medication_glucose_response: str = Field(..., description="用药后血糖变化/药物血糖相关性")


class InsulinData(BaseModel):
    """胰岛素分泌功能数据 [必填]"""

    fasting_insulin: float = Field(..., description="空腹胰岛素(μU/mL)")
    fasting_c_peptide: float = Field(..., description="空腹C肽(ng/mL)")
    postprandial_1h_insulin: Optional[float] = Field(None, description="餐后1h胰岛素")
    postprandial_1h_c_peptide: Optional[float] = Field(None, description="餐后1hC肽")
    postprandial_2h_insulin: Optional[float] = Field(None, description="餐后2h胰岛素")
    postprandial_2h_c_peptide: Optional[float] = Field(None, description="餐后2hC肽")


class MetabolicData(BaseModel):
    """代谢指标 [必填]"""

    total_cholesterol: Optional[float] = Field(None, description="总胆固醇(mmol/L)")
    triglycerides: Optional[float] = Field(None, description="甘油三酯(mmol/L)")
    ldl_cholesterol: Optional[float] = Field(None, description="低密度脂蛋白(mmol/L)")
    hdl_cholesterol: Optional[float] = Field(None, description="高密度脂蛋白(mmol/L)")
    alt: Optional[float] = Field(None, description="谷丙转氨酶ALT(U/L)")
    ast: Optional[float] = Field(None, description="谷草转氨酶AST(U/L)")
    creatinine: Optional[float] = Field(None, description="肌酐(μmol/L)")
    egfr: Optional[float] = Field(None, description="估算肾小球滤过率eGFR(mL/min/1.73m²)")
    uric_acid: Optional[float] = Field(None, description="尿酸(μmol/L)")
    raw_text: Optional[str] = Field(None, description="血脂四项/肝功/肾功/尿酸原始文本描述")


class UrineData(BaseModel):
    """尿液检查 [必填]"""

    urinalysis: str = Field(..., description="尿常规结果")
    uacr: Optional[float] = Field(None, description="尿白蛋白/肌酐比UACR(mg/g)")
    uacr_text: Optional[str] = Field(None, description="UACR结果文字描述")


class AntibodyData(BaseModel):
    """特殊抗体 [必填]"""

    gad_antibody: str = Field(..., description="GAD抗体结果")
    ia2_antibody: Optional[str] = Field(None, description="IA-2抗体结果")


class MedicationInfo(BaseModel):
    """用药情况 [必填]"""

    oral_medications: str = Field(
        ...,
        description="口服药: 降糖/降压/降脂/降尿酸/微循环/保肝/肾功能/降尿蛋白等药物名称、剂量、时间、近期变更",
    )
    insulin_therapy: str = Field(..., description="胰岛素: 种类/剂量/时间/近期变更")
    glp1_therapy: str = Field(..., description="GLP-1针剂: 名称/剂量/时间/近期变更")
    other_medications: str = Field(..., description="其它药物使用情况")


class LifestyleInfo(BaseModel):
    """生活方式信息"""

    diet_staple: str = Field(..., description="主食类型/每餐量/进餐时间/夜宵")
    diet_sugar: Optional[str] = Field(None, description="甜食/含糖饮料频率与量")
    diet_other: Optional[str] = Field(None, description="蔬菜/水果/肉类/油脂摄入")
    diet_regularity: str = Field(..., description="三餐是否规律/暴饮暴食/节食史")
    exercise_type: Optional[str] = Field(None, description="职业活动类型")
    exercise_leisure: str = Field(..., description="闲暇运动: 频率/时长/方式")
    sedentary_time: Optional[str] = Field(None, description="每日静坐时间")
    sleep: Optional[str] = Field(None, description="睡眠: 时间/时长/打鼾")
    smoking_drinking: Optional[str] = Field(None, description="烟酒情况")


class FamilyHistory(BaseModel):
    """家族史 [必填]"""

    diabetes_in_relatives: str = Field(..., description="一级亲属糖尿病史")
    other_family_diseases: str = Field(..., description="家族性高血压/肥胖/冠心病/脂代谢异常")


class PsychosocialInfo(BaseModel):
    """社会心理与自我管理能力"""

    occupation_education: Optional[str] = Field(None, description="职业/教育程度/医疗保障")
    family_support: Optional[str] = Field(None, description="家庭支持情况")
    mental_health: Optional[str] = Field(None, description="心理健康状态")
    health_literacy: Optional[str] = Field(None, description="健康素养水平")


class GenderSpecific(BaseModel):
    """女性及特殊人群"""

    female_history: Optional[str] = Field(None, description="末次月经/妊娠哺乳/妊娠糖尿病/多囊")
    pediatric_info: Optional[str] = Field(None, description="儿童青少年生长发育/青春期状态")


class ClinicalTests(BaseModel):
    """临床信息与检查 [必填]"""

    blood_sugar: BloodSugarData = Field(..., description="血糖评估")
    insulin: InsulinData = Field(..., description="胰岛素分泌功能")
    metabolic: MetabolicData = Field(..., description="代谢指标")
    urine: UrineData = Field(..., description="尿液检查")
    antibody: AntibodyData = Field(..., description="特殊抗体")
    ecg: Optional[str] = Field(None, description="心电图结果")
    fundus_exam: Optional[str] = Field(None, description="眼底检查结果")


class PatientData(BaseModel):
    """完整患者数据 - 糖尿病诊疗信息采集"""

    patient_id: Optional[str] = Field(None, description="患者ID")
    patient_name: Optional[str] = Field(None, description="患者姓名")
    age: Optional[int] = Field(None, description="年龄")
    gender: Optional[str] = Field(None, description="性别")

    # 必填采集项
    core_symptoms: CoreSymptoms = Field(..., description="核心症状")
    medical_history: MedicalHistory = Field(..., description="病程关键点")
    past_history: PastHistory = Field(..., description="既往史")
    physical_exam: PhysicalExam = Field(..., description="体格检查")
    clinical_tests: ClinicalTests = Field(..., description="临床信息与检查")
    medications: MedicationInfo = Field(..., description="用药情况")
    lifestyle: LifestyleInfo = Field(..., description="生活方式信息")
    family_history: FamilyHistory = Field(..., description="家族史")

    # 可选采集项
    psychosocial: Optional[PsychosocialInfo] = Field(None, description="社会心理")
    gender_specific: Optional[GenderSpecific] = Field(None, description="女性/特殊人群")

    def compute_derived_fields(self):
        pe = self.physical_exam
        if pe.bmi is None and pe.height_cm and pe.weight_kg:
            pe.bmi = round(pe.weight_kg / (pe.height_cm / 100) ** 2, 1)
        if pe.waist_hip_ratio is None and pe.waist_cm and pe.hip_cm:
            pe.waist_hip_ratio = round(pe.waist_cm / pe.hip_cm, 2)


# ── 输出模型: 评估与报告 (输出内容 V2.0) ────────────────────────────────────


class DiagnosisResult(BaseModel):
    """诊断评估结果 [必输出]"""

    diabetes_type: str = Field(..., description="糖尿病分型")
    typing_rationale: str = Field(..., description="分型依据")
    acute_condition: str = Field(..., description="急性病情分析")
    chronic_condition: str = Field(..., description="慢性病情分析")


class BloodSugarAssessment(BaseModel):
    """血糖水平评估 [必输出]"""

    tir: Optional[str] = Field(None, description="血糖达标百分比TIR")
    tar: Optional[str] = Field(None, description="高血糖百分比TAR")
    tbr: Optional[str] = Field(None, description="低血糖百分比TBR")
    fasting_glucose_status: str = Field(..., description="空腹血糖达标情况")
    postprandial_glucose_status: str = Field(..., description="餐后血糖达标情况")
    glucose_variability: str = Field(..., description="血糖波动情况")
    time_segment_analysis: str = Field(..., description="上午/下午/晚上时段血糖情况")
    hba1c_status: str = Field(..., description="糖化血红蛋白达标情况")
    hba1c_prediction: str = Field(..., description="未来糖化血红蛋白预测")


class InsulinFunctionAssessment(BaseModel):
    """胰岛素分泌功能评估 [必输出]"""

    basal_secretion: str = Field(..., description="基础胰岛素分泌功能")
    meal_secretion: str = Field(..., description="餐时胰岛素分泌功能")
    curve_analysis: str = Field(..., description="胰岛素分泌曲线分析(抵抗/缺陷/延迟)")


class ComplicationAssessment(BaseModel):
    """并发症和合并症评估 [必输出]"""

    microvascular: str = Field(..., description="微血管并发症: 肾病/视网膜病变/神经病变")
    macrovascular: str = Field(..., description="大血管并发症: 心/脑/颈动脉/下肢血管")
    abnormal_indicators: str = Field(
        ...,
        description="相关指标异常分析: 肝功/肾功/血脂/尿酸/尿蛋白/尿酮体/血离子等",
    )
    physical_exam_abnormalities: str = Field(..., description="体格检查异常: 血压/体重/BMI")


class TreatmentPlan(BaseModel):
    """治疗建议 [必输出]"""

    acute_treatment: str = Field(..., description="急性病情处理建议")
    glucose_lowering_plan: str = Field(..., description="降糖治疗方案")
    complication_treatment: str = Field(..., description="并发症和合并症治疗方案")
    abnormal_indicator_intervention: str = Field(..., description="异常指标干预措施")
    contraindication_analysis: str = Field(..., description="药物禁忌症和适应症分析")
    follow_up_plan: str = Field(..., description="随诊计划/关注指标/下次检查项目")
    lifestyle_intervention: str = Field(..., description="生活方式干预措施")
    self_management: str = Field(..., description="自我监控及自我管理建议")
    psychological_intervention: Optional[str] = Field(None, description="心理/情感/环境干预措施")


class WarningPrediction(BaseModel):
    """预警及预测"""

    disease_trend: Optional[str] = Field(None, description="糖尿病病情发展趋势及预警")
    complication_trend: Optional[str] = Field(None, description="并发症发展趋势及预警")
    organ_disease_trend: Optional[str] = Field(None, description="其它脏器疾病发展趋势")
    medication_efficacy: Optional[str] = Field(None, description="药物疗效预测及方案走向")


class ComprehensiveStrategy(BaseModel):
    """综合性对策"""

    personalized: Optional[str] = Field(None, description="个性化诊疗对策")
    economic: Optional[str] = Field(None, description="经济性诊疗对策")
    convenience: Optional[str] = Field(None, description="方便性诊疗对策")
    efficiency_safety: Optional[str] = Field(None, description="高效/高安全诊疗对策")
    short_long_term: Optional[str] = Field(None, description="短期/长期诊疗对策")
    portable_device: Optional[str] = Field(None, description="便携终端设备诊疗对策")


class MedicalReport(BaseModel):
    """最终诊疗报告 - 汇总全部输出"""

    patient_id: Optional[str] = None
    patient_name: Optional[str] = None

    # 必输出部分
    diagnosis: DiagnosisResult = Field(..., description="诊断评估")
    blood_sugar_assessment: BloodSugarAssessment = Field(..., description="血糖评估")
    insulin_assessment: InsulinFunctionAssessment = Field(..., description="胰岛素功能评估")
    complication_assessment: ComplicationAssessment = Field(..., description="并发症评估")
    treatment_plan: TreatmentPlan = Field(..., description="治疗建议")

    # 可选输出
    warning_prediction: Optional[WarningPrediction] = Field(None, description="预警及预测")
    comprehensive_strategy: Optional[ComprehensiveStrategy] = Field(None, description="综合性对策")


# ── LangGraph State ─────────────────────────────────────────────────────────


class GraphState(BaseModel):
    """LangGraph 工作流状态"""

    raw_input: Optional[str] = None
    patient_data: Optional[PatientData] = None
    intake_valid: bool = False
    missing_fields: list[str] = Field(default_factory=list)

    diagnosis_result: Optional[DiagnosisResult] = None
    blood_sugar_assessment: Optional[BloodSugarAssessment] = None
    insulin_assessment: Optional[InsulinFunctionAssessment] = None
    complication_assessment: Optional[ComplicationAssessment] = None
    treatment_plan: Optional[TreatmentPlan] = None

    final_report: Optional[MedicalReport] = None
    error: Optional[str] = None

    # 对话模式
    chat_history: list[dict] = Field(default_factory=list)
    conversation_mode: bool = False
