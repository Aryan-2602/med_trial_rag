# Dummy Clinical Trial Data Schema

This document describes the comprehensive MySQL schema for dummy clinical trial data that supports complex analytical queries.

## Overview

The dummy data schema consists of **15 tables** designed to support:
- Patient completion predictions
- AE prediction and early warning patterns
- Site-level analytics
- FDA audit risk scoring
- Visit punctuality analysis
- Behavioral adherence tracking
- Lab trend analysis
- Sentiment analysis from physician notes

## Table Structure

### 1. `sites`
**Purpose**: Clinical research sites  
**Key Columns**:
- `site_id` (PK): Unique site identifier
- `site_code`: Site code (e.g., "SITE001")
- `site_name`: Site name
- `country`, `region`: Geographic information
- `principal_investigator`: PI name
- `enrollment_capacity`: Maximum enrollment

**Use Cases**: Site-level analytics, FDA audit risk scoring

### 2. `patients`
**Purpose**: Patient demographics and enrollment  
**Key Columns**:
- `patient_id` (PK): Unique patient identifier
- `patient_number`: Patient number (e.g., "P0001")
- `site_id` (FK): Reference to sites
- `enrollment_date`: Date of enrollment
- `age`, `gender`, `race`, `ethnicity`: Demographics
- `weight_kg`, `height_cm`, `bmi`: Physical characteristics
- `randomization_group`: Treatment/Control/Placebo
- `status`: Active/Completed/Discontinued/Screen Failed
- `discontinuation_reason`, `discontinuation_date`

**Use Cases**: Patient demographics, completion analysis

### 3. `comorbidities`
**Purpose**: Patient comorbidities  
**Key Columns**:
- `comorbidity_id` (PK)
- `patient_id` (FK)
- `condition_name`: Condition name
- `severity`: Mild/Moderate/Severe
- `onset_date`: When condition started
- `is_controlled`: Whether condition is controlled
- `medication`: Medication for condition

**Use Cases**: Comorbidity burden analysis for completion predictions

### 4. `prior_therapies`
**Purpose**: Prior treatment history  
**Key Columns**:
- `prior_therapy_id` (PK)
- `patient_id` (FK)
- `therapy_name`: Name of prior therapy
- `therapy_type`: Type of therapy
- `start_date`, `end_date`: Treatment period
- `response`: Response to therapy
- `tolerance_score`: 1-10 scale (10 = excellent tolerance)
- `adverse_events_count`: Number of AEs during therapy

**Use Cases**: Prior therapy tolerance for completion predictions

### 5. `treatment_cycles`
**Purpose**: Treatment cycle tracking  
**Key Columns**:
- `cycle_id` (PK)
- `patient_id` (FK)
- `cycle_number`: Cycle number (1, 2, 3, ...)
- `planned_start_date`, `actual_start_date`: Start dates
- `planned_end_date`, `actual_end_date`: End dates
- `status`: Planned/In Progress/Completed/Delayed/Skipped/Terminated
- `dose_received`, `dose_planned`: Dosing information
- `dose_reduction_reason`: Reason for dose reduction
- `adherence_percentage`: Medication adherence

**Use Cases**: Treatment completion analysis, cycle adherence

### 6. `visits`
**Purpose**: Visit tracking with punctuality  
**Key Columns**:
- `visit_id` (PK)
- `patient_id` (FK)
- `cycle_id` (FK): Associated treatment cycle
- `visit_number`: Sequential visit number
- `visit_type`: Screening/Baseline/Cycle Visit/End of Treatment/Follow-up
- `planned_date`, `actual_date`: Visit dates
- `punctuality_hours`: Hours difference from planned (negative = early, positive = late)
- `punctuality_variance`: Variance in punctuality across all visits
- `visit_status`: Scheduled/Completed/Missed/Rescheduled/Cancelled
- `site_id` (FK)
- `investigator_notes`: Free text notes

**Use Cases**: Visit punctuality variance analysis, dropout risk

### 7. `adverse_events`
**Purpose**: Adverse event tracking  
**Key Columns**:
- `ae_id` (PK)
- `patient_id` (FK)
- `visit_id` (FK), `cycle_id` (FK)
- `ae_term`: Event term/name
- `meddra_code`: MedDRA code
- `severity_grade`: 1-5 (CTCAE)
- `severity_category`: Grade 1-5
- `onset_date`, `resolution_date`: Event dates
- `is_serious`: Boolean flag
- `seriousness_criteria`: Criteria for seriousness
- `is_related_to_treatment`: Boolean
- `action_taken`: None/Dose Reduced/Dose Interrupted/etc.
- `outcome`: Recovered/Recovering/Not Recovered/etc.
- `site_id` (FK)
- `reported_date`: Date reported to sponsor
- `report_latency_days`: Days between onset and report

**Use Cases**: AE prediction, severity analysis, site-level AE latency

### 8. `lab_results`
**Purpose**: Laboratory test results with trend analysis  
**Key Columns**:
- `lab_result_id` (PK)
- `patient_id` (FK)
- `visit_id` (FK), `cycle_id` (FK)
- `test_date`: Date of test
- `test_name`: Test name (e.g., "ALT", "Creatinine")
- `test_category`: Hematology/Chemistry/Liver Function/Renal Function/etc.
- `test_value`: Test result value
- `unit`: Unit of measurement
- `reference_range_low`, `reference_range_high`: Normal ranges
- `is_abnormal`: Boolean flag
- `abnormality_flag`: Normal/Low/High/Critical Low/Critical High
- `delta_from_baseline`: Change from baseline value
- `delta_percentage`: Percentage change from baseline
- `trend_direction`: Improving/Stable/Worsening/Fluctuating

**Use Cases**: Lab stability analysis, early warning patterns (ALT drift, etc.)

### 9. `vitals`
**Purpose**: Vital signs measurements  
**Key Columns**:
- `vital_id` (PK)
- `patient_id` (FK)
- `visit_id` (FK), `cycle_id` (FK)
- `measurement_date`, `measurement_time`: When measured
- `systolic_bp`, `diastolic_bp`: Blood pressure
- `heart_rate`: Heart rate (bpm)
- `heart_rate_variability`: HRV in milliseconds
- `temperature_celsius`: Body temperature
- `respiratory_rate`: Breathing rate
- `oxygen_saturation`: SpO2
- `weight_kg`: Weight

**Use Cases**: Real-time vitals for AE prediction, HR variability analysis

### 10. `physician_notes`
**Purpose**: Physician notes with sentiment analysis  
**Key Columns**:
- `note_id` (PK)
- `patient_id` (FK)
- `visit_id` (FK)
- `note_date`: Date of note
- `note_type`: Progress Note/AE Note/Treatment Note/etc.
- `note_text`: Full text of note (FULLTEXT indexed)
- `sentiment_score`: -1.0 to 1.0 (negative to positive)
- `sentiment_label`: Very Negative/Negative/Neutral/Positive/Very Positive
- `key_findings`: Extracted key findings
- `concerns_mentioned`: Concerns mentioned in note

**Use Cases**: Sentiment analysis for AE prediction, note search

### 11. `behavioral_adherence`
**Purpose**: Behavioral adherence tracking  
**Key Columns**:
- `adherence_id` (PK)
- `patient_id` (FK)
- `cycle_id` (FK)
- `assessment_date`: Date of assessment
- `medication_adherence_percentage`: Medication adherence (0-100)
- `visit_adherence_percentage`: Visit adherence (0-100)
- `diary_completion_percentage`: Diary completion (0-100)
- `overall_adherence_score`: Weighted average (0-100)
- `missed_doses_count`, `late_doses_count`: Adherence metrics
- `adherence_pattern`: Excellent/Good/Fair/Poor/Very Poor
- `risk_factors`: Factors affecting adherence

**Use Cases**: Adherence patterns for completion predictions

### 12. `sae_reconciliation`
**Purpose**: SAE reconciliation tracking (FDA audit)  
**Key Columns**:
- `reconciliation_id` (PK)
- `site_id` (FK)
- `sae_id`: Reference to adverse_events (where is_serious=TRUE)
- `reconciliation_date`: Date of reconciliation
- `reconciliation_status`: Pending/In Progress/Completed/Overdue
- `lag_days`: Days between SAE onset and reconciliation completion
- `documentation_completeness`: 0-100 percentage
- `metadata_completeness`: 0-100 percentage
- `discrepancies_found`: Text description
- `corrective_actions`: Actions taken

**Use Cases**: FDA audit risk scoring, SAE reconciliation lag

### 13. `documentation_metadata`
**Purpose**: Documentation quality tracking (FDA audit)  
**Key Columns**:
- `metadata_id` (PK)
- `site_id` (FK)
- `document_type`: CRF/Source Document/Lab Report/AE Report/etc.
- `document_date`: Date of document
- `completeness_score`: 0-100
- `timeliness_score`: 0-100 (based on submission delay)
- `quality_score`: 0-100
- `missing_fields`: List of missing fields
- `inconsistencies`: List of inconsistencies

**Use Cases**: FDA audit risk scoring, documentation quality

### 14. `pk_data`
**Purpose**: Pharmacokinetic data  
**Key Columns**:
- `pk_id` (PK)
- `patient_id` (FK)
- `visit_id` (FK), `cycle_id` (FK)
- `sample_date`, `sample_time`: When sample taken
- `time_point_hours`: Hours post-dose
- `concentration`: PK concentration
- `unit`: Unit (typically "ng/mL")
- `is_linked_to_ae`: Boolean flag
- `linked_ae_id` (FK): Reference to adverse_events

**Use Cases**: PK-AE linkage, FDA query prediction (missing PK linkage)

### 15. `fda_audit_risk_scores`
**Purpose**: FDA audit risk scoring per site  
**Key Columns**:
- `risk_score_id` (PK)
- `site_id` (FK)
- `assessment_date`: Date of assessment
- `overall_risk_score`: 0-100 (higher = more risk)
- `risk_category`: Low/Medium/High/Critical
- `documentation_latency_score`: 0-100
- `sae_reconciliation_lag_score`: 0-100
- `metadata_completeness_score`: 0-100
- `ae_severity_inconsistencies_count`: Count of inconsistencies
- `missing_pk_linkage_count`: Count of missing PK linkages
- `other_risk_factors`: Text description
- `recommendations`: Recommendations for site

**Use Cases**: FDA audit risk simulation, site-specific corrective actions

## Query Examples

### Query 1: Top 30 patients most likely to complete treatment
```sql
SELECT 
    p.patient_id,
    p.patient_number,
    -- Lab stability score
    (SELECT AVG(ABS(lr.delta_percentage)) 
     FROM lab_results lr 
     WHERE lr.patient_id = p.patient_id) as lab_stability,
    -- Comorbidity burden
    (SELECT COUNT(*) FROM comorbidities c WHERE c.patient_id = p.patient_id) as comorbidity_count,
    -- Prior therapy tolerance
    (SELECT AVG(pt.tolerance_score) 
     FROM prior_therapies pt 
     WHERE pt.patient_id = p.patient_id) as prior_tolerance,
    -- Behavioral adherence
    (SELECT AVG(ba.overall_adherence_score) 
     FROM behavioral_adherence ba 
     WHERE ba.patient_id = p.patient_id) as adherence_score
FROM patients p
WHERE p.status = 'Active'
ORDER BY 
    (lab_stability DESC) +  -- Lower is better
    (comorbidity_count ASC) +  -- Lower is better
    (prior_tolerance DESC) +  -- Higher is better
    (adherence_score DESC)  -- Higher is better
LIMIT 30;
```

### Query 2: Predict Grade ≥ 3 AEs within 14 days
```sql
SELECT 
    p.patient_id,
    p.patient_number,
    -- Real-time vitals (recent)
    (SELECT AVG(v.heart_rate) FROM vitals v 
     WHERE v.patient_id = p.patient_id 
     AND v.measurement_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)) as recent_hr,
    -- Lab deltas
    (SELECT MAX(ABS(lr.delta_percentage)) FROM lab_results lr 
     WHERE lr.patient_id = p.patient_id 
     AND lr.test_name IN ('ALT', 'AST', 'Creatinine')
     AND lr.test_date >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)) as max_lab_delta,
    -- Sentiment tone
    (SELECT AVG(pn.sentiment_score) FROM physician_notes pn 
     WHERE pn.patient_id = p.patient_id 
     AND pn.note_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)) as sentiment
FROM patients p
WHERE p.status = 'Active'
HAVING max_lab_delta > 25 OR sentiment < -0.3;
```

### Query 3: Early warning patterns
```sql
SELECT 
    p.patient_id,
    p.patient_number,
    -- ALT drift > 25%
    (SELECT MAX(lr.delta_percentage) FROM lab_results lr 
     WHERE lr.patient_id = p.patient_id 
     AND lr.test_name = 'ALT') as alt_drift,
    -- HR variability > 15%
    (SELECT STDDEV(v.heart_rate_variability) / AVG(v.heart_rate_variability) * 100 
     FROM vitals v 
     WHERE v.patient_id = p.patient_id) as hr_variability_pct
FROM patients p
WHERE p.status = 'Active'
HAVING alt_drift > 25 OR hr_variability_pct > 15;
```

### Query 4: Visit punctuality variance
```sql
SELECT 
    p.patient_id,
    p.patient_number,
    AVG(v.punctuality_hours) as avg_punctuality,
    STDDEV(v.punctuality_hours) as punctuality_variance,
    COUNT(*) as visit_count
FROM patients p
JOIN visits v ON p.patient_id = v.patient_id
WHERE p.status = 'Active'
GROUP BY p.patient_id, p.patient_number
HAVING punctuality_variance > 8;  -- High variance = dropout risk
```

### Query 5: Site-level AE latency
```sql
SELECT 
    s.site_id,
    s.site_code,
    AVG(ae.report_latency_days) as avg_latency,
    STDDEV(ae.report_latency_days) as latency_stddev,
    COUNT(*) as ae_count
FROM sites s
JOIN adverse_events ae ON s.site_id = ae.site_id
GROUP BY s.site_id, s.site_code
HAVING avg_latency > 3 OR latency_stddev > 5;  -- Abnormal latency
```

### Query 6: FDA audit risk score
```sql
SELECT 
    s.site_id,
    s.site_code,
    fars.assessment_date,
    fars.overall_risk_score,
    fars.risk_category,
    fars.documentation_latency_score,
    fars.sae_reconciliation_lag_score,
    fars.metadata_completeness_score,
    fars.recommendations
FROM sites s
JOIN fda_audit_risk_scores fars ON s.site_id = fars.site_id
WHERE fars.assessment_date = (
    SELECT MAX(assessment_date) 
    FROM fda_audit_risk_scores 
    WHERE site_id = s.site_id
)
ORDER BY fars.overall_risk_score DESC;
```

## Data Generation

To generate dummy data:

```bash
make create-dummy-data
```

Or directly:

```bash
PYTHONPATH=. python scripts/create_dummy_clinical_trial_data.py
```

This will create:
- 10 sites
- 200 patients
- Comprehensive data across all 15 tables
- Realistic relationships and patterns

## Notes

- All dates are relative to `STUDY_START_DATE` (2023-01-01)
- Data includes realistic patterns (e.g., lab drift, AE clustering)
- Foreign key relationships are properly maintained
- Indexes are created for common query patterns
- Full-text search is available on `physician_notes.note_text`

