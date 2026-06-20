RISK_QUESTIONS = [
    {"id": "bias_001", "category": "bias", "label": "训练或评估数据是否覆盖低资源语言、方言和边缘用户群体？"},
    {"id": "bias_002", "category": "bias", "label": "是否评估不同群体间的输出质量差异？"},
    {"id": "misuse_001", "category": "misuse", "label": "模型是否可能被用于虚假信息、欺诈或操纵性内容生成？"},
    {"id": "privacy_001", "category": "privacy", "label": "训练或日志数据是否包含PII，且是否有脱敏与删除策略？"},
    {"id": "safety_001", "category": "safety", "label": "拒答边界、越狱防护和人工升级机制是否明确？"},
    {"id": "environment_001", "category": "environment", "label": "训练/推理能耗和碳足迹是否被估算并记录？"},
    {"id": "labor_001", "category": "labor", "label": "标注、审核或内容治理劳动条件是否被纳入评估？"},
]

REFLEXIVITY_QUESTIONS = [
    "我们假定的典型用户是谁？为什么？",
    "哪些用户或场景没有被充分纳入设计？",
    "安全、隐私、自由表达、公平、效率之间如何排序？",
    "有害内容定义是否考虑文化差异和制度语境？",
    "哪些价值冲突已经被识别但尚未解决？",
]

MONITORING_TEMPLATES = [
    {"dimension": "有害输出", "metric": "用户举报率、自动检测命中率", "threshold": "周环比上升50%触发复审"},
    {"dimension": "偏见表现", "metric": "不同群体间输出质量差异", "threshold": "显著差异或持续扩大触发复审"},
    {"dimension": "滥用检测", "metric": "疑似恶意使用模式", "threshold": "实时告警"},
    {"dimension": "拒答率", "metric": "按主题分类的拒绝回答比例", "threshold": "过度拒答超过阈值触发复审"},
    {"dimension": "用户反馈", "metric": "满意度、投诉分类、申诉量", "threshold": "持续下降趋势触发复审"},
]

COMPLIANCE_TEMPLATES = [
    {
        "jurisdiction": "中国大陆",
        "norm_reference": "生成式人工智能服务管理暂行办法",
        "requirement_summary": "关注内容安全、数据治理、服务规范和用户权益保护。",
        "related_questions": ["privacy_001", "safety_001", "misuse_001"],
        "evidence_required": "内容安全策略、数据处理说明、用户投诉/申诉机制。",
    },
    {
        "jurisdiction": "中国大陆",
        "norm_reference": "新一代人工智能伦理规范",
        "requirement_summary": "要求伦理道德融入人工智能全生命周期，强调公平、公正、可控、可信。",
        "related_questions": ["bias_001", "bias_002", "labor_001"],
        "evidence_required": "生命周期伦理评估记录、偏见测试、参与计划。",
    },
    {
        "jurisdiction": "国际",
        "norm_reference": "UNESCO Recommendation on the Ethics of Artificial Intelligence",
        "requirement_summary": "强调人权、尊严、多样性、包容性和环境可持续。",
        "related_questions": ["bias_001", "environment_001", "labor_001"],
        "evidence_required": "人权影响说明、弱势群体参与记录、环境影响估算。",
    },
]

DOMAIN_TEMPLATES = {
    "教育": {"bias": 1.2, "privacy": 1.3, "safety": 1.2, "misuse": 1.0, "environment": 0.6, "labor": 0.8},
    "医疗": {"bias": 1.3, "privacy": 1.5, "safety": 1.5, "misuse": 1.0, "environment": 0.6, "labor": 0.8},
    "金融": {"bias": 1.4, "privacy": 1.4, "safety": 1.2, "misuse": 1.3, "environment": 0.5, "labor": 0.7},
    "政务": {"bias": 1.4, "privacy": 1.4, "safety": 1.4, "misuse": 1.2, "environment": 0.5, "labor": 0.8},
    "通用": {"bias": 1.0, "privacy": 1.0, "safety": 1.0, "misuse": 1.0, "environment": 1.0, "labor": 1.0},
}
