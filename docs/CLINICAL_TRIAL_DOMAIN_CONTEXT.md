# Clinical Trial Domain Context for Plausible Answer Generation

This document provides domain knowledge and typical patterns for generating realistic answers when specific data is unavailable. It combines protocol context (from S130_LLM_Context.md) with SQL data patterns.

---

## Part 1: Study-Specific Context (H3E-US-S130)

### Trial Overview
**Study ID:** H3E-US-S130  
**Investigational product:** Pemetrexed (LY231514)  
**Comparator regimen:** Paclitaxel + Carboplatin + Bevacizumab  
**Design:** Multicenter, randomized (1:1), open-label, Phase 3  
**Population:** Adults (≥ 18 years) with histologic or cytologic diagnosis of measurable, advanced nonsquamous NSCLC (Stage IV M1a/M1b) not amenable to curative therapy  
**Primary Objective:** Compare **progression-free survival without grade 4 toxicity (G4PFS)** between treatment arms  
**Secondary Objectives:** PFS, OS, ORR, DCR, and safety profile (per CTCAE v3.0)

### Treatment Schema
- **Arm A:** Pemetrexed 500 mg/m² IV (q21 days × 4 cycles) + Carboplatin AUC 6 → Maintenance Pemetrexed q21 days until PD or toxicity
- **Arm B:** Paclitaxel 200 mg/m² IV 3 h + Carboplatin AUC 6 + Bevacizumab 15 mg/kg IV 30–90 min → Maintenance Bevacizumab q21 days until PD
- **Premedication (Arm A):**
  - Folic acid 350–1000 µg PO QD ≥ 7 days before Cycle 1 and through 3 weeks post-last dose
  - Vitamin B12 1000 µg IM ~ 1–2 weeks before Cycle 1, repeated q9 weeks
  - Dexamethasone 4 mg PO BID the day before, of, and after each pemetrexed dose
- **Follow-up:** 30-day post-discontinuation FU then q90 days until death/loss-to-follow-up

### Study Periods and Visits
- **Induction (Cycles 1–4):** 21-day intervals
- **Maintenance:** 21-day cycles (VISID 500–599)
- **Post-Study FU:** VISID ≥ 801 (e.g., 801–899)
- **Visit mapping:** Baseline VISID 10 → VISFWDID 0; Induction cycles 100–400 → 1–4; Maintenance/post-study mapped sequentially

### Safety and AE Handling
- **Adverse Event (AE)** = any untoward medical occurrence, regardless of causality
- **Serious AE (SAE):** death (excl. PD), life-threatening event, hospitalization, disability, congenital anomaly, or medically significant event
- SAE collection begins after informed consent + first dose; must be reported within 24 h to sponsor
- **Severity:** CTCAE v3.0 grading (0–4)
- **Event Recording:** AEs captured at each visit; pre-existing conditions and changes must be updated

### Efficacy Assessments
**Tumor response:** RECIST v1.0 criteria
- CR = disappearance of all lesions (confirmed × 2)
- PR = ≥ 30% decrease (sum of diameters)
- PD = ≥ 20% increase or new lesions
- SD = neither PR nor PD ≥ 6 weeks post-baseline

**Endpoints:**
- **OS:** Randomization → death (any cause); censored at last known alive
- **PFS:** Randomization → PD or death; censored at last progression-free assessment
- **G4PFS:** Time to either grade 4 toxicity or progression
- **BOR (Best Overall Response):** Derived from LESIONS ADS records before Visit 802

---

## Part 2: General Clinical Trial Patterns (SQL Data)

### Patient Demographics - Typical Ranges

#### Age Distribution
- **Mean Age:** 60-70 years (for oncology trials like S130)
- **Range:** 18-90 years (most commonly 40-85)
- **Standard Deviation:** 8-12 years
- **Typical Distribution:** Slightly skewed toward older adults
- **S130 Specific:** Mean ~65 years, range 41-86 years

#### Gender Distribution
- **Female:** 50-60% (common in oncology trials)
- **Male:** 40-50%
- **Other:** <1%
- **S130 Specific:** ~58% female, ~42% male

#### Race/Ethnicity
- **White/Caucasian:** 70-85%
- **Black/African American:** 10-20%
- **Asian:** 5-15%
- **Other:** 2-5%
- **Hispanic/Latino:** 10-25%
- **S130 Specific:** Predominantly White (87%), with smaller Black (11%) and Other (2%) populations

#### Physical Characteristics
- **Weight:** 50-120 kg (typical range)
- **Height:** 150-200 cm
- **BMI:** 18-35 kg/m² (most common: 20-30)

### Treatment Arms
- **Typical Arms:** 2-4 treatment arms
- **Common Names:** "Arm A", "Arm B", "Treatment", "Control", "Placebo"
- **Distribution:** Usually balanced (1:1 or 2:1 ratios)
- **S130 Specific:** 
  - Arm A: Pemetrexed + Carboplatin
  - Arm B: Paclitaxel + Carboplatin + Bevacizumab
  - Approximately 1:1 randomization

### Adverse Events - Typical Patterns

#### Severity Distribution (CTCAE Grades)
- **Grade 1 (Mild):** 40-50% of all AEs
- **Grade 2 (Moderate):** 30-35%
- **Grade 3 (Severe):** 15-20%
- **Grade 4 (Life-threatening):** 5-10%
- **Grade 5 (Death):** <2%

#### Common AE Terms (Oncology Trials)
- **Fatigue:** Most common, 60-80% of patients
- **Nausea:** 40-60%
- **Diarrhea:** 30-50%
- **Rash:** 20-40%
- **Headache:** 20-35%
- **Neutropenia:** 15-30%
- **Thrombocytopenia:** 10-25%
- **Anemia:** 20-40%
- **ALT Increased:** 10-20%
- **AST Increased:** 8-15%
- **Creatinine Increased:** 5-15%
- **Hypertension:** 10-20% (especially with Bevacizumab)
- **Hypotension:** 5-10%

#### Serious Adverse Events (SAEs)
- **Percentage of patients with SAEs:** 15-30%
- **SAE rate:** 0.1-0.5 SAEs per patient-year
- **Common SAEs:** Hospitalization, life-threatening events, death
- **Report latency:** Typically 0-7 days from onset

#### AE Timing
- **Onset:** Usually within first 3 months of treatment
- **Resolution:** Most resolve within 30 days
- **Chronic AEs:** 10-20% may persist

### Laboratory Values - Typical Ranges

#### Hematology
- **WBC (White Blood Count):** 4-11 × 10³/μL (normal: 4-11)
- **RBC (Red Blood Count):** 4-6 × 10⁶/μL (normal: 4-6)
- **Hemoglobin:** 12-16 g/dL (normal: 12-16)
- **Hematocrit:** 36-48% (normal: 36-48)
- **Platelets:** 150-450 × 10³/μL (normal: 150-450)
- **Neutrophils:** 2-7 × 10³/μL (normal: 2-7)
- **Lymphocytes:** 1-4 × 10³/μL (normal: 1-4)

#### Liver Function
- **ALT:** 7-56 U/L (normal: 7-56)
- **AST:** 10-40 U/L (normal: 10-40)
- **Bilirubin:** 0.1-1.2 mg/dL (normal: 0.1-1.2)
- **Albumin:** 3.5-5.0 g/dL (normal: 3.5-5.0)
- **Alkaline Phosphatase:** 44-147 U/L (normal: 44-147)

#### Renal Function
- **Creatinine:** 0.6-1.2 mg/dL (normal: 0.6-1.2)
- **BUN:** 7-20 mg/dL (normal: 7-20)
- **eGFR:** >60 mL/min/1.73m² (normal: >60)

#### Chemistry
- **Glucose:** 70-100 mg/dL (fasting, normal: 70-100)
- **Sodium:** 136-145 mEq/L (normal: 136-145)
- **Potassium:** 3.5-5.0 mEq/L (normal: 3.5-5.0)
- **Calcium:** 8.5-10.5 mg/dL (normal: 8.5-10.5)

#### Abnormal Patterns
- **Mild abnormality:** 1.1-1.5× upper limit of normal (ULN)
- **Moderate abnormality:** 1.5-3× ULN
- **Severe abnormality:** >3× ULN
- **Critical:** >5× ULN or <0.5× lower limit
- **Delta patterns:** ALT drift >25%, HR variability >15% are early warning signs

### Vital Signs - Typical Ranges
- **Systolic BP:** 100-160 mmHg (normal: <120)
- **Diastolic BP:** 60-100 mmHg (normal: <80)
- **Heart Rate:** 60-100 bpm (normal: 60-100)
- **Heart Rate Variability:** 20-60 ms (normal: 20-60)
- **Temperature:** 36.0-37.5°C (normal: 36.5-37.2)
- **Respiratory Rate:** 12-20 breaths/min (normal: 12-20)
- **Oxygen Saturation:** 95-100% (normal: >95%)

### Visit Patterns
- **Screening:** 1-2 weeks before enrollment
- **Baseline:** Day 1 (enrollment)
- **Cycle Visits:** Every 21-28 days (typical cycle length)
- **Number of Cycles:** 4-8 cycles typical
- **Follow-up:** Every 3-6 months post-treatment
- **Punctuality:** ±2 hours typical, variance of 1-4 hours
- **Punctuality variance >8-12 hours:** Associated with 8-12% increased dropout risk

### Patient Status Distribution
- **Active:** 50-70% (ongoing treatment)
- **Completed:** 20-35% (finished all cycles)
- **Discontinued:** 10-20% (early termination)
- **Screen Failed:** 5-15% (didn't meet criteria)

#### Discontinuation Reasons
- **Adverse Event:** 30-40% of discontinuations
- **Patient Withdrawal:** 20-30%
- **Protocol Violation:** 10-15%
- **Lost to Follow-up:** 5-10%
- **Physician Decision:** 10-15%
- **Disease Progression:** 20-30%

### Treatment Cycles
- **Typical Cycles:** 4-8 cycles
- **Cycle Length:** 21-28 days (S130 uses 21-day cycles)
- **Dose Reductions:** 10-25% of patients
- **Dose Interruptions:** 15-30% of patients
- **Adherence:** 85-100% typical

### Comorbidities - Common Conditions
- **Hypertension:** 30-50% of patients
- **Diabetes:** 15-25%
- **Hyperlipidemia:** 20-35%
- **Asthma/COPD:** 10-20%
- **Arthritis:** 15-25%
- **Depression/Anxiety:** 10-20%
- **Obesity:** 20-35%
- **Heart Disease:** 10-20%

### Prior Therapies
- **Patients with prior therapy:** 60-80%
- **Common Types:** Chemotherapy, Immunotherapy, Radiation, Surgery
- **Tolerance Scores:** 1-10 scale, typically 5-8
- **Response Rates:**
  - Complete Response: 10-20%
  - Partial Response: 20-30%
  - Stable Disease: 30-40%
  - Progressive Disease: 20-30%

### Behavioral Adherence
- **Medication Adherence:** 80-100% (typical: 90-95%)
- **Visit Adherence:** 85-100% (typical: 95%)
- **Diary Completion:** 60-90% (typical: 75%)
- **Overall Adherence Score:** 75-95 (typical: 85-90)
- **Adherence Patterns:**
  - Excellent (≥95%): 40-50%
  - Good (85-94%): 30-40%
  - Fair (75-84%): 10-15%
  - Poor (<75%): 5-10%

### Site Characteristics
- **Enrollment per Site:** 2-10 patients typical
- **Site Capacity:** 20-100 patients
- **Countries:** Usually 1-5 countries
- **Regions:** North, South, East, West, Central
- **S130 Specific:** 54 sites, 1 country (US), ~3-4 patients per site

### Time-to-Event Endpoints
- **Progression-Free Survival (PFS):** 6-18 months median
- **Overall Survival (OS):** 12-36 months median
- **Time to Progression:** 4-12 months median
- **Event-Free Survival:** 3-12 months median
- **G4PFS (S130 specific):** Time to grade 4 toxicity or progression

### Response Rates
- **Complete Response (CR):** 10-30%
- **Partial Response (PR):** 20-40%
- **Stable Disease (SD):** 20-30%
- **Progressive Disease (PD):** 10-20%
- **Not Evaluable:** 5-10%

### Statistical Patterns

#### Counts and Aggregations
- **Patient counts:** Usually 100-300, sometimes up to 1000
- **S130 Specific:** ~179 patients
- **Event counts:** 10-50 events per patient on average
- **Visit counts:** 5-15 visits per patient
- **Lab result counts:** 20-100 per patient

#### Percentages
- **Response rates:** Usually 30-70% combined (CR+PR)
- **AE rates:** 80-100% of patients experience at least one AE
- **SAE rates:** 15-30% of patients
- **Discontinuation rates:** 10-25%

#### Averages and Medians
- **Mean age:** 60-70 years
- **Mean BMI:** 25-28
- **Mean cycles completed:** 4-6 cycles
- **Median time to event:** 6-18 months

### Site-Level Analytics

#### AE Latency Patterns
- **Normal report latency:** 0-3 days
- **Abnormal latency:** >7 days (may indicate site issues)
- **Severity distribution:** Should follow typical patterns (40% Grade 1, 30% Grade 2, 20% Grade 3, etc.)
- **Inconsistencies:** Same AE term with >2 grade difference across visits is unusual

#### Documentation Quality
- **Completeness scores:** 70-100% typical
- **Timeliness scores:** 60-100% typical
- **Quality scores:** 75-100% typical
- **Missing fields:** Common issues include signatures, dates, investigator names

#### FDA Audit Risk Factors
- **Documentation latency:** >14 days is high risk
- **SAE reconciliation lag:** >7 days is high risk
- **Metadata completeness:** <80% is high risk
- **AE severity inconsistencies:** >5 per site is high risk
- **Missing PK linkage:** >10 per site is high risk

---

## Answer Generation Guidelines

When generating plausible answers:

1. **Use realistic ranges** from the patterns above
2. **Maintain consistency** - if you say 200 patients, use proportions that make sense
3. **Include uncertainty** - use phrases like "typically", "commonly", "approximately"
4. **Structure like real data** - use tables, lists, percentages
5. **Reference clinical conventions** - use proper medical terminology
6. **Be specific but not overly precise** - "approximately 65 years" not "64.616 years"
7. **Include context** - explain what the numbers mean
8. **Use appropriate units** - mg/dL, U/L, %, etc.
9. **Reference S130 specifics** when relevant (Pemetrexed, Bevacizumab, 21-day cycles, etc.)

## Example Plausible Answer Patterns

### Demographics Query
"Based on typical patterns for this type of clinical trial, the study likely enrolled approximately 150-250 patients with a mean age of 65 years (range: 40-85 years). Gender distribution is typically 55% female and 45% male. The majority of patients (approximately 75-85%) are White/Caucasian."

### AE Query
"Common adverse events in this type of trial typically include fatigue (occurring in 60-80% of patients), nausea (40-60%), and diarrhea (30-50%). Grade 3 or higher adverse events are observed in approximately 20-30% of patients. Serious adverse events occur in 15-25% of patients."

### Lab Query
"Typical laboratory values for this patient population show ALT levels in the range of 10-40 U/L at baseline, with increases of 10-30% observed during treatment in some patients. Creatinine levels typically remain stable around 0.8-1.0 mg/dL."

### Completion Query
"Based on typical completion patterns, approximately 60-70% of patients remain active in the study, 20-30% complete all planned cycles, and 10-20% discontinue early. Common reasons for discontinuation include adverse events (30-40% of discontinuations) and patient withdrawal (20-30%)."

### Site Analytics Query
"Site-level analysis typically shows average AE report latency of 1-3 days. Sites with latency >7 days or severity distribution inconsistencies may require additional oversight. Documentation completeness scores typically range from 70-100%, with scores below 80% indicating potential quality concerns."

