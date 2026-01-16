#!/usr/bin/env python3
"""
Create dummy clinical trial data for CoTrial RAG system.

This script creates comprehensive SQL tables with realistic dummy data
that supports complex clinical trial queries including:
- Patient completion predictions
- AE prediction and early warning patterns
- Site-level analytics
- FDA audit risk scoring
"""

import mysql.connector
import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Config import removed - using environment variables directly

# Configuration
NUM_PATIENTS = 200
NUM_SITES = 10
NUM_TREATMENT_CYCLES = 6
DAYS_PER_CYCLE = 28
STUDY_START_DATE = datetime(2023, 1, 1)


def get_db_connection() -> mysql.connector.MySQLConnection:
    """Get MySQL database connection."""
    # Get MySQL connection parameters from environment
    mysql_host = os.getenv("MYSQL_HOST", "localhost")
    mysql_port = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user = os.getenv("MYSQL_USER", "root")
    mysql_password = os.getenv("MYSQL_PASSWORD") or os.getenv("MYSQL_PWD", "")
    mysql_db = os.getenv("MYSQL_DB", "cotrial_rag")
    
    if not mysql_password:
        raise ValueError("MYSQL_PASSWORD environment variable is required")
    
    return mysql.connector.connect(
        host=mysql_host,
        port=mysql_port,
        user=mysql_user,
        password=mysql_password,
        database=mysql_db,
    )


def random_string(length: int = 8) -> str:
    """Generate random string."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def random_date(start: datetime, end: datetime) -> datetime:
    """Generate random date between start and end."""
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)


def create_tables(cursor, conn) -> None:
    """Create all clinical trial tables."""
    
    print("📊 Creating clinical trial tables...")
    
    # Drop existing tables if they exist (to ensure clean schema)
    print("  Dropping existing tables if they exist...")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    tables = [
        'fda_audit_risk_scores', 'pk_data', 'documentation_metadata', 'sae_reconciliation',
        'behavioral_adherence', 'physician_notes', 'vitals', 'lab_results', 'adverse_events',
        'visits', 'treatment_cycles', 'prior_therapies', 'comorbidities', 'patients', 'sites'
    ]
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    print("  ✅ Dropped existing tables")
    
    # 1. Sites table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sites (
            site_id INT PRIMARY KEY AUTO_INCREMENT,
            site_code VARCHAR(20) UNIQUE NOT NULL,
            site_name VARCHAR(200) NOT NULL,
            country VARCHAR(100),
            region VARCHAR(100),
            principal_investigator VARCHAR(200),
            enrollment_capacity INT DEFAULT 50,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_site_code (site_code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # 2. Patients table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id INT PRIMARY KEY AUTO_INCREMENT,
            patient_number VARCHAR(50) UNIQUE NOT NULL,
            site_id INT NOT NULL,
            enrollment_date DATE NOT NULL,
            age INT NOT NULL,
            gender ENUM('M', 'F', 'Other') NOT NULL,
            race VARCHAR(50),
            ethnicity VARCHAR(50),
            weight_kg DECIMAL(5,2),
            height_cm DECIMAL(5,2),
            bmi DECIMAL(4,2),
            randomization_group ENUM('Treatment', 'Control', 'Placebo') NOT NULL,
            status ENUM('Active', 'Completed', 'Discontinued', 'Screen Failed') DEFAULT 'Active',
            discontinuation_reason TEXT,
            discontinuation_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (site_id) REFERENCES sites(site_id),
            INDEX idx_patient_number (patient_number),
            INDEX idx_site_id (site_id),
            INDEX idx_status (status),
            INDEX idx_enrollment_date (enrollment_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # 3. Comorbidities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comorbidities (
            comorbidity_id INT PRIMARY KEY AUTO_INCREMENT,
            patient_id INT NOT NULL,
            condition_name VARCHAR(200) NOT NULL,
            severity ENUM('Mild', 'Moderate', 'Severe') DEFAULT 'Mild',
            onset_date DATE,
            is_controlled BOOLEAN DEFAULT TRUE,
            medication VARCHAR(200),
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
            INDEX idx_patient_id (patient_id),
            INDEX idx_condition (condition_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # 4. Prior therapies table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prior_therapies (
            prior_therapy_id INT PRIMARY KEY AUTO_INCREMENT,
            patient_id INT NOT NULL,
            therapy_name VARCHAR(200) NOT NULL,
            therapy_type VARCHAR(100),
            start_date DATE,
            end_date DATE,
            response ENUM('Complete Response', 'Partial Response', 'Stable Disease', 
                         'Progressive Disease', 'Not Evaluable') DEFAULT 'Not Evaluable',
            tolerance_score INT DEFAULT 5 COMMENT '1-10 scale, 10 = excellent tolerance',
            adverse_events_count INT DEFAULT 0,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
            INDEX idx_patient_id (patient_id),
            INDEX idx_tolerance (tolerance_score)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # 5. Treatment cycles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS treatment_cycles (
            cycle_id INT PRIMARY KEY AUTO_INCREMENT,
            patient_id INT NOT NULL,
            cycle_number INT NOT NULL,
            planned_start_date DATE NOT NULL,
            actual_start_date DATE,
            planned_end_date DATE NOT NULL,
            actual_end_date DATE,
            status ENUM('Planned', 'In Progress', 'Completed', 'Delayed', 'Skipped', 'Terminated') DEFAULT 'Planned',
            dose_received DECIMAL(8,2),
            dose_planned DECIMAL(8,2),
            dose_reduction_reason TEXT,
            adherence_percentage DECIMAL(5,2) DEFAULT 100.0,
            notes TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
            INDEX idx_patient_id (patient_id),
            INDEX idx_cycle_number (cycle_number),
            INDEX idx_status (status),
            UNIQUE KEY unique_patient_cycle (patient_id, cycle_number)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # 6. Visits table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            visit_id INT PRIMARY KEY AUTO_INCREMENT,
            patient_id INT NOT NULL,
            cycle_id INT,
            visit_number INT NOT NULL,
            visit_type ENUM('Screening', 'Baseline', 'Cycle Visit', 'End of Treatment', 
                           'Follow-up', 'Unscheduled') NOT NULL,
            planned_date DATE NOT NULL,
            actual_date DATE,
            punctuality_hours DECIMAL(6,2) COMMENT 'Hours difference from planned (negative = early, positive = late)',
            punctuality_variance DECIMAL(6,2) COMMENT 'Variance in punctuality across all visits',
            visit_status ENUM('Scheduled', 'Completed', 'Missed', 'Rescheduled', 'Cancelled') DEFAULT 'Scheduled',
            site_id INT NOT NULL,
            investigator_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
            FOREIGN KEY (cycle_id) REFERENCES treatment_cycles(cycle_id) ON DELETE SET NULL,
            FOREIGN KEY (site_id) REFERENCES sites(site_id),
            INDEX idx_patient_id (patient_id),
            INDEX idx_planned_date (planned_date),
            INDEX idx_actual_date (actual_date),
            INDEX idx_punctuality (punctuality_hours),
            INDEX idx_visit_status (visit_status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # 7. Adverse events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS adverse_events (
            ae_id INT PRIMARY KEY AUTO_INCREMENT,
            patient_id INT NOT NULL,
            visit_id INT,
            cycle_id INT,
            ae_term VARCHAR(500) NOT NULL,
            meddra_code VARCHAR(50),
            severity_grade INT NOT NULL COMMENT '1-5 per CTCAE',
            severity_category ENUM('Grade 1', 'Grade 2', 'Grade 3', 'Grade 4', 'Grade 5') NOT NULL,
            onset_date DATE NOT NULL,
            resolution_date DATE,
            is_serious BOOLEAN DEFAULT FALSE,
            seriousness_criteria TEXT,
            is_related_to_treatment BOOLEAN DEFAULT TRUE,
            action_taken ENUM('None', 'Dose Reduced', 'Dose Interrupted', 'Dose Discontinued', 
                             'Treatment Discontinued', 'Concomitant Medication') DEFAULT 'None',
            outcome ENUM('Recovered', 'Recovering', 'Not Recovered', 'Recovered with Sequelae', 
                        'Fatal', 'Unknown') DEFAULT 'Unknown',
            site_id INT NOT NULL,
            reported_date DATE COMMENT 'Date AE was reported to sponsor',
            report_latency_days INT COMMENT 'Days between onset and report',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
            FOREIGN KEY (visit_id) REFERENCES visits(visit_id) ON DELETE SET NULL,
            FOREIGN KEY (cycle_id) REFERENCES treatment_cycles(cycle_id) ON DELETE SET NULL,
            FOREIGN KEY (site_id) REFERENCES sites(site_id),
            INDEX idx_patient_id (patient_id),
            INDEX idx_severity_grade (severity_grade),
            INDEX idx_onset_date (onset_date),
            INDEX idx_is_serious (is_serious),
            INDEX idx_report_latency (report_latency_days),
            INDEX idx_site_id (site_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # 8. Lab results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lab_results (
            lab_result_id INT PRIMARY KEY AUTO_INCREMENT,
            patient_id INT NOT NULL,
            visit_id INT,
            cycle_id INT,
            test_date DATE NOT NULL,
            test_name VARCHAR(200) NOT NULL,
            test_category ENUM('Hematology', 'Chemistry', 'Liver Function', 'Renal Function', 
                               'Lipid Panel', 'Coagulation', 'Other') NOT NULL,
            test_value DECIMAL(12,4),
            unit VARCHAR(50),
            reference_range_low DECIMAL(12,4),
            reference_range_high DECIMAL(12,4),
            is_abnormal BOOLEAN DEFAULT FALSE,
            abnormality_flag ENUM('Normal', 'Low', 'High', 'Critical Low', 'Critical High') DEFAULT 'Normal',
            delta_from_baseline DECIMAL(12,4) COMMENT 'Change from baseline value',
            delta_percentage DECIMAL(8,2) COMMENT 'Percentage change from baseline',
            trend_direction ENUM('Improving', 'Stable', 'Worsening', 'Fluctuating') DEFAULT 'Stable',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
            FOREIGN KEY (visit_id) REFERENCES visits(visit_id) ON DELETE SET NULL,
            FOREIGN KEY (cycle_id) REFERENCES treatment_cycles(cycle_id) ON DELETE SET NULL,
            INDEX idx_patient_id (patient_id),
            INDEX idx_test_date (test_date),
            INDEX idx_test_name (test_name),
            INDEX idx_is_abnormal (is_abnormal),
            INDEX idx_delta_percentage (delta_percentage)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # 9. Vitals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vitals (
            vital_id INT PRIMARY KEY AUTO_INCREMENT,
            patient_id INT NOT NULL,
            visit_id INT,
            cycle_id INT,
            measurement_date DATE NOT NULL,
            measurement_time TIME,
            systolic_bp INT,
            diastolic_bp INT,
            heart_rate INT,
            heart_rate_variability DECIMAL(5,2) COMMENT 'HRV in ms',
            temperature_celsius DECIMAL(4,2),
            respiratory_rate INT,
            oxygen_saturation DECIMAL(4,2),
            weight_kg DECIMAL(5,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
            FOREIGN KEY (visit_id) REFERENCES visits(visit_id) ON DELETE SET NULL,
            FOREIGN KEY (cycle_id) REFERENCES treatment_cycles(cycle_id) ON DELETE SET NULL,
            INDEX idx_patient_id (patient_id),
            INDEX idx_measurement_date (measurement_date),
            INDEX idx_heart_rate (heart_rate),
            INDEX idx_heart_rate_variability (heart_rate_variability)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # 10. Physician notes table (for sentiment analysis)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS physician_notes (
            note_id INT PRIMARY KEY AUTO_INCREMENT,
            patient_id INT NOT NULL,
            visit_id INT,
            note_date DATE NOT NULL,
            note_type ENUM('Progress Note', 'Adverse Event Note', 'Treatment Note', 
                          'Discontinuation Note', 'Other') NOT NULL,
            note_text TEXT NOT NULL,
            sentiment_score DECIMAL(4,2) COMMENT '-1.0 to 1.0, negative to positive',
            sentiment_label ENUM('Very Negative', 'Negative', 'Neutral', 'Positive', 'Very Positive') DEFAULT 'Neutral',
            key_findings TEXT,
            concerns_mentioned TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
            FOREIGN KEY (visit_id) REFERENCES visits(visit_id) ON DELETE SET NULL,
            INDEX idx_patient_id (patient_id),
            INDEX idx_note_date (note_date),
            INDEX idx_sentiment_score (sentiment_score),
            FULLTEXT idx_note_text (note_text)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # 11. Behavioral adherence table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS behavioral_adherence (
            adherence_id INT PRIMARY KEY AUTO_INCREMENT,
            patient_id INT NOT NULL,
            cycle_id INT,
            assessment_date DATE NOT NULL,
            medication_adherence_percentage DECIMAL(5,2) DEFAULT 100.0,
            visit_adherence_percentage DECIMAL(5,2) DEFAULT 100.0,
            diary_completion_percentage DECIMAL(5,2) DEFAULT 100.0,
            overall_adherence_score DECIMAL(5,2) COMMENT 'Weighted average, 0-100',
            missed_doses_count INT DEFAULT 0,
            late_doses_count INT DEFAULT 0,
            adherence_pattern ENUM('Excellent', 'Good', 'Fair', 'Poor', 'Very Poor') DEFAULT 'Good',
            risk_factors TEXT COMMENT 'Factors affecting adherence',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
            FOREIGN KEY (cycle_id) REFERENCES treatment_cycles(cycle_id) ON DELETE SET NULL,
            INDEX idx_patient_id (patient_id),
            INDEX idx_assessment_date (assessment_date),
            INDEX idx_overall_adherence_score (overall_adherence_score)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # 12. SAE reconciliation table (for FDA audit)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sae_reconciliation (
            reconciliation_id INT PRIMARY KEY AUTO_INCREMENT,
            site_id INT NOT NULL,
            sae_id INT COMMENT 'Reference to adverse_events where is_serious=TRUE',
            reconciliation_date DATE,
            reconciliation_status ENUM('Pending', 'In Progress', 'Completed', 'Overdue') DEFAULT 'Pending',
            lag_days INT COMMENT 'Days between SAE onset and reconciliation completion',
            documentation_completeness DECIMAL(5,2) COMMENT '0-100, percentage of required docs',
            metadata_completeness DECIMAL(5,2) COMMENT '0-100, percentage of required metadata',
            discrepancies_found TEXT,
            corrective_actions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (site_id) REFERENCES sites(site_id),
            INDEX idx_site_id (site_id),
            INDEX idx_reconciliation_status (reconciliation_status),
            INDEX idx_lag_days (lag_days)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # 13. Documentation metadata table (for FDA audit)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documentation_metadata (
            metadata_id INT PRIMARY KEY AUTO_INCREMENT,
            site_id INT NOT NULL,
            document_type ENUM('CRF', 'Source Document', 'Lab Report', 'AE Report', 
                               'SAE Report', 'Protocol Deviation', 'Other') NOT NULL,
            document_date DATE,
            completeness_score DECIMAL(5,2) COMMENT '0-100',
            timeliness_score DECIMAL(5,2) COMMENT '0-100, based on submission delay',
            quality_score DECIMAL(5,2) COMMENT '0-100',
            missing_fields TEXT,
            inconsistencies TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (site_id) REFERENCES sites(site_id),
            INDEX idx_site_id (site_id),
            INDEX idx_document_type (document_type),
            INDEX idx_completeness_score (completeness_score)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # 14. PK (Pharmacokinetic) data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pk_data (
            pk_id INT PRIMARY KEY AUTO_INCREMENT,
            patient_id INT NOT NULL,
            visit_id INT,
            cycle_id INT,
            sample_date DATE NOT NULL,
            sample_time TIME,
            time_point_hours DECIMAL(6,2) COMMENT 'Hours post-dose',
            concentration DECIMAL(12,4),
            unit VARCHAR(50) DEFAULT 'ng/mL',
            is_linked_to_ae BOOLEAN DEFAULT FALSE,
            linked_ae_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
            FOREIGN KEY (visit_id) REFERENCES visits(visit_id) ON DELETE SET NULL,
            FOREIGN KEY (cycle_id) REFERENCES treatment_cycles(cycle_id) ON DELETE SET NULL,
            FOREIGN KEY (linked_ae_id) REFERENCES adverse_events(ae_id) ON DELETE SET NULL,
            INDEX idx_patient_id (patient_id),
            INDEX idx_sample_date (sample_date),
            INDEX idx_is_linked_to_ae (is_linked_to_ae)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    # 15. FDA audit risk scores table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fda_audit_risk_scores (
            risk_score_id INT PRIMARY KEY AUTO_INCREMENT,
            site_id INT NOT NULL,
            assessment_date DATE NOT NULL,
            overall_risk_score DECIMAL(5,2) COMMENT '0-100, higher = more risk',
            risk_category ENUM('Low', 'Medium', 'High', 'Critical') NOT NULL,
            documentation_latency_score DECIMAL(5,2) COMMENT '0-100, higher = more risk',
            sae_reconciliation_lag_score DECIMAL(5,2) COMMENT '0-100, higher = more risk',
            metadata_completeness_score DECIMAL(5,2) COMMENT '0-100, higher = more risk',
            ae_severity_inconsistencies_count INT DEFAULT 0,
            missing_pk_linkage_count INT DEFAULT 0,
            other_risk_factors TEXT,
            recommendations TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (site_id) REFERENCES sites(site_id),
            INDEX idx_site_id (site_id),
            INDEX idx_assessment_date (assessment_date),
            INDEX idx_overall_risk_score (overall_risk_score),
            INDEX idx_risk_category (risk_category)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    
    print("✅ All tables created successfully")


def generate_dummy_data(cursor, conn) -> None:
    """Generate comprehensive dummy data."""
    
    print(f"\n📝 Generating dummy data for {NUM_PATIENTS} patients across {NUM_SITES} sites...")
    
    # Common data pools
    countries = ['USA', 'Canada', 'UK', 'Germany', 'France', 'Spain', 'Italy', 'Australia']
    regions = ['North', 'South', 'East', 'West', 'Central']
    races = ['White', 'Black or African American', 'Asian', 'Native American', 'Other']
    ethnicities = ['Hispanic or Latino', 'Not Hispanic or Latino']
    conditions = ['Hypertension', 'Diabetes', 'Hyperlipidemia', 'Asthma', 'COPD', 
                  'Arthritis', 'Depression', 'Anxiety', 'Obesity', 'Heart Disease']
    therapies = ['Chemotherapy', 'Immunotherapy', 'Radiation', 'Surgery', 'Hormone Therapy']
    ae_terms = ['Fatigue', 'Nausea', 'Diarrhea', 'Rash', 'Headache', 'Fever', 
                'Neutropenia', 'Thrombocytopenia', 'Anemia', 'ALT Increased', 
                'AST Increased', 'Creatinine Increased', 'Hypertension', 'Hypotension']
    lab_tests = {
        'Hematology': ['WBC', 'RBC', 'Hemoglobin', 'Hematocrit', 'Platelets', 'Neutrophils', 'Lymphocytes'],
        'Liver Function': ['ALT', 'AST', 'Bilirubin', 'Albumin', 'Alkaline Phosphatase'],
        'Renal Function': ['Creatinine', 'BUN', 'eGFR', 'Urea'],
        'Chemistry': ['Glucose', 'Sodium', 'Potassium', 'Calcium', 'Magnesium']
    }
    
    # 1. Create sites
    print("  Creating sites...")
    sites = []
    for i in range(1, NUM_SITES + 1):
        site_code = f"SITE{i:03d}"
        site_name = f"Clinical Research Site {i}"
        country = random.choice(countries)
        region = random.choice(regions)
        pi_name = f"Dr. {random_string(8)}"
        capacity = random.randint(20, 100)
        
        cursor.execute("""
            INSERT INTO sites (site_code, site_name, country, region, principal_investigator, enrollment_capacity)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (site_code, site_name, country, region, pi_name, capacity))
        sites.append(cursor.lastrowid)
    
    conn.commit()
    print(f"  ✅ Created {NUM_SITES} sites")
    
    # 2. Create patients
    print("  Creating patients...")
    patients = []
    enrollment_dates = []
    
    for i in range(1, NUM_PATIENTS + 1):
        patient_number = f"P{i:04d}"
        site_id = random.choice(sites)
        enrollment_date = random_date(STUDY_START_DATE, STUDY_START_DATE + timedelta(days=180))
        enrollment_dates.append(enrollment_date)
        age = random.randint(18, 85)
        gender = random.choice(['M', 'F', 'Other'])
        race = random.choice(races)
        ethnicity = random.choice(ethnicities)
        weight = random.uniform(50, 120)
        height = random.uniform(150, 200)
        bmi = weight / ((height/100) ** 2)
        randomization = random.choice(['Treatment', 'Control', 'Placebo'])
        
        # Status distribution: 60% active, 25% completed, 10% discontinued, 5% screen failed
        status_roll = random.random()
        if status_roll < 0.60:
            status = 'Active'
            disc_reason = None
            disc_date = None
        elif status_roll < 0.85:
            status = 'Completed'
            disc_reason = None
            disc_date = None
        elif status_roll < 0.95:
            status = 'Discontinued'
            disc_reasons = ['Adverse Event', 'Patient Withdrawal', 'Protocol Violation', 
                           'Lost to Follow-up', 'Physician Decision']
            disc_reason = random.choice(disc_reasons)
            disc_date = random_date(enrollment_date + timedelta(days=30), 
                                   enrollment_date + timedelta(days=180))
        else:
            status = 'Screen Failed'
            disc_reason = 'Failed inclusion criteria'
            disc_date = enrollment_date + timedelta(days=random.randint(1, 14))
        
        cursor.execute("""
            INSERT INTO patients (patient_number, site_id, enrollment_date, age, gender, 
                                race, ethnicity, weight_kg, height_cm, bmi, 
                                randomization_group, status, discontinuation_reason, discontinuation_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (patient_number, site_id, enrollment_date, age, gender, race, ethnicity,
              weight, height, bmi, randomization, status, disc_reason, disc_date))
        
        patient_id = cursor.lastrowid
        patients.append((patient_id, enrollment_date, site_id, status))
    
    conn.commit()
    print(f"  ✅ Created {NUM_PATIENTS} patients")
    
    # 3. Create comorbidities
    print("  Creating comorbidities...")
    comorbidity_count = 0
    for patient_id, _, _, _ in patients:
        num_comorbidities = random.choices([0, 1, 2, 3, 4], weights=[20, 30, 30, 15, 5])[0]
        for _ in range(num_comorbidities):
            condition = random.choice(conditions)
            severity = random.choice(['Mild', 'Moderate', 'Severe'])
            onset_date = random_date(STUDY_START_DATE - timedelta(days=365*5), STUDY_START_DATE)
            is_controlled = random.choice([True, True, True, False])  # 75% controlled
            medication = f"Medication {random_string(6)}" if is_controlled else None
            
            cursor.execute("""
                INSERT INTO comorbidities (patient_id, condition_name, severity, 
                                         onset_date, is_controlled, medication)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (patient_id, condition, severity, onset_date, is_controlled, medication))
            comorbidity_count += 1
    
    conn.commit()
    print(f"  ✅ Created {comorbidity_count} comorbidities")
    
    # 4. Create prior therapies
    print("  Creating prior therapies...")
    prior_therapy_count = 0
    for patient_id, enrollment_date, _, _ in patients:
        num_therapies = random.choices([0, 1, 2, 3], weights=[30, 40, 25, 5])[0]
        for _ in range(num_therapies):
            therapy_name = random.choice(therapies)
            therapy_type = therapy_name
            start_date = random_date(enrollment_date - timedelta(days=365*3), enrollment_date - timedelta(days=30))
            end_date = random_date(start_date + timedelta(days=30), enrollment_date - timedelta(days=1))
            response = random.choice(['Complete Response', 'Partial Response', 'Stable Disease', 
                                    'Progressive Disease', 'Not Evaluable'])
            tolerance_score = random.randint(1, 10)
            ae_count = random.randint(0, 5) if tolerance_score < 7 else random.randint(0, 2)
            
            cursor.execute("""
                INSERT INTO prior_therapies (patient_id, therapy_name, therapy_type, 
                                           start_date, end_date, response, tolerance_score, adverse_events_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (patient_id, therapy_name, therapy_type, start_date, end_date, 
                  response, tolerance_score, ae_count))
            prior_therapy_count += 1
    
    conn.commit()
    print(f"  ✅ Created {prior_therapy_count} prior therapies")
    
    # 5. Create treatment cycles
    print("  Creating treatment cycles...")
    cycle_count = 0
    cycles_by_patient = {}
    
    for patient_id, enrollment_date, _, status in patients:
        if status in ['Screen Failed', 'Discontinued']:
            continue
        
        num_cycles = random.randint(1, NUM_TREATMENT_CYCLES)
        cycles_by_patient[patient_id] = []
        
        for cycle_num in range(1, num_cycles + 1):
            planned_start = enrollment_date + timedelta(days=(cycle_num - 1) * DAYS_PER_CYCLE)
            actual_start_offset = random.randint(-2, 5)  # Some delays
            actual_start = planned_start + timedelta(days=actual_start_offset)
            planned_end = planned_start + timedelta(days=DAYS_PER_CYCLE - 1)
            
            if cycle_num < num_cycles:
                actual_end = actual_start + timedelta(days=DAYS_PER_CYCLE - 1)
                cycle_status = 'Completed'
            else:
                if status == 'Active':
                    cycle_status = 'In Progress'
                    actual_end = None
                else:
                    actual_end = actual_start + timedelta(days=random.randint(1, DAYS_PER_CYCLE - 1))
                    cycle_status = 'Completed'
            
            dose_planned = random.uniform(100, 500)
            dose_received = dose_planned * random.uniform(0.85, 1.0)  # Some dose reductions
            dose_reduction = None if dose_received >= dose_planned * 0.95 else "Toxicity"
            adherence = random.uniform(80, 100)
            
            cursor.execute("""
                INSERT INTO treatment_cycles (patient_id, cycle_number, planned_start_date, 
                                             actual_start_date, planned_end_date, actual_end_date,
                                             status, dose_received, dose_planned, 
                                             dose_reduction_reason, adherence_percentage)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (patient_id, cycle_num, planned_start, actual_start, planned_end, actual_end,
                  cycle_status, dose_received, dose_planned, dose_reduction, adherence))
            
            cycle_id = cursor.lastrowid
            cycles_by_patient[patient_id].append((cycle_id, cycle_num, actual_start, actual_end))
            cycle_count += 1
    
    conn.commit()
    print(f"  ✅ Created {cycle_count} treatment cycles")
    
    # 6. Create visits
    print("  Creating visits...")
    visit_count = 0
    visits_by_patient = {}
    
    for patient_id, enrollment_date, site_id, status in patients:
        if status == 'Screen Failed':
            continue
        
        patient_visits = []
        
        # Screening visit
        screen_date = enrollment_date - timedelta(days=random.randint(7, 21))
        punctuality = random.uniform(-2, 2)
        cursor.execute("""
            INSERT INTO visits (patient_id, visit_number, visit_type, planned_date, actual_date,
                              punctuality_hours, visit_status, site_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (patient_id, 1, 'Screening', screen_date, screen_date + timedelta(hours=punctuality),
              punctuality, 'Completed', site_id))
        visit_id = cursor.lastrowid
        patient_visits.append(visit_id)
        visit_count += 1
        
        # Baseline
        baseline_date = enrollment_date
        punctuality = random.uniform(-1, 3)
        cursor.execute("""
            INSERT INTO visits (patient_id, visit_number, visit_type, planned_date, actual_date,
                              punctuality_hours, visit_status, site_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (patient_id, 2, 'Baseline', baseline_date, baseline_date + timedelta(hours=punctuality),
              punctuality, 'Completed', site_id))
        visit_id = cursor.lastrowid
        patient_visits.append(visit_id)
        visit_count += 1
        
        # Cycle visits
        if patient_id in cycles_by_patient:
            visit_num = 3
            for cycle_id, cycle_num, cycle_start, cycle_end in cycles_by_patient[patient_id]:
                # Cycle start visit
                visit_date = cycle_start
                punctuality = random.uniform(-2, 4)
                cursor.execute("""
                    INSERT INTO visits (patient_id, cycle_id, visit_number, visit_type, 
                                      planned_date, actual_date, punctuality_hours, visit_status, site_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (patient_id, cycle_id, visit_num, 'Cycle Visit', visit_date,
                      visit_date + timedelta(hours=punctuality), punctuality, 'Completed', site_id))
                visit_id = cursor.lastrowid
                patient_visits.append(visit_id)
                visit_count += 1
                visit_num += 1
                
                # Mid-cycle visit (if cycle completed)
                if cycle_end:
                    mid_date = cycle_start + timedelta(days=DAYS_PER_CYCLE // 2)
                    punctuality = random.uniform(-3, 5)
                    cursor.execute("""
                        INSERT INTO visits (patient_id, cycle_id, visit_number, visit_type,
                                          planned_date, actual_date, punctuality_hours, visit_status, site_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (patient_id, cycle_id, visit_num, 'Cycle Visit', mid_date,
                          mid_date + timedelta(hours=punctuality), punctuality, 'Completed', site_id))
                    visit_id = cursor.lastrowid
                    patient_visits.append(visit_id)
                    visit_count += 1
                    visit_num += 1
        
        # Calculate punctuality variance for patient
        if len(patient_visits) > 1:
            cursor.execute("""
                SELECT AVG(punctuality_hours), STDDEV(punctuality_hours)
                FROM visits WHERE patient_id = %s
            """, (patient_id,))
            result = cursor.fetchone()
            if result and result[1]:
                variance = float(result[1]) ** 2
                cursor.execute("""
                    UPDATE visits SET punctuality_variance = %s WHERE patient_id = %s
                """, (variance, patient_id))
        
        visits_by_patient[patient_id] = patient_visits
    
    conn.commit()
    print(f"  ✅ Created {visit_count} visits")
    
    # 7. Create adverse events
    print("  Creating adverse events...")
    ae_count = 0
    ae_by_patient = {}
    
    for patient_id, enrollment_date, site_id, status in patients:
        if status == 'Screen Failed':
            continue
        
        patient_aes = []
        num_aes = random.choices([0, 1, 2, 3, 4, 5], weights=[20, 25, 25, 15, 10, 5])[0]
        
        for _ in range(num_aes):
            visit_id = random.choice(visits_by_patient.get(patient_id, [None]))
            cycle_id = None
            if patient_id in cycles_by_patient and cycles_by_patient[patient_id]:
                cycle_id = random.choice(cycles_by_patient[patient_id])[0]
            
            ae_term = random.choice(ae_terms)
            meddra_code = f"100{random.randint(10000, 99999)}"
            severity_grade = random.choices([1, 2, 3, 4, 5], weights=[40, 30, 20, 8, 2])[0]
            severity_category = f"Grade {severity_grade}"
            
            onset_date = random_date(enrollment_date, enrollment_date + timedelta(days=180))
            resolution_date = None
            if random.random() < 0.7:  # 70% resolved
                resolution_date = random_date(onset_date, onset_date + timedelta(days=30))
            
            is_serious = severity_grade >= 3 and random.random() < 0.3
            seriousness_criteria = "Death" if severity_grade == 5 else ("Life-threatening" if severity_grade == 4 else None)
            
            is_related = random.choice([True, True, True, False])  # 75% related
            action = random.choice(['None', 'Dose Reduced', 'Dose Interrupted', 'Dose Discontinued'])
            outcome = random.choice(['Recovered', 'Recovering', 'Not Recovered', 'Recovered with Sequelae'])
            
            reported_date = onset_date + timedelta(days=random.randint(0, 7))
            report_latency = (reported_date - onset_date).days
            
            cursor.execute("""
                INSERT INTO adverse_events (patient_id, visit_id, cycle_id, ae_term, meddra_code,
                                          severity_grade, severity_category, onset_date, resolution_date,
                                          is_serious, seriousness_criteria, is_related_to_treatment,
                                          action_taken, outcome, site_id, reported_date, report_latency_days)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (patient_id, visit_id, cycle_id, ae_term, meddra_code, severity_grade, 
                  severity_category, onset_date, resolution_date, is_serious, seriousness_criteria,
                  is_related, action, outcome, site_id, reported_date, report_latency))
            
            ae_id = cursor.lastrowid
            patient_aes.append(ae_id)
            ae_count += 1
        
        ae_by_patient[patient_id] = patient_aes
    
    conn.commit()
    print(f"  ✅ Created {ae_count} adverse events")
    
    # 8. Create lab results
    print("  Creating lab results...")
    lab_count = 0
    baseline_labs = {}  # Store baseline for delta calculations
    
    for patient_id, enrollment_date, _, status in patients:
        if status == 'Screen Failed':
            continue
        
        patient_visits_list = visits_by_patient.get(patient_id, [])
        
        # Create baseline labs
        baseline_date = enrollment_date
        for category, tests in lab_tests.items():
            for test_name in tests:
                # Generate realistic baseline values
                if test_name == 'ALT':
                    baseline_value = random.uniform(10, 40)
                    ref_low, ref_high = 7, 56
                elif test_name == 'AST':
                    baseline_value = random.uniform(10, 40)
                    ref_low, ref_high = 10, 40
                elif test_name == 'Creatinine':
                    baseline_value = random.uniform(0.6, 1.2)
                    ref_low, ref_high = 0.6, 1.2
                elif test_name == 'Hemoglobin':
                    baseline_value = random.uniform(12, 16)
                    ref_low, ref_high = 12, 16
                elif test_name == 'WBC':
                    baseline_value = random.uniform(4, 11)
                    ref_low, ref_high = 4, 11
                else:
                    baseline_value = random.uniform(50, 150)
                    ref_low, ref_high = 50, 150
                
                baseline_labs[(patient_id, test_name)] = baseline_value
                
                cursor.execute("""
                    INSERT INTO lab_results (patient_id, visit_id, test_date, test_name, test_category,
                                           test_value, unit, reference_range_low, reference_range_high,
                                           is_abnormal, abnormality_flag, delta_from_baseline, delta_percentage)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (patient_id, patient_visits_list[1] if len(patient_visits_list) > 1 else None,
                      baseline_date, test_name, category, baseline_value, 'standard',
                      ref_low, ref_high, False, 'Normal', 0, 0))
                lab_count += 1
        
        # Create follow-up labs
        if patient_id in cycles_by_patient:
            for cycle_id, cycle_num, cycle_start, cycle_end in cycles_by_patient[patient_id]:
                visit_id = None
                for vid in patient_visits_list:
                    cursor.execute("SELECT cycle_id FROM visits WHERE visit_id = %s", (vid,))
                    result = cursor.fetchone()
                    if result and result[0] == cycle_id:
                        visit_id = vid
                        break
                
                test_date = cycle_start + timedelta(days=random.randint(7, 14))
                
                # Select subset of tests per visit
                tests_to_run = random.sample(
                    [t for tests in lab_tests.values() for t in tests],
                    k=random.randint(5, 10)
                )
                
                for test_name in tests_to_run:
                    baseline = baseline_labs.get((patient_id, test_name), 50)
                    
                    # Simulate changes over time (some drift, some spikes)
                    if random.random() < 0.2:  # 20% chance of significant change
                        delta_pct = random.uniform(-50, 100)
                    else:
                        delta_pct = random.uniform(-10, 10)
                    
                    current_value = baseline * (1 + delta_pct / 100)
                    
                    # Determine abnormality
                    ref_low = baseline * 0.8
                    ref_high = baseline * 1.2
                    is_abnormal = current_value < ref_low or current_value > ref_high
                    flag = 'Normal'
                    if is_abnormal:
                        if current_value < ref_low * 0.7:
                            flag = 'Critical Low'
                        elif current_value > ref_high * 1.3:
                            flag = 'Critical High'
                        elif current_value < ref_low:
                            flag = 'Low'
                        else:
                            flag = 'High'
                    
                    delta_from_baseline = current_value - baseline
                    trend = 'Worsening' if abs(delta_pct) > 15 else ('Improving' if delta_pct < -5 else 'Stable')
                    
                    cursor.execute("""
                        INSERT INTO lab_results (patient_id, visit_id, cycle_id, test_date, test_name, test_category,
                                               test_value, unit, reference_range_low, reference_range_high,
                                               is_abnormal, abnormality_flag, delta_from_baseline, delta_percentage, trend_direction)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (patient_id, visit_id, cycle_id, test_date, test_name,
                          next(cat for cat, tests in lab_tests.items() if test_name in tests),
                          current_value, 'standard', ref_low, ref_high, is_abnormal, flag,
                          delta_from_baseline, delta_pct, trend))
                    lab_count += 1
    
    conn.commit()
    print(f"  ✅ Created {lab_count} lab results")
    
    # 9. Create vitals
    print("  Creating vitals...")
    vital_count = 0
    
    for patient_id, enrollment_date, _, status in patients:
        if status == 'Screen Failed':
            continue
        
        patient_visits_list = visits_by_patient.get(patient_id, [])
        
        for visit_id in patient_visits_list:
            cursor.execute("SELECT actual_date FROM visits WHERE visit_id = %s", (visit_id,))
            result = cursor.fetchone()
            if not result or not result[0]:
                continue
            
            measurement_date = result[0]
            measurement_time = datetime.combine(measurement_date, datetime.min.time()).time()
            
            systolic = random.randint(100, 160)
            diastolic = random.randint(60, 100)
            heart_rate = random.randint(60, 100)
            hrv = random.uniform(20, 60)  # Heart rate variability
            temperature = random.uniform(36.0, 37.5)
            respiratory = random.randint(12, 20)
            oxygen = random.uniform(95, 100)
            weight = random.uniform(50, 120)
            
            cursor.execute("""
                INSERT INTO vitals (patient_id, visit_id, measurement_date, measurement_time,
                                  systolic_bp, diastolic_bp, heart_rate, heart_rate_variability,
                                  temperature_celsius, respiratory_rate, oxygen_saturation, weight_kg)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (patient_id, visit_id, measurement_date, measurement_time,
                  systolic, diastolic, heart_rate, hrv, temperature, respiratory, oxygen, weight))
            vital_count += 1
    
    conn.commit()
    print(f"  ✅ Created {vital_count} vital measurements")
    
    # 10. Create physician notes
    print("  Creating physician notes...")
    note_count = 0
    
    note_templates = [
        "Patient reports {symptom}. Vital signs stable. Continue current treatment.",
        "Patient doing well. No new concerns. Treatment tolerance good.",
        "Patient experiencing {symptom}. Monitoring closely. May need dose adjustment.",
        "Significant improvement noted. Patient responding well to treatment.",
        "Patient reports increased fatigue. Lab values within normal limits.",
        "Concern about {symptom}. Will monitor and consider intervention if needed.",
        "Patient stable. No adverse events. Treatment progressing as planned.",
        "Noted {symptom} during visit. Discussed with patient. Will follow up."
    ]
    
    symptoms = ['mild fatigue', 'nausea', 'headache', 'rash', 'dizziness', 'joint pain']
    
    for patient_id, enrollment_date, _, status in patients:
        if status == 'Screen Failed':
            continue
        
        patient_visits_list = visits_by_patient.get(patient_id, [])
        num_notes = random.randint(2, len(patient_visits_list))
        
        for _ in range(num_notes):
            visit_id = random.choice(patient_visits_list)
            cursor.execute("SELECT actual_date FROM visits WHERE visit_id = %s", (visit_id,))
            result = cursor.fetchone()
            if not result or not result[0]:
                continue
            
            note_date = result[0]
            note_type = random.choice(['Progress Note', 'Adverse Event Note', 'Treatment Note'])
            
            template = random.choice(note_templates)
            symptom = random.choice(symptoms)
            note_text = template.format(symptom=symptom)
            
            # Generate sentiment score (-1 to 1)
            if 'well' in note_text.lower() or 'improvement' in note_text.lower() or 'stable' in note_text.lower():
                sentiment = random.uniform(0.3, 1.0)
                sentiment_label = random.choice(['Positive', 'Very Positive'])
            elif 'concern' in note_text.lower() or 'monitoring' in note_text.lower():
                sentiment = random.uniform(-0.5, 0.2)
                sentiment_label = random.choice(['Neutral', 'Negative'])
            else:
                sentiment = random.uniform(-0.2, 0.3)
                sentiment_label = 'Neutral'
            
            key_findings = random.choice(['Stable condition', 'Mild symptoms', 'Good tolerance', 'No concerns'])
            concerns = random.choice([None, 'Monitor closely', 'Consider dose adjustment'])
            
            cursor.execute("""
                INSERT INTO physician_notes (patient_id, visit_id, note_date, note_type, note_text,
                                            sentiment_score, sentiment_label, key_findings, concerns_mentioned)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (patient_id, visit_id, note_date, note_type, note_text,
                  sentiment, sentiment_label, key_findings, concerns))
            note_count += 1
    
    conn.commit()
    print(f"  ✅ Created {note_count} physician notes")
    
    # 11. Create behavioral adherence
    print("  Creating behavioral adherence records...")
    adherence_count = 0
    
    for patient_id, enrollment_date, _, status in patients:
        if status in ['Screen Failed', 'Discontinued']:
            continue
        
        if patient_id not in cycles_by_patient:
            continue
        
        for cycle_id, cycle_num, cycle_start, cycle_end in cycles_by_patient[patient_id]:
            assessment_date = cycle_start + timedelta(days=random.randint(7, 14))
            
            med_adherence = random.uniform(70, 100)
            visit_adherence = random.uniform(80, 100)
            diary_completion = random.uniform(60, 100)
            overall_score = (med_adherence * 0.5 + visit_adherence * 0.3 + diary_completion * 0.2)
            
            missed_doses = random.randint(0, 5) if med_adherence < 90 else random.randint(0, 2)
            late_doses = random.randint(0, 3) if med_adherence < 95 else random.randint(0, 1)
            
            if overall_score >= 95:
                pattern = 'Excellent'
            elif overall_score >= 85:
                pattern = 'Good'
            elif overall_score >= 75:
                pattern = 'Fair'
            elif overall_score >= 60:
                pattern = 'Poor'
            else:
                pattern = 'Very Poor'
            
            risk_factors = random.choice([None, 'Busy schedule', 'Forgetfulness', 'Side effects'])
            
            cursor.execute("""
                INSERT INTO behavioral_adherence (patient_id, cycle_id, assessment_date,
                                                medication_adherence_percentage, visit_adherence_percentage,
                                                diary_completion_percentage, overall_adherence_score,
                                                missed_doses_count, late_doses_count, adherence_pattern, risk_factors)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (patient_id, cycle_id, assessment_date, med_adherence, visit_adherence,
                  diary_completion, overall_score, missed_doses, late_doses, pattern, risk_factors))
            adherence_count += 1
    
    conn.commit()
    print(f"  ✅ Created {adherence_count} adherence records")
    
    # 12. Create SAE reconciliation
    print("  Creating SAE reconciliation records...")
    sae_recon_count = 0
    
    # Get all serious AEs
    cursor.execute("""
        SELECT ae_id, patient_id, site_id, onset_date, reported_date
        FROM adverse_events
        WHERE is_serious = TRUE
    """)
    serious_aes = cursor.fetchall()
    
    for ae_id, patient_id, site_id, onset_date, reported_date in serious_aes:
        reconciliation_date = reported_date + timedelta(days=random.randint(1, 14))
        lag_days = (reconciliation_date - onset_date).days
        
        status_roll = random.random()
        if status_roll < 0.6:
            recon_status = 'Completed'
        elif status_roll < 0.8:
            recon_status = 'In Progress'
        elif status_roll < 0.95:
            recon_status = 'Pending'
        else:
            recon_status = 'Overdue'
        
        doc_completeness = random.uniform(60, 100) if recon_status == 'Completed' else random.uniform(30, 80)
        metadata_completeness = random.uniform(70, 100) if recon_status == 'Completed' else random.uniform(40, 85)
        
        discrepancies = random.choice([None, 'Date mismatch', 'Severity discrepancy', 'Missing information'])
        corrective_actions = random.choice([None, 'Site training', 'Data correction', 'Protocol review'])
        
        cursor.execute("""
            INSERT INTO sae_reconciliation (site_id, sae_id, reconciliation_date, reconciliation_status,
                                          lag_days, documentation_completeness, metadata_completeness,
                                          discrepancies_found, corrective_actions)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (site_id, ae_id, reconciliation_date, recon_status, lag_days,
              doc_completeness, metadata_completeness, discrepancies, corrective_actions))
        sae_recon_count += 1
    
    conn.commit()
    print(f"  ✅ Created {sae_recon_count} SAE reconciliation records")
    
    # 13. Create documentation metadata
    print("  Creating documentation metadata...")
    doc_meta_count = 0
    
    for site_id in sites:
        num_docs = random.randint(50, 200)
        for _ in range(num_docs):
            doc_type = random.choice(['CRF', 'Source Document', 'Lab Report', 'AE Report', 'SAE Report'])
            doc_date = random_date(STUDY_START_DATE, datetime.now())
            completeness = random.uniform(70, 100)
            timeliness = random.uniform(60, 100)
            quality = random.uniform(75, 100)
            
            missing_fields = random.choice([None, 'Signature', 'Date', 'Investigator name'])
            inconsistencies = random.choice([None, 'Date mismatch', 'Value discrepancy'])
            
            cursor.execute("""
                INSERT INTO documentation_metadata (site_id, document_type, document_date,
                                                   completeness_score, timeliness_score, quality_score,
                                                   missing_fields, inconsistencies)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (site_id, doc_type, doc_date, completeness, timeliness, quality,
                  missing_fields, inconsistencies))
            doc_meta_count += 1
    
    conn.commit()
    print(f"  ✅ Created {doc_meta_count} documentation metadata records")
    
    # 14. Create PK data
    print("  Creating PK data...")
    pk_count = 0
    
    for patient_id, enrollment_date, _, status in patients:
        if status in ['Screen Failed', 'Discontinued']:
            continue
        
        if patient_id not in cycles_by_patient:
            continue
        
        # Create PK samples for some cycles
        for cycle_id, cycle_num, cycle_start, cycle_end in random.sample(
            cycles_by_patient[patient_id],
            k=min(3, len(cycles_by_patient[patient_id]))
        ):
            # Multiple time points per cycle
            time_points = [0, 2, 4, 8, 24, 48]  # Hours post-dose
            num_samples = random.randint(3, 6)
            selected_time_points = random.sample(time_points, k=num_samples)
            
            for time_point in sorted(selected_time_points):
                sample_date = cycle_start + timedelta(hours=time_point)
                sample_time = datetime.combine(sample_date, datetime.min.time()).time()
                
                # Simulate PK concentration curve
                concentration = random.uniform(10, 500) * (1 / (1 + time_point / 4))  # Decay curve
                
                visit_id = None
                for vid in visits_by_patient.get(patient_id, []):
                    cursor.execute("SELECT cycle_id FROM visits WHERE visit_id = %s", (vid,))
                    result = cursor.fetchone()
                    if result and result[0] == cycle_id:
                        visit_id = vid
                        break
                
                is_linked = random.random() < 0.1  # 10% linked to AE
                linked_ae_id = None
                if is_linked and patient_id in ae_by_patient and ae_by_patient[patient_id]:
                    linked_ae_id = random.choice(ae_by_patient[patient_id])
                
                cursor.execute("""
                    INSERT INTO pk_data (patient_id, visit_id, cycle_id, sample_date, sample_time,
                                       time_point_hours, concentration, unit, is_linked_to_ae, linked_ae_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (patient_id, visit_id, cycle_id, sample_date, sample_time,
                      time_point, concentration, 'ng/mL', is_linked, linked_ae_id))
                pk_count += 1
    
    conn.commit()
    print(f"  ✅ Created {pk_count} PK data points")
    
    # 15. Create FDA audit risk scores
    print("  Creating FDA audit risk scores...")
    risk_score_count = 0
    
    for site_id in sites:
        # Create monthly risk assessments
        current_date = STUDY_START_DATE
        while current_date < datetime.now():
            assessment_date = current_date
            
            # Calculate risk components
            cursor.execute("""
                SELECT AVG(lag_days), AVG(documentation_completeness), AVG(metadata_completeness)
                FROM sae_reconciliation
                WHERE site_id = %s AND reconciliation_date <= %s
            """, (site_id, assessment_date))
            sae_result = cursor.fetchone()
            
            cursor.execute("""
                SELECT AVG(timeliness_score), AVG(completeness_score)
                FROM documentation_metadata
                WHERE site_id = %s AND document_date <= %s
            """, (site_id, assessment_date))
            doc_result = cursor.fetchone()
            
            # Calculate scores (inverse - higher lag = higher risk)
            doc_latency_score = 100 - (doc_result[0] if doc_result and doc_result[0] else 50)
            sae_lag_score = min(100, (sae_result[0] if sae_result and sae_result[0] else 0) * 2)
            metadata_score = 100 - (sae_result[2] if sae_result and sae_result[2] else 50)
            
            # Count inconsistencies
            cursor.execute("""
                SELECT COUNT(*) FROM adverse_events ae1
                JOIN adverse_events ae2 ON ae1.patient_id = ae2.patient_id
                WHERE ae1.site_id = %s AND ae1.ae_id != ae2.ae_id
                AND ae1.ae_term = ae2.ae_term
                AND ABS(ae1.severity_grade - ae2.severity_grade) >= 2
            """, (site_id,))
            inconsistency_count = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                SELECT COUNT(*) FROM pk_data pk
                JOIN patients p ON pk.patient_id = p.patient_id
                JOIN adverse_events ae ON pk.patient_id = ae.patient_id
                WHERE p.site_id = %s AND pk.is_linked_to_ae = FALSE
                AND pk.sample_date BETWEEN ae.onset_date AND DATE_ADD(ae.onset_date, INTERVAL 7 DAY)
            """, (site_id,))
            missing_pk_count = cursor.fetchone()[0] or 0
            
            # Overall risk score (weighted average)
            overall_risk = (
                doc_latency_score * 0.3 +
                sae_lag_score * 0.3 +
                metadata_score * 0.2 +
                min(100, inconsistency_count * 10) * 0.1 +
                min(100, missing_pk_count * 5) * 0.1
            )
            
            if overall_risk < 30:
                risk_category = 'Low'
            elif overall_risk < 60:
                risk_category = 'Medium'
            elif overall_risk < 80:
                risk_category = 'High'
            else:
                risk_category = 'Critical'
            
            recommendations = random.choice([
                'Continue monitoring',
                'Site training recommended',
                'Enhanced oversight required',
                'Immediate corrective action needed'
            ])
            
            cursor.execute("""
                INSERT INTO fda_audit_risk_scores (site_id, assessment_date, overall_risk_score, risk_category,
                                                  documentation_latency_score, sae_reconciliation_lag_score,
                                                  metadata_completeness_score, ae_severity_inconsistencies_count,
                                                  missing_pk_linkage_count, recommendations)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (site_id, assessment_date, overall_risk, risk_category,
                  doc_latency_score, sae_lag_score, metadata_score,
                  inconsistency_count, missing_pk_count, recommendations))
            risk_score_count += 1
            
            current_date += timedelta(days=30)  # Monthly assessments
    
    conn.commit()
    print(f"  ✅ Created {risk_score_count} FDA audit risk scores")
    
    print(f"\n✅ Data generation complete!")
    print(f"\n📊 Summary:")
    print(f"   - {NUM_SITES} sites")
    print(f"   - {NUM_PATIENTS} patients")
    print(f"   - {comorbidity_count} comorbidities")
    print(f"   - {prior_therapy_count} prior therapies")
    print(f"   - {cycle_count} treatment cycles")
    print(f"   - {visit_count} visits")
    print(f"   - {ae_count} adverse events")
    print(f"   - {lab_count} lab results")
    print(f"   - {vital_count} vital measurements")
    print(f"   - {note_count} physician notes")
    print(f"   - {adherence_count} adherence records")
    print(f"   - {sae_recon_count} SAE reconciliations")
    print(f"   - {doc_meta_count} documentation records")
    print(f"   - {pk_count} PK data points")
    print(f"   - {risk_score_count} risk assessments")


def main():
    """Main function."""
    print("=" * 60)
    print("CoTrial RAG - Dummy Clinical Trial Data Generator")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Drop existing tables if needed (uncomment to reset)
        # print("\n⚠️  Dropping existing tables...")
        # cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        # tables = ['fda_audit_risk_scores', 'pk_data', 'documentation_metadata', 'sae_reconciliation',
        #           'behavioral_adherence', 'physician_notes', 'vitals', 'lab_results', 'adverse_events',
        #           'visits', 'treatment_cycles', 'prior_therapies', 'comorbidities', 'patients', 'sites']
        # for table in tables:
        #     cursor.execute(f"DROP TABLE IF EXISTS {table}")
        # cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        # conn.commit()
        
        create_tables(cursor, conn)
        generate_dummy_data(cursor, conn)
        
        cursor.close()
        conn.close()
        
        print("\n✅ All done!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

