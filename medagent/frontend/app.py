"""MedAgent - Streamlit 前端"""

import json
import re

import httpx
import streamlit as st

API_BASE = "http://localhost:8000"


def _extract_pct(text: str | None) -> str | None:
    """从评估文本中提取百分比数值，供 metric 组件显示。"""
    if not text:
        return None
    match = re.search(r"([\d.]+)\s*%", text)
    return f"{match.group(1)}%" if match else None

st.set_page_config(page_title="MedAgent 糖尿病诊疗系统", page_icon="🏥", layout="wide")
st.title("🏥 MedAgent 糖尿病诊疗智能Agent系统")

tab1, tab2, tab3 = st.tabs(["📋 结构化录入", "💬 对话采集", "📊 报告查看"])

# ── Tab 1: 结构化JSON输入 ──────────────────────────────────────────────────

with tab1:
    st.header("结构化数据录入")
    st.markdown("请填写患者诊疗信息（**加粗项**为必填）")

    with st.form("patient_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("基本信息")
            patient_name = st.text_input("姓名")
            age = st.number_input("年龄", min_value=0, max_value=120, value=55)
            gender = st.selectbox("性别", ["男", "女"])

            st.subheader("**核心症状** ⚠️")
            polyuria = st.text_area("多尿症状（时间/频率/程度）", placeholder="如: 近3个月出现，日间8-10次，夜间3-4次")
            polydipsia = st.text_area("烦渴多饮", placeholder="如: 近2个月明显口渴，每日饮水>3L")
            polyphagia = st.text_area("易饥多食", placeholder="如: 食量增加约30%")
            weight_loss = st.text_area("体重下降", placeholder="如: 近1个月减轻3kg")
            hypoglycemia = st.text_area("**低血糖反应**", placeholder="有无心慌、手抖、出冷汗、饥饿感")

            st.subheader("**病史** ⚠️")
            glucose_history = st.text_area("**既往血糖异常史**", placeholder="首次发现时间/数值/治疗情况")
            steroid_use = st.text_area("**特殊药物使用史**", placeholder="糖皮质激素/噻嗪类利尿剂/抗精神病药")
            diagnosed_diseases = st.text_area("**已诊断疾病**", placeholder="甲亢/高血压/血脂异常/冠心病等")
            allergy = st.text_area("**过敏史**", placeholder="磺胺类/二甲双胍/胰岛素等")

        with col2:
            st.subheader("**体格检查** ⚠️")
            height = st.number_input("身高(cm)", min_value=50.0, max_value=250.0, value=170.0)
            weight = st.number_input("体重(kg)", min_value=20.0, max_value=300.0, value=75.0)
            waist = st.number_input("腰围(cm)", min_value=30.0, max_value=200.0, value=90.0)
            hip = st.number_input("臀围(cm)", min_value=30.0, max_value=200.0, value=95.0)
            sbp = st.number_input("收缩压(mmHg)", min_value=60.0, max_value=300.0, value=140.0)
            dbp = st.number_input("舒张压(mmHg)", min_value=30.0, max_value=200.0, value=85.0)
            pulse = st.number_input("脉率(次/分)", min_value=30.0, max_value=200.0, value=78.0)

            st.subheader("**血糖数据** ⚠️")
            fasting_glucose = st.number_input("空腹血糖(mmol/L)", min_value=0.0, max_value=50.0, value=8.5)
            hba1c = st.number_input("HbA1c(%)", min_value=0.0, max_value=20.0, value=8.2)
            postprandial = st.number_input("餐后2h血糖(mmol/L)", min_value=0.0, max_value=50.0, value=12.3)
            hypo_freq = st.text_area("**低血糖发生情况**", placeholder="频率/时段/与用药饮食运动关系")
            med_response = st.text_area("**用药后血糖变化**", placeholder="药物与血糖的相关性")

            st.subheader("**胰岛素数据** ⚠️")
            fasting_insulin = st.number_input("空腹胰岛素(μU/mL)", min_value=0.0, value=12.0)
            fasting_cpeptide = st.number_input("空腹C肽(ng/mL)", min_value=0.0, value=1.8)

        st.subheader("**用药情况** ⚠️")
        col3, col4 = st.columns(2)
        with col3:
            oral_meds = st.text_area("**口服药**", placeholder="药物名称/剂量/用药时间/近期变更")
            insulin_therapy = st.text_area("**胰岛素**", placeholder="种类/剂量/时间/近期变更")
        with col4:
            glp1 = st.text_area("**GLP-1针剂**", placeholder="名称/剂量/时间/近期变更")
            other_meds = st.text_area("**其它药物**", placeholder="其它药物使用情况")

        st.subheader("其他必填项")
        col5, col6 = st.columns(2)
        with col5:
            metabolic_text = st.text_area("**代谢指标**", placeholder="血脂四项/肝功/肾功/尿酸等")
            urinalysis = st.text_area("**尿常规**", placeholder="尿常规结果")
            gad_antibody = st.text_area("**GAD抗体**", placeholder="阴性/阳性及数值")
            diet_staple = st.text_area("**主食类型/量**", placeholder="精米白面/全谷物，每餐量")
        with col6:
            diet_regularity = st.text_area("**三餐规律性**", placeholder="是否规律/暴饮暴食/节食")
            exercise = st.text_area("**运动情况**", placeholder="频率/时长/方式")
            family_dm = st.text_area("**家族糖尿病史**", placeholder="一级亲属中糖尿病情况")
            family_other = st.text_area("**家族其他疾病**", placeholder="高血压/肥胖/冠心病/脂代谢异常")

        submitted = st.form_submit_button("🔬 开始分析", type="primary", use_container_width=True)

    if submitted:
        patient_data = {
            "patient_name": patient_name,
            "age": age,
            "gender": gender,
            "core_symptoms": {
                "triad_symptoms": {
                    "polyuria": polyuria or None,
                    "polydipsia": polydipsia or None,
                    "polyphagia": polyphagia or None,
                    "weight_loss": weight_loss or None,
                },
                "hypoglycemia_reaction": hypoglycemia or "未提供",
            },
            "medical_history": {
                "prior_glucose_history": glucose_history or "未提供",
                "steroid_diuretic_use": steroid_use or "未提供",
            },
            "past_history": {
                "diagnosed_diseases": diagnosed_diseases or "未提供",
                "allergy_history": allergy or "未提供",
            },
            "physical_exam": {
                "height_cm": height,
                "weight_kg": weight,
                "waist_cm": waist,
                "hip_cm": hip,
                "systolic_bp": sbp,
                "diastolic_bp": dbp,
                "pulse_rate": pulse,
            },
            "clinical_tests": {
                "blood_sugar": {
                    "fasting_glucose": fasting_glucose,
                    "hba1c": hba1c,
                    "postprandial_2h_glucose": postprandial,
                    "hypoglycemia_frequency": hypo_freq or "未提供",
                    "medication_glucose_response": med_response or "未提供",
                },
                "insulin": {
                    "fasting_insulin": fasting_insulin,
                    "fasting_c_peptide": fasting_cpeptide,
                },
                "metabolic": {
                    "raw_text": metabolic_text or "未提供",
                },
                "urine": {
                    "urinalysis": urinalysis or "未提供",
                },
                "antibody": {
                    "gad_antibody": gad_antibody or "未提供",
                },
            },
            "medications": {
                "oral_medications": oral_meds or "未提供",
                "insulin_therapy": insulin_therapy or "未提供",
                "glp1_therapy": glp1 or "未提供",
                "other_medications": other_meds or "未提供",
            },
            "lifestyle": {
                "diet_staple": diet_staple or "未提供",
                "diet_regularity": diet_regularity or "未提供",
                "exercise_leisure": exercise or "未提供",
            },
            "family_history": {
                "diabetes_in_relatives": family_dm or "未提供",
                "other_family_diseases": family_other or "未提供",
            },
        }

        with st.spinner("🔄 正在进行多Agent协同分析，请稍候..."):
            try:
                resp = httpx.post(
                    f"{API_BASE}/api/analyze",
                    json={"patient_data": patient_data},
                    timeout=300,
                )
                result = resp.json()

                if result["success"]:
                    st.success(f"✅ 分析完成！报告ID: {result['report_id']}")
                    st.session_state["current_report"] = result["report"]
                    st.session_state["current_report_id"] = result["report_id"]
                else:
                    st.error(f"❌ 分析失败: {result.get('error', '未知错误')}")
                    if result.get("missing_fields"):
                        st.warning(f"缺少必填字段: {', '.join(result['missing_fields'])}")
            except Exception as e:
                st.error(f"❌ 请求失败: {str(e)}\n请确保后端服务已启动 (uvicorn medagent.main:app)")

# ── Tab 2: 对话模式 ────────────────────────────────────────────────────────

with tab2:
    st.header("对话式信息采集")
    st.markdown("通过对话方式逐步采集患者信息，系统会自动引导您完成所有必填项。")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
        st.session_state.chat_session_id = None

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("请输入患者信息...")

    if user_input:
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        with st.spinner("思考中..."):
            try:
                resp = httpx.post(
                    f"{API_BASE}/api/chat",
                    json={
                        "session_id": st.session_state.chat_session_id,
                        "message": user_input,
                    },
                    timeout=120,
                )
                result = resp.json()
                st.session_state.chat_session_id = result["session_id"]

                with st.chat_message("assistant"):
                    st.write(result["reply"])
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": result["reply"]}
                )

                if result.get("intake_complete") and result.get("report_id"):
                    st.success(f"✅ 报告已生成！ID: {result['report_id']}")
                    st.session_state["current_report_id"] = result["report_id"]

            except Exception as e:
                st.error(f"请求失败: {str(e)}")

    if st.button("🔄 开始新对话"):
        st.session_state.chat_messages = []
        st.session_state.chat_session_id = None
        st.rerun()

# ── Tab 3: 报告查看 ────────────────────────────────────────────────────────

with tab3:
    st.header("诊疗报告")

    report_id_input = st.text_input("输入报告ID查看", value=st.session_state.get("current_report_id", ""))

    if st.button("📥 加载报告") and report_id_input:
        try:
            resp = httpx.get(f"{API_BASE}/api/report/{report_id_input}", timeout=30)
            if resp.status_code == 200:
                report_data = resp.json()
                st.session_state["current_report"] = report_data.get("final_report", report_data)
            else:
                st.error("报告不存在")
        except Exception as e:
            st.error(f"加载失败: {str(e)}")

    report = st.session_state.get("current_report")
    if report:
        st.divider()

        # ── 诊断 ──
        diag = report.get("diagnosis", {})
        if diag:
            st.subheader("一、患者临床数据评估")
            st.markdown("#### 1. 糖尿病诊断")
            st.info(f"**分型**: {diag.get('diabetes_type', '未知')}")
            st.write(f"**分型依据**: {diag.get('typing_rationale', '')}")
            st.markdown("#### 2. 病情分析")
            st.write(f"**急性病情**: {diag.get('acute_condition', '')}")
            st.write(f"**慢性病情**: {diag.get('chronic_condition', '')}")

        # ── 血糖 ──
        bs = report.get("blood_sugar_assessment", {})
        if bs:
            st.markdown("#### 3. 血糖水平评估")
            cols = st.columns(3)
            tir_text = bs.get("tir", "")
            tar_text = bs.get("tar", "")
            tbr_text = bs.get("tbr", "")
            cols[0].metric("TIR", _extract_pct(tir_text) or "N/A")
            cols[1].metric("TAR", _extract_pct(tar_text) or "N/A")
            cols[2].metric("TBR", _extract_pct(tbr_text) or "N/A")
            if tir_text:
                st.write(f"**TIR评估**: {tir_text}")
            if tar_text:
                st.write(f"**TAR评估**: {tar_text}")
            if tbr_text:
                st.write(f"**TBR评估**: {tbr_text}")
            st.write(f"**空腹血糖**: {bs.get('fasting_glucose_status', '')}")
            st.write(f"**餐后血糖**: {bs.get('postprandial_glucose_status', '')}")
            st.write(f"**血糖波动**: {bs.get('glucose_variability', '')}")
            st.write(f"**时段分析**: {bs.get('time_segment_analysis', '')}")
            st.write(f"**HbA1c**: {bs.get('hba1c_status', '')}")
            st.write(f"**HbA1c预测**: {bs.get('hba1c_prediction', '')}")

        # ── 胰岛素 ──
        ins = report.get("insulin_assessment", {})
        if ins:
            st.markdown("#### 4. 胰岛素分泌功能评估")
            st.write(f"**基础分泌**: {ins.get('basal_secretion', '')}")
            st.write(f"**餐时分泌**: {ins.get('meal_secretion', '')}")
            st.write(f"**曲线分析**: {ins.get('curve_analysis', '')}")

        # ── 并发症 ──
        comp = report.get("complication_assessment", {})
        if comp:
            st.markdown("#### 5. 并发症和合并症评估")
            st.write(f"**微血管**: {comp.get('microvascular', '')}")
            st.write(f"**大血管**: {comp.get('macrovascular', '')}")
            st.markdown("#### 6. 相关指标异常")
            st.write(comp.get("abnormal_indicators", ""))
            st.markdown("#### 7. 体格检查异常")
            st.write(comp.get("physical_exam_abnormalities", ""))

        # ── 治疗 ──
        tx = report.get("treatment_plan", {})
        if tx:
            st.subheader("二、治疗建议")
            sections = [
                ("1. 急性病情处理", "acute_treatment"),
                ("2. 降糖治疗方案", "glucose_lowering_plan"),
                ("3. 并发症治疗方案", "complication_treatment"),
                ("4. 异常指标干预", "abnormal_indicator_intervention"),
                ("5. 药物禁忌症分析", "contraindication_analysis"),
                ("6. 随诊计划", "follow_up_plan"),
                ("7. 生活方式干预", "lifestyle_intervention"),
                ("8. 自我监控与管理", "self_management"),
            ]
            for title, key in sections:
                st.markdown(f"#### {title}")
                st.write(tx.get(key, ""))

        # ── 预警 ──
        wp = report.get("warning_prediction", {})
        if wp:
            st.subheader("三、预警及预测")
            for key, label in [
                ("disease_trend", "病情发展趋势"),
                ("complication_trend", "并发症趋势"),
                ("organ_disease_trend", "脏器疾病趋势"),
                ("medication_efficacy", "药物疗效预测"),
            ]:
                val = wp.get(key)
                if val:
                    st.write(f"**{label}**: {val}")

        st.divider()
        with st.expander("📄 查看原始JSON"):
            st.json(report)
    else:
        st.info("暂无报告。请通过「结构化录入」或「对话采集」生成报告。")
