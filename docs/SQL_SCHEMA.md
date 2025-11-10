# SQL Schema Documentation

This document describes the MySQL database schema for the H3E-US-S130 clinical trial data.

## Overview

The database contains 16 tables representing different aspects of the clinical trial:
- **Patient/Subject Information**: Demographics, baseline characteristics
- **Safety Data**: Adverse events, vital signs
- **Efficacy Data**: Lesions, best overall response, time-to-event
- **Treatment Data**: Study treatment, concomitant medications
- **Administrative Data**: Visits, disposition, exposure summaries

## Table Descriptions

### subjinfo
**Purpose**: Patient demographics and baseline information  
**Rows**: ~179 (one per patient)  
**Key Columns**:
- `subjid` (BIGINT, PRIMARY KEY): Subject ID - Primary identifier
- `usubjid` (VARCHAR): Unique Subject ID - Study-wide unique identifier
- `ageyr` (DOUBLE): Age in years
- `sex` (DOUBLE): Sex (1=Male, 2=Female)
- `race` (DOUBLE): Race code
- `ethnic` (DOUBLE): Ethnicity code
- `country` (VARCHAR): Country
- `trt` (VARCHAR): Treatment arm
- `trtsort` (DOUBLE): Treatment sort order
- `birthdt` (DATETIME): Birth date
- `enterdt` (DATETIME): Study entry date

**Indexes**: subjid, usubjid, trt, ageyr, sex, race

**Common Queries**:
```sql
-- Get all patients
SELECT * FROM subjinfo;

-- Get patients by treatment arm
SELECT * FROM subjinfo WHERE trt = 'Arm A';

-- Get patient demographics
SELECT subjid, ageyr, sex, race, trt FROM subjinfo;
```

### events
**Purpose**: Adverse events and safety monitoring  
**Rows**: ~25,522 (multiple per patient)  
**Key Columns**:
- `subjid` (BIGINT): Subject ID (indexed)
- `aeid` (DOUBLE): Adverse event ID
- `aeseqid` (DOUBLE): Event sequence ID
- `aeterm` (VARCHAR): Event term/name
- `aestdt` (DATETIME): Event start date (indexed)
- `aeendt` (DATETIME): Event end date
- `aesevvis` (DOUBLE): Severity at visit
- `saeasflg` (DOUBLE): Serious adverse event flag
- `aectc` (DOUBLE): CTC grade
- `aectcgrd` (DOUBLE): CTC grade code

**Indexes**: subjid, aeid, aeseqid, aestdt, aeterm, aectc

**Common Queries**:
```sql
-- Get all adverse events for a patient
SELECT * FROM events WHERE subjid = 1001;

-- Get serious adverse events
SELECT * FROM events WHERE saeasflg = 1;

-- Get events by severity
SELECT * FROM events WHERE aectc >= 3;

-- Count events by patient
SELECT subjid, COUNT(*) as event_count FROM events GROUP BY subjid;
```

### lesions
**Purpose**: Tumor lesion measurements and assessments  
**Rows**: ~4,068 (multiple per patient/lesion)  
**Key Columns**:
- `subjid` (BIGINT): Subject ID (indexed)
- `lsid` (DOUBLE): Lesion ID
- `lsname` (VARCHAR): Lesion name
- `lsasmdt` (DATETIME): Assessment date (indexed)
- `lsloc` (DOUBLE): Lesion location code
- `lsrn` (DOUBLE): Lesion response number
- `lsresprn` (DOUBLE): Response number
- `lsresptp` (DOUBLE): Response type

**Indexes**: subjid, lsid, lsasmdt, lsname

**Common Queries**:
```sql
-- Get all lesions for a patient
SELECT * FROM lesions WHERE subjid = 1001;

-- Get lesion assessments by date
SELECT * FROM lesions WHERE subjid = 1001 ORDER BY lsasmdt;

-- Get target lesions
SELECT * FROM lesions WHERE bltrgflg = 1;
```

### visit
**Purpose**: Visit schedules and compliance  
**Rows**: ~1,938 (multiple per patient)  
**Key Columns**:
- `subjid` (BIGINT): Subject ID (indexed)
- `visfwdid` (DOUBLE): Visit forward ID
- `visdt` (DATETIME): Visit date (indexed)
- `visendt` (DATETIME): Visit end date
- `vistp` (DOUBLE): Visit type
- `visdesc` (VARCHAR): Visit description
- `phase` (VARCHAR): Study phase

**Indexes**: subjid, visfwdid, visdt

**Common Queries**:
```sql
-- Get all visits for a patient
SELECT * FROM visit WHERE subjid = 1001 ORDER BY visdt;

-- Get visits in date range
SELECT * FROM visit WHERE visdt BETWEEN '2020-01-01' AND '2020-12-31';
```

### vitals
**Purpose**: Vital signs measurements  
**Rows**: ~7,420 (multiple per patient/visit)  
**Key Columns**:
- `subjid` (BIGINT): Subject ID (indexed)
- `visfwdid` (DOUBLE): Visit ID (indexed)
- `vstestcd` (VARCHAR): Test code (indexed)
- `vstest` (VARCHAR): Test name
- `vsrn` (DOUBLE): Result number
- `vsru` (DOUBLE): Result unit

**Indexes**: subjid, visfwdid, vstestcd

**Common Queries**:
```sql
-- Get vital signs for a patient
SELECT * FROM vitals WHERE subjid = 1001;

-- Get specific vital sign (e.g., blood pressure)
SELECT * FROM vitals WHERE subjid = 1001 AND vstestcd = 'SYSBP';
```

### cmtpy
**Purpose**: Concomitant medications  
**Rows**: ~24,335 (multiple per patient)  
**Key Columns**:
- `subjid` (BIGINT): Subject ID (indexed)
- `cmid` (DOUBLE): Medication ID
- `cmterm` (VARCHAR): Medication term/name
- `cmname` (VARCHAR): Medication name
- `cmstdt` (DATETIME): Start date
- `cmendt` (DATETIME): End date

**Indexes**: subjid, cmid, cmterm

**Common Queries**:
```sql
-- Get medications for a patient
SELECT * FROM cmtpy WHERE subjid = 1001;

-- Get active medications
SELECT * FROM cmtpy WHERE subjid = 1001 AND cmendt IS NULL;
```

### sdytrt
**Purpose**: Study treatment administration  
**Rows**: ~2,786 (multiple per patient)  
**Key Columns**:
- `subjid` (BIGINT): Subject ID (indexed)
- `sdytrtid` (DOUBLE): Treatment ID
- `sdytrtname` (VARCHAR): Treatment name
- `sdydosedt` (DATETIME): Dose date
- `sdydose` (DOUBLE): Dose amount
- `sdydoseu` (DOUBLE): Dose unit

**Indexes**: subjid, sdytrtid

**Common Queries**:
```sql
-- Get treatment for a patient
SELECT * FROM sdytrt WHERE subjid = 1001;

-- Get treatment doses
SELECT * FROM sdytrt WHERE subjid = 1001 ORDER BY sdydosedt;
```

### ttevent
**Purpose**: Time-to-event analyses  
**Rows**: ~3,818 (multiple per patient)  
**Key Columns**:
- `subjid` (BIGINT): Subject ID (indexed)
- `ttecd` (VARCHAR): Event code
- `ttetest` (VARCHAR): Test name
- `ttestdt` (DATETIME): Test start date
- `tteendt` (DATETIME): Test end date
- `ttecensflg` (DOUBLE): Censoring flag

**Indexes**: subjid, ttecd

**Common Queries**:
```sql
-- Get time-to-event data
SELECT * FROM ttevent WHERE subjid = 1001;

-- Get progression events
SELECT * FROM ttevent WHERE ttecd = 'PFS';
```

### bor
**Purpose**: Best Overall Response  
**Rows**: ~179 (one per patient)  
**Key Columns**:
- `subjid` (BIGINT): Subject ID (indexed)
- `borcd` (DOUBLE): Response code
- `bordt` (DATETIME): Assessment date

**Indexes**: subjid, bordt

**Common Queries**:
```sql
-- Get best overall response
SELECT * FROM bor WHERE subjid = 1001;

-- Get responses by treatment
SELECT b.subjid, b.borcd, s.trt FROM bor b
JOIN subjinfo s ON b.subjid = s.subjid;
```

### disposit
**Purpose**: Patient disposition  
**Rows**: ~175 (one per patient)  
**Key Columns**:
- `subjid` (BIGINT): Subject ID (indexed)
- `ds` (DOUBLE): Disposition code
- `dsdt` (DATETIME): Disposition date
- `dsstat` (DOUBLE): Disposition status

**Indexes**: subjid

**Common Queries**:
```sql
-- Get patient disposition
SELECT * FROM disposit WHERE subjid = 1001;

-- Get completed patients
SELECT * FROM disposit WHERE dsstat = 1;
```

## Common Join Patterns

### Patient with Events
```sql
SELECT s.subjid, s.ageyr, s.sex, s.trt, e.aeterm, e.aestdt
FROM subjinfo s
JOIN events e ON s.subjid = e.subjid
WHERE s.trt = 'Arm A';
```

### Patient with Lesions
```sql
SELECT s.subjid, s.trt, l.lsname, l.lsasmdt, l.lsresptp
FROM subjinfo s
JOIN lesions l ON s.subjid = l.subjid
ORDER BY s.subjid, l.lsasmdt;
```

### Patient with Visits and Vitals
```sql
SELECT s.subjid, v.visdt, vs.vstest, vs.vsrn
FROM subjinfo s
JOIN visit v ON s.subjid = v.subjid
JOIN vitals vs ON v.subjid = vs.subjid AND v.visfwdid = vs.visfwdid
WHERE s.subjid = 1001;
```

## Data Types

- **BIGINT**: Integer IDs (subjid, aeid, etc.)
- **DOUBLE**: Numeric values (age, codes, flags)
- **VARCHAR/TEXT**: Text fields (names, terms, descriptions)
- **DATETIME**: Date/time fields (dates, timestamps)

## Notes for LLM Query Generation

1. **Primary Key**: Always use `subjid` to join tables
2. **Date Fields**: Most date fields have both DATETIME and VARCHAR (DTC) versions
3. **Flags**: Many fields have flag columns (0/1 or Y/N)
4. **Codes**: Many categorical fields have both code (numeric) and name (text) versions
5. **Multiple Rows**: Most tables have multiple rows per patient (events, visits, etc.)
6. **Missing Data**: Some fields may be NULL - handle appropriately in queries

## Query Optimization Tips

1. Always filter by `subjid` first when querying patient-specific data
2. Use indexes on `subjid`, `visfwdid`, `aestdt`, `visdt` for date range queries
3. Use `LIMIT` to restrict result sets
4. Consider using `GROUP BY` for aggregations
5. Use `JOIN` instead of subqueries when possible

