-- drugs                药品主表
-- drug_indications     适应症
-- drug_contraindications 禁忌症规则
-- drug_side_effects    不良反应
-- drug_interactions    药物相互作用
-- drug_aliases         药物别名，可选但建议加

CREATE TABLE IF NOT EXISTS drugs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(128) NOT NULL UNIQUE,
    category VARCHAR(128),
    dose_range TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS drug_aliases (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    drug_id BIGINT NOT NULL,
    alias VARCHAR(128) NOT NULL,
    UNIQUE KEY uq_drug_alias (drug_id, alias),
    KEY idx_drug_alias (alias),
    CONSTRAINT fk_drug_aliases_drug FOREIGN KEY (drug_id) REFERENCES drugs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS drug_indications (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    drug_id BIGINT NOT NULL,
    indication TEXT NOT NULL,
    CONSTRAINT fk_drug_indications_drug FOREIGN KEY (drug_id) REFERENCES drugs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS drug_contraindications (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    drug_id BIGINT NOT NULL,
    rule_key VARCHAR(64) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(32) DEFAULT 'warning',
    KEY idx_drug_contra_rule (rule_key),
    CONSTRAINT fk_drug_contraindications_drug FOREIGN KEY (drug_id) REFERENCES drugs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS drug_side_effects (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    drug_id BIGINT NOT NULL,
    side_effect TEXT NOT NULL,
    CONSTRAINT fk_drug_side_effects_drug FOREIGN KEY (drug_id) REFERENCES drugs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS drug_interactions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    drug_a VARCHAR(128) NOT NULL,
    drug_b VARCHAR(128) NOT NULL,
    interaction TEXT NOT NULL,
    severity VARCHAR(32) DEFAULT 'warning',
    KEY idx_drug_interaction_a (drug_a),
    KEY idx_drug_interaction_b (drug_b)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
