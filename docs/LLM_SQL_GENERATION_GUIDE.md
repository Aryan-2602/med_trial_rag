# LLM SQL Query Generation Guide

## Purpose
This document provides comprehensive guidance for generating accurate SQL queries from natural language questions about the H3E-US-S130 clinical trial data. Use this as a reference when converting user queries into SQL.

---

## Table of Contents
1. [Schema Overview](#schema-overview)
2. [Core Concepts](#core-concepts)
3. [Query Generation Workflow](#query-generation-workflow)
4. [Thinking Patterns](#thinking-patterns)
5. [Common Query Patterns](#common-query-patterns)
6. [Few-Shot Examples](#few-shot-examples)
7. [Data Type Handling](#data-type-handling)
8. [Join Strategies](#join-strategies)
9. [Aggregation Patterns](#aggregation-patterns)
10. [Date/Time Handling](#datetime-handling)
11. [Common Mistakes to Avoid](#common-mistakes)
12. [Best Practices](#best-practices)
13. [Advanced Patterns](#advanced-patterns)

---

## Schema Overview

### Database: `cotrial_rag`
**Study**: H3E-US-S130 Clinical Trial  
**Total Tables**: 16  
**Primary Entity**: Patients (identified by `SUBJID`)

### Key Tables

| Table | Rows | Purpose | Primary Key |
|-------|------|---------|-------------|
| `subjinfo` | ~179 | Patient demographics & baseline | `subjid` |
| `events` | ~25,522 | Adverse events & safety | `subjid`, `aeid`, `aeseqid` |
| `lesions` | ~4,068 | Tumor lesion measurements | `subjid`, `lsid` |
| `visit` | ~1,938 | Visit schedules | `subjid`, `visfwdid` |
| `vitals` | ~7,420 | Vital signs | `subjid`, `visfwdid`, `vstestcd` |
| `cmtpy` | ~24,335 | Concomitant medications | `subjid`, `cmid` |
| `sdytrt` | ~2,786 | Study treatment dosing | `subjid`, `sdytrtid` |
| `ttevent` | ~3,818 | Time-to-event analyses | `subjid`, `ttecd` |
| `bor` | ~179 | Best Overall Response | `subjid` |
| `disposit` | ~175 | Patient disposition | `subjid` |
| `diag` | ~179 | Diagnostic information | `subjid` |
| `exsum` | ~1,095 | Exposure summary | `subjid` |
| `syst` | ~515 | System administration | `subjid` |
| `history` | ~273 | Medical history | `subjid`, `hxid` |
| `pdsumm` | ~1,715 | Progressive disease | `subjid`, `visfwdid` |
| `cmtpyatc` | ~1,261 | ATC medication codes | `cmterm` |

### Critical Columns

**Patient Identifiers:**
- `subjid` (BIGINT): Primary patient identifier - USE THIS FOR JOINS
- `usubjid` (VARCHAR): Unique study-wide identifier

**Demographics (subjinfo):**
- `ageyr` (DOUBLE): Age in years
- `sex` (DOUBLE): 1=Male, 2=Female
- `race` (DOUBLE): Race code
- `ethnic` (DOUBLE): Ethnicity code
- `country` (VARCHAR): Country name
- `trt` (VARCHAR): Treatment arm (e.g., "Arm A", "Arm B")
- `trtsort` (DOUBLE): Treatment sort order

**Common Patterns:**
- Date fields: Usually have both `*DT` (DATETIME) and `*DTC` (VARCHAR) versions
- Code fields: Often have `*CD` (numeric code) and `*NM` (name/description) versions
- Flag fields: End with `*FLG` (0/1 or Y/N indicators)

---

## Core Concepts

### 1. One-to-Many Relationships
Most tables have **multiple rows per patient**:
- One patient → Many adverse events
- One patient → Many visits
- One patient → Many lesions
- One patient → Many vital sign measurements

**Exception**: `subjinfo`, `bor`, `disposit`, `diag` have **one row per patient**.

### 2. Primary Join Key
**ALWAYS use `subjid` to join tables**. This is the universal identifier.

### 3. Date Fields
- DATETIME fields: `*dt` (e.g., `aestdt`, `visdt`, `lsasmdt`)
- VARCHAR fields: `*dtc` (e.g., `aestdtc`, `visdtc`) - ISO format strings
- **Prefer DATETIME fields** for queries, use `*dtc` only for display

### 4. Code vs Name Fields
Many fields have both:
- Code: Numeric (e.g., `race`, `sex`, `aectc`)
- Name: Text description (e.g., `racelnm`, `sexlnm`, `aectclnm`)
- **Use code for filtering, name for display**

### 5. Missing Data
- Many fields can be NULL
- Use `IS NULL` or `IS NOT NULL` checks
- Consider `COALESCE()` for defaults

---

## Query Generation Workflow

### Step 1: Understand the Question
1. **Identify the entity**: Patient? Event? Visit? Lesion?
2. **Identify the action**: Count? List? Filter? Aggregate?
3. **Identify filters**: Age? Treatment? Date range? Severity?
4. **Identify grouping**: By patient? By treatment? By time?

### Step 2: Map to Tables
1. **Primary table**: Which table contains the main data?
2. **Join tables**: Do we need patient demographics? Treatment info?
3. **Filter tables**: Do we need to filter by related data?

### Step 3: Construct Query
1. **SELECT**: What columns to return?
2. **FROM**: Primary table
3. **JOIN**: Related tables (always on `subjid`)
4. **WHERE**: Filters
5. **GROUP BY**: Aggregations
6. **HAVING**: Post-aggregation filters
7. **ORDER BY**: Sort order
8. **LIMIT**: Result size (ALWAYS include LIMIT for safety)

### Step 4: Validate
1. **Check joins**: All joins use `subjid`?
2. **Check filters**: Appropriate data types?
3. **Check aggregations**: GROUP BY matches SELECT?
4. **Check NULLs**: Handle missing data?
5. **Check LIMIT**: Included for safety?

---

## Thinking Patterns

### Pattern 1: Patient-Centric Queries
**When**: Questions about patients, demographics, counts of patients

**Structure**:
```sql
SELECT [demographics/aggregates]
FROM subjinfo
[WHERE filters]
[GROUP BY grouping]
[ORDER BY sort]
LIMIT [number];
```

**Example Thinking**:
- "How many patients are in each treatment arm?"
- → Primary: `subjinfo` (one row per patient)
- → Action: COUNT
- → Group: `trt`
- → Query: `SELECT trt, COUNT(*) FROM subjinfo GROUP BY trt`

### Pattern 2: Event-Centric Queries
**When**: Questions about adverse events, safety data

**Structure**:
```sql
SELECT [event details]
FROM events
[JOIN subjinfo ON events.subjid = subjinfo.subjid]
WHERE [filters]
[GROUP BY grouping]
[ORDER BY sort]
LIMIT [number];
```

**Example Thinking**:
- "What are the serious adverse events for patients in Arm A?"
- → Primary: `events` (adverse events)
- → Join: `subjinfo` (for treatment arm)
- → Filter: `saeasflg = 1` AND `trt = 'Arm A'`
- → Query: `SELECT * FROM events e JOIN subjinfo s ON e.subjid = s.subjid WHERE e.saeasflg = 1 AND s.trt = 'Arm A' LIMIT 100`

### Pattern 3: Time-Series Queries
**When**: Questions about changes over time, visits, assessments

**Structure**:
```sql
SELECT [time field, other fields]
FROM [table]
WHERE subjid = [id] OR [other filters]
ORDER BY [date field]
LIMIT [number];
```

**Example Thinking**:
- "Show me all visits for patient 1001 in chronological order"
- → Primary: `visit`
- → Filter: `subjid = 1001`
- → Sort: `visdt` (visit date)
- → Query: `SELECT * FROM visit WHERE subjid = 1001 ORDER BY visdt LIMIT 100`

### Pattern 4: Aggregation Queries
**When**: Questions with "how many", "count", "average", "sum"

**Structure**:
```sql
SELECT [aggregate functions], [grouping columns]
FROM [table]
[JOIN related tables]
WHERE [filters]
GROUP BY [grouping columns]
[HAVING post-aggregation filters]
ORDER BY [sort]
LIMIT [number];
```

**Example Thinking**:
- "What's the average age of patients by treatment arm?"
- → Primary: `subjinfo`
- → Aggregate: `AVG(ageyr)`
- → Group: `trt`
- → Query: `SELECT trt, AVG(ageyr) as avg_age FROM subjinfo GROUP BY trt`

### Pattern 5: Complex Multi-Table Queries
**When**: Questions requiring data from multiple tables

**Structure**:
```sql
SELECT [columns from multiple tables]
FROM [primary table] p
JOIN [secondary table] s ON p.subjid = s.subjid
[JOIN additional tables]
WHERE [filters]
[GROUP BY grouping]
[ORDER BY sort]
LIMIT [number];
```

**Example Thinking**:
- "Show me patients with their best overall response and treatment arm"
- → Primary: `subjinfo` (demographics)
- → Join: `bor` (best response)
- → Join key: `subjid`
- → Query: `SELECT s.subjid, s.trt, b.borcd FROM subjinfo s JOIN bor b ON s.subjid = b.subjid LIMIT 100`

---

## Common Query Patterns

### Pattern 1: Patient Demographics
```sql
-- Get all patients
SELECT * FROM subjinfo LIMIT 100;

-- Get patients by treatment
SELECT * FROM subjinfo WHERE trt = 'Arm A' LIMIT 100;

-- Get patient count by treatment
SELECT trt, COUNT(*) as patient_count 
FROM subjinfo 
GROUP BY trt;

-- Get demographics summary
SELECT 
    trt,
    COUNT(*) as n,
    AVG(ageyr) as avg_age,
    MIN(ageyr) as min_age,
    MAX(ageyr) as max_age
FROM subjinfo
GROUP BY trt;
```

### Pattern 2: Adverse Events
```sql
-- Get all adverse events
SELECT * FROM events LIMIT 100;

-- Get events for a specific patient
SELECT * FROM events WHERE subjid = 1001 LIMIT 100;

-- Get serious adverse events
SELECT * FROM events WHERE saeasflg = 1 LIMIT 100;

-- Count events by patient
SELECT subjid, COUNT(*) as event_count 
FROM events 
GROUP BY subjid 
ORDER BY event_count DESC 
LIMIT 100;

-- Get events by severity
SELECT aectc, COUNT(*) as count 
FROM events 
WHERE aectc IS NOT NULL
GROUP BY aectc 
ORDER BY aectc;

-- Get events with patient demographics
SELECT 
    e.subjid,
    s.trt,
    e.aeterm,
    e.aestdt,
    e.aectc
FROM events e
JOIN subjinfo s ON e.subjid = s.subjid
LIMIT 100;
```

### Pattern 3: Lesions
```sql
-- Get all lesions
SELECT * FROM lesions LIMIT 100;

-- Get lesions for a patient
SELECT * FROM lesions WHERE subjid = 1001 ORDER BY lsasmdt LIMIT 100;

-- Get target lesions
SELECT * FROM lesions WHERE bltrgflg = 1 LIMIT 100;

-- Count lesions per patient
SELECT subjid, COUNT(*) as lesion_count 
FROM lesions 
GROUP BY subjid 
ORDER BY lesion_count DESC 
LIMIT 100;
```

### Pattern 4: Visits
```sql
-- Get all visits
SELECT * FROM visit LIMIT 100;

-- Get visits for a patient
SELECT * FROM visit WHERE subjid = 1001 ORDER BY visdt LIMIT 100;

-- Get visits in date range
SELECT * FROM visit 
WHERE visdt BETWEEN '2020-01-01' AND '2020-12-31' 
LIMIT 100;

-- Count visits per patient
SELECT subjid, COUNT(*) as visit_count 
FROM visit 
GROUP BY subjid 
ORDER BY visit_count DESC 
LIMIT 100;
```

### Pattern 5: Vital Signs
```sql
-- Get vital signs for a patient
SELECT * FROM vitals WHERE subjid = 1001 LIMIT 100;

-- Get specific vital sign (e.g., blood pressure)
SELECT * FROM vitals 
WHERE subjid = 1001 AND vstestcd = 'SYSBP' 
ORDER BY visfwdid 
LIMIT 100;

-- Get all vital signs for a visit
SELECT * FROM vitals 
WHERE subjid = 1001 AND visfwdid = 1 
LIMIT 100;
```

### Pattern 6: Medications
```sql
-- Get medications for a patient
SELECT * FROM cmtpy WHERE subjid = 1001 LIMIT 100;

-- Get active medications (no end date)
SELECT * FROM cmtpy 
WHERE subjid = 1001 AND cmendt IS NULL 
LIMIT 100;

-- Get medications in date range
SELECT * FROM cmtpy 
WHERE subjid = 1001 
  AND cmstdt >= '2020-01-01' 
  AND (cmendt <= '2020-12-31' OR cmendt IS NULL)
LIMIT 100;
```

### Pattern 7: Treatment
```sql
-- Get treatment for a patient
SELECT * FROM sdytrt WHERE subjid = 1001 ORDER BY sdydosedt LIMIT 100;

-- Get treatment doses
SELECT subjid, sdydosedt, sdydose, sdydoseu 
FROM sdytrt 
WHERE subjid = 1001 
ORDER BY sdydosedt 
LIMIT 100;
```

### Pattern 8: Best Overall Response
```sql
-- Get BOR for all patients
SELECT * FROM bor LIMIT 100;

-- Get BOR with treatment
SELECT s.subjid, s.trt, b.borcd, b.bordt 
FROM subjinfo s
JOIN bor b ON s.subjid = b.subjid
LIMIT 100;

-- Count responses by treatment
SELECT s.trt, b.borcd, COUNT(*) as count
FROM subjinfo s
JOIN bor b ON s.subjid = b.subjid
GROUP BY s.trt, b.borcd
ORDER BY s.trt, b.borcd;
```

---

## Few-Shot Examples

### Example 1: Simple Patient Count
**Question**: "How many patients are in the study?"

**Thinking**:
- Entity: Patients
- Action: Count
- Table: `subjinfo` (one row per patient)
- No filters needed
- No grouping needed

**SQL**:
```sql
SELECT COUNT(*) as patient_count 
FROM subjinfo;
```

**Expected Output**: Single row with `patient_count` (e.g., 179)

---

### Example 2: Patient Count by Treatment
**Question**: "How many patients are in each treatment arm?"

**Thinking**:
- Entity: Patients
- Action: Count
- Table: `subjinfo`
- Grouping: By `trt` (treatment arm)
- No filters

**SQL**:
```sql
SELECT trt, COUNT(*) as patient_count 
FROM subjinfo 
GROUP BY trt 
ORDER BY trt;
```

**Expected Output**:
```
trt    | patient_count
-------|---------------
Arm A  | 89
Arm B  | 90
```

---

### Example 3: Average Age by Treatment
**Question**: "What is the average age of patients in each treatment arm?"

**Thinking**:
- Entity: Patients
- Action: Average age
- Table: `subjinfo`
- Aggregate: `AVG(ageyr)`
- Grouping: By `trt`
- No filters

**SQL**:
```sql
SELECT 
    trt, 
    AVG(ageyr) as avg_age,
    COUNT(*) as n
FROM subjinfo 
GROUP BY trt 
ORDER BY trt;
```

**Expected Output**:
```
trt    | avg_age | n
-------|---------|----
Arm A  | 62.5    | 89
Arm B  | 61.8    | 90
```

---

### Example 4: Patient Demographics
**Question**: "Show me the demographics of patients in Arm A"

**Thinking**:
- Entity: Patients
- Action: List/Show
- Table: `subjinfo`
- Filter: `trt = 'Arm A'`
- Columns: Demographics (age, sex, race, etc.)

**SQL**:
```sql
SELECT 
    subjid,
    usubjid,
    ageyr,
    sex,
    race,
    ethnic,
    country,
    trt
FROM subjinfo 
WHERE trt = 'Arm A' 
LIMIT 100;
```

**Expected Output**: Multiple rows with patient demographics

---

### Example 5: Adverse Events for a Patient
**Question**: "What adverse events did patient 1001 experience?"

**Thinking**:
- Entity: Adverse events
- Action: List
- Table: `events`
- Filter: `subjid = 1001`
- Order: By date (chronological)

**SQL**:
```sql
SELECT 
    subjid,
    aeid,
    aeterm,
    aestdt,
    aeendt,
    aectc,
    saeasflg
FROM events 
WHERE subjid = 1001 
ORDER BY aestdt 
LIMIT 100;
```

**Expected Output**: Multiple rows with adverse events for patient 1001

---

### Example 6: Serious Adverse Events
**Question**: "How many serious adverse events occurred in Arm A?"

**Thinking**:
- Entity: Adverse events
- Action: Count
- Tables: `events` (for events) + `subjinfo` (for treatment)
- Filter: `saeasflg = 1` AND `trt = 'Arm A'`
- Join: `events.subjid = subjinfo.subjid`
- Aggregate: COUNT

**SQL**:
```sql
SELECT COUNT(*) as serious_ae_count
FROM events e
JOIN subjinfo s ON e.subjid = s.subjid
WHERE e.saeasflg = 1 
  AND s.trt = 'Arm A';
```

**Expected Output**: Single row with count

---

### Example 7: Events by Severity
**Question**: "How many adverse events occurred by severity grade?"

**Thinking**:
- Entity: Adverse events
- Action: Count
- Table: `events`
- Grouping: By `aectc` (CTC grade/severity)
- Filter: Exclude NULL grades

**SQL**:
```sql
SELECT 
    aectc,
    COUNT(*) as event_count
FROM events 
WHERE aectc IS NOT NULL
GROUP BY aectc 
ORDER BY aectc;
```

**Expected Output**:
```
aectc | event_count
------|-------------
1     | 500
2     | 300
3     | 150
4     | 50
5     | 10
```

---

### Example 8: Patient with Events and Demographics
**Question**: "Show me patients in Arm A who had grade 3 or higher adverse events"

**Thinking**:
- Entity: Patients + Events
- Action: List
- Tables: `subjinfo` + `events`
- Join: `subjinfo.subjid = events.subjid`
- Filter: `trt = 'Arm A'` AND `aectc >= 3`
- Distinct: May need DISTINCT if patient has multiple events

**SQL**:
```sql
SELECT DISTINCT
    s.subjid,
    s.usubjid,
    s.ageyr,
    s.sex,
    s.trt,
    e.aeterm,
    e.aectc,
    e.aestdt
FROM subjinfo s
JOIN events e ON s.subjid = e.subjid
WHERE s.trt = 'Arm A' 
  AND e.aectc >= 3
ORDER BY s.subjid, e.aestdt
LIMIT 100;
```

**Expected Output**: Multiple rows with patients and their grade 3+ events

---

### Example 9: Visit Timeline
**Question**: "Show me all visits for patient 1001 in chronological order"

**Thinking**:
- Entity: Visits
- Action: List
- Table: `visit`
- Filter: `subjid = 1001`
- Order: By `visdt` (visit date)

**SQL**:
```sql
SELECT 
    subjid,
    visfwdid,
    visdt,
    visendt,
    visdesc,
    vistp
FROM visit 
WHERE subjid = 1001 
ORDER BY visdt 
LIMIT 100;
```

**Expected Output**: Multiple rows with visits in chronological order

---

### Example 10: Lesion Assessments Over Time
**Question**: "Show me all lesion assessments for patient 1001 over time"

**Thinking**:
- Entity: Lesions
- Action: List
- Table: `lesions`
- Filter: `subjid = 1001`
- Order: By `lsasmdt` (assessment date)

**SQL**:
```sql
SELECT 
    subjid,
    lsid,
    lsname,
    lsasmdt,
    lsrn,
    lsresptp
FROM lesions 
WHERE subjid = 1001 
ORDER BY lsasmdt, lsid 
LIMIT 100;
```

**Expected Output**: Multiple rows with lesion assessments over time

---

### Example 11: Vital Signs for a Visit
**Question**: "What were the vital signs for patient 1001 at visit 1?"

**Thinking**:
- Entity: Vital signs
- Action: List
- Table: `vitals`
- Filter: `subjid = 1001` AND `visfwdid = 1`

**SQL**:
```sql
SELECT 
    subjid,
    visfwdid,
    vstestcd,
    vstest,
    vsrn,
    vsru
FROM vitals 
WHERE subjid = 1001 
  AND visfwdid = 1 
LIMIT 100;
```

**Expected Output**: Multiple rows with different vital sign measurements

---

### Example 12: Best Overall Response by Treatment
**Question**: "What is the best overall response rate by treatment arm?"

**Thinking**:
- Entity: Best Overall Response
- Action: Count/Calculate rate
- Tables: `bor` + `subjinfo`
- Join: `bor.subjid = subjinfo.subjid`
- Grouping: By `trt` and `borcd`
- Calculate: Count and percentage

**SQL**:
```sql
SELECT 
    s.trt,
    b.borcd,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY s.trt), 2) as percentage
FROM subjinfo s
JOIN bor b ON s.subjid = b.subjid
GROUP BY s.trt, b.borcd
ORDER BY s.trt, b.borcd;
```

**Expected Output**: Response counts and percentages by treatment

---

### Example 13: Patients with Multiple Events
**Question**: "Which patients had more than 5 adverse events?"

**Thinking**:
- Entity: Patients
- Action: Filter/List
- Table: `events`
- Aggregate: COUNT by `subjid`
- Filter: `HAVING COUNT(*) > 5`
- Join: May need `subjinfo` for patient details

**SQL**:
```sql
SELECT 
    e.subjid,
    s.usubjid,
    s.trt,
    COUNT(*) as event_count
FROM events e
JOIN subjinfo s ON e.subjid = s.subjid
GROUP BY e.subjid, s.usubjid, s.trt
HAVING COUNT(*) > 5
ORDER BY event_count DESC
LIMIT 100;
```

**Expected Output**: Patients with more than 5 events

---

### Example 14: Date Range Query
**Question**: "What adverse events occurred between January 1, 2020 and March 31, 2020?"

**Thinking**:
- Entity: Adverse events
- Action: List
- Table: `events`
- Filter: `aestdt BETWEEN '2020-01-01' AND '2020-03-31'`
- Order: By date

**SQL**:
```sql
SELECT 
    subjid,
    aeterm,
    aestdt,
    aeendt,
    aectc
FROM events 
WHERE aestdt BETWEEN '2020-01-01' AND '2020-03-31'
ORDER BY aestdt 
LIMIT 100;
```

**Expected Output**: Events in the date range

---

### Example 15: Complex Multi-Table Query
**Question**: "Show me patients in Arm A with their treatment doses, visits, and best overall response"

**Thinking**:
- Entity: Patients with related data
- Action: List
- Tables: `subjinfo` (base) + `sdytrt` + `visit` + `bor`
- Joins: All on `subjid`
- Filter: `trt = 'Arm A'`
- Note: This may create many rows due to multiple doses/visits per patient

**SQL**:
```sql
SELECT 
    s.subjid,
    s.usubjid,
    s.trt,
    t.sdydosedt,
    t.sdydose,
    v.visdt,
    v.visdesc,
    b.borcd,
    b.bordt
FROM subjinfo s
LEFT JOIN sdytrt t ON s.subjid = t.subjid
LEFT JOIN visit v ON s.subjid = v.subjid
LEFT JOIN bor b ON s.subjid = b.subjid
WHERE s.trt = 'Arm A'
ORDER BY s.subjid, t.sdydosedt, v.visdt
LIMIT 200;
```

**Expected Output**: Multiple rows per patient with treatment, visits, and response

---

## Data Type Handling

### Numeric Fields
- **BIGINT**: IDs (`subjid`, `aeid`, etc.)
- **DOUBLE**: Measurements, codes, flags
- **Use appropriate comparisons**: `=`, `>`, `<`, `>=`, `<=`, `BETWEEN`

### String Fields
- **VARCHAR/TEXT**: Names, terms, descriptions
- **Use LIKE for pattern matching**: `WHERE aeterm LIKE '%fever%'`
- **Case sensitivity**: MySQL is case-insensitive by default, but be explicit: `WHERE trt = 'Arm A'`

### Date/Time Fields
- **DATETIME**: Use for comparisons and sorting
- **Format**: `'YYYY-MM-DD'` or `'YYYY-MM-DD HH:MM:SS'`
- **Comparisons**: `BETWEEN`, `>=`, `<=`, `=`
- **Functions**: `DATE()`, `YEAR()`, `MONTH()`, `DAY()`

**Examples**:
```sql
-- Date range
WHERE aestdt BETWEEN '2020-01-01' AND '2020-12-31'

-- Specific year
WHERE YEAR(visdt) = 2020

-- Date comparison
WHERE aestdt >= '2020-01-01'
```

### NULL Handling
- **Check for NULL**: `IS NULL`, `IS NOT NULL`
- **Default values**: `COALESCE(column, default_value)`
- **Exclude NULLs**: `WHERE column IS NOT NULL`

**Examples**:
```sql
-- Exclude NULL ages
WHERE ageyr IS NOT NULL

-- Default for missing values
SELECT COALESCE(aectc, 0) as grade FROM events

-- Count non-NULL values
SELECT COUNT(ageyr) as n FROM subjinfo
```

---

## Join Strategies

### Inner Join (Default)
**Use when**: You only want rows that exist in both tables

```sql
SELECT * 
FROM events e
JOIN subjinfo s ON e.subjid = s.subjid
WHERE s.trt = 'Arm A';
```

### Left Join
**Use when**: You want all rows from the left table, even if no match in right table

```sql
SELECT * 
FROM subjinfo s
LEFT JOIN bor b ON s.subjid = b.subjid;
-- Returns all patients, even if no BOR record
```

### Right Join
**Use when**: You want all rows from the right table (rarely used)

### Multiple Joins
**Always join on `subjid`**:

```sql
SELECT 
    s.subjid,
    s.trt,
    e.aeterm,
    v.visdt
FROM subjinfo s
JOIN events e ON s.subjid = e.subjid
JOIN visit v ON s.subjid = v.subjid
WHERE s.trt = 'Arm A';
```

**Note**: Multiple joins can create Cartesian products if not careful. Use appropriate WHERE clauses.

---

## Aggregation Patterns

### COUNT
```sql
-- Count all rows
SELECT COUNT(*) FROM subjinfo;

-- Count distinct values
SELECT COUNT(DISTINCT subjid) FROM events;

-- Count with grouping
SELECT trt, COUNT(*) FROM subjinfo GROUP BY trt;
```

### SUM, AVG, MIN, MAX
```sql
-- Average age
SELECT AVG(ageyr) FROM subjinfo;

-- Min/Max age by treatment
SELECT trt, MIN(ageyr), MAX(ageyr), AVG(ageyr)
FROM subjinfo
GROUP BY trt;

-- Sum of doses
SELECT subjid, SUM(sdydose) as total_dose
FROM sdytrt
GROUP BY subjid;
```

### GROUP BY
**Rule**: All non-aggregated columns in SELECT must be in GROUP BY

```sql
-- Correct
SELECT trt, COUNT(*) FROM subjinfo GROUP BY trt;

-- Wrong (will error)
SELECT trt, ageyr, COUNT(*) FROM subjinfo GROUP BY trt;
-- ageyr must be in GROUP BY or removed
```

### HAVING
**Use for filtering after aggregation**:

```sql
-- Patients with more than 5 events
SELECT subjid, COUNT(*) as event_count
FROM events
GROUP BY subjid
HAVING COUNT(*) > 5;
```

---

## Date/Time Handling

### Date Comparisons
```sql
-- Date range
WHERE visdt BETWEEN '2020-01-01' AND '2020-12-31'

-- After date
WHERE aestdt >= '2020-01-01'

-- Before date
WHERE aeendt <= '2020-12-31'

-- Specific date
WHERE DATE(visdt) = '2020-06-15'
```

### Date Functions
```sql
-- Extract year
SELECT YEAR(visdt) as visit_year FROM visit;

-- Extract month
SELECT MONTH(visdt) as visit_month FROM visit;

-- Date difference (days)
SELECT DATEDIFF(aeendt, aestdt) as event_duration
FROM events
WHERE aeendt IS NOT NULL;

-- Current date
WHERE visdt >= CURDATE()
```

### Date Formatting
```sql
-- Format date for display
SELECT DATE_FORMAT(visdt, '%Y-%m-%d') as visit_date FROM visit;

-- Format with time
SELECT DATE_FORMAT(visdt, '%Y-%m-%d %H:%i:%s') as visit_datetime FROM visit;
```

---

## Common Mistakes to Avoid

### Mistake 1: Forgetting LIMIT
**Always include LIMIT** to prevent returning too many rows:
```sql
-- Good
SELECT * FROM events LIMIT 100;

-- Bad (could return 25,522 rows!)
SELECT * FROM events;
```

### Mistake 2: Wrong Join Key
**Always use `subjid` for joins**, not `usubjid` or other fields:
```sql
-- Good
JOIN subjinfo s ON e.subjid = s.subjid

-- Bad
JOIN subjinfo s ON e.usubjid = s.usubjid  -- May not work correctly
```

### Mistake 3: Missing GROUP BY
**When using aggregates, include GROUP BY**:
```sql
-- Good
SELECT trt, COUNT(*) FROM subjinfo GROUP BY trt;

-- Bad (will error or give wrong results)
SELECT trt, COUNT(*) FROM subjinfo;
```

### Mistake 4: Using Wrong Date Field
**Use DATETIME fields (`*dt`) for queries, not VARCHAR (`*dtc`)**:
```sql
-- Good
WHERE aestdt >= '2020-01-01'

-- Bad (string comparison, slower)
WHERE aestdtc >= '2020-01-01'
```

### Mistake 5: Not Handling NULLs
**Check for NULLs when needed**:
```sql
-- Good
WHERE aectc IS NOT NULL AND aectc >= 3

-- Bad (may miss rows or cause errors)
WHERE aectc >= 3  -- NULLs excluded, but be explicit
```

### Mistake 6: Case Sensitivity in String Comparisons
**Be explicit with string comparisons**:
```sql
-- Good
WHERE trt = 'Arm A'  -- MySQL is case-insensitive, but be explicit

-- Also good (case-insensitive)
WHERE UPPER(trt) = 'ARM A'
```

### Mistake 7: Cartesian Products
**Be careful with multiple joins** - always join on `subjid`:
```sql
-- Good (explicit joins)
FROM subjinfo s
JOIN events e ON s.subjid = e.subjid
JOIN visit v ON s.subjid = v.subjid

-- Bad (missing join condition = Cartesian product!)
FROM subjinfo s, events e, visit v
WHERE s.trt = 'Arm A'  -- Missing join conditions!
```

### Mistake 8: Forgetting DISTINCT
**Use DISTINCT when needed**:
```sql
-- If a patient can have multiple events, use DISTINCT for patient list
SELECT DISTINCT subjid FROM events WHERE aectc >= 3;

-- Without DISTINCT, you get duplicate patient IDs
SELECT subjid FROM events WHERE aectc >= 3;
```

---

## Best Practices

### 1. Always Include LIMIT
```sql
SELECT * FROM events LIMIT 100;  -- Always!
```

### 2. Use Explicit JOINs
```sql
-- Good
FROM subjinfo s
JOIN events e ON s.subjid = e.subjid

-- Avoid (old style)
FROM subjinfo s, events e
WHERE s.subjid = e.subjid
```

### 3. Use Table Aliases
```sql
-- Good (clear and concise)
SELECT s.subjid, s.trt, e.aeterm
FROM subjinfo s
JOIN events e ON s.subjid = e.subjid

-- Avoid (verbose)
SELECT subjinfo.subjid, subjinfo.trt, events.aeterm
FROM subjinfo
JOIN events ON subjinfo.subjid = events.subjid
```

### 4. Order Results Logically
```sql
-- Chronological
ORDER BY visdt

-- By patient then date
ORDER BY subjid, visdt

-- By count descending
ORDER BY event_count DESC
```

### 5. Filter Early
```sql
-- Good (filter before join when possible)
FROM subjinfo s
WHERE s.trt = 'Arm A'
JOIN events e ON s.subjid = e.subjid

-- Also good (filter in WHERE after join)
FROM subjinfo s
JOIN events e ON s.subjid = e.subjid
WHERE s.trt = 'Arm A'
```

### 6. Use Meaningful Column Names
```sql
-- Good
SELECT COUNT(*) as patient_count FROM subjinfo;

-- Avoid
SELECT COUNT(*) as cnt FROM subjinfo;
```

### 7. Handle NULLs Explicitly
```sql
-- Good
WHERE ageyr IS NOT NULL
SELECT COALESCE(aectc, 0) as grade

-- Avoid
WHERE ageyr > 0  -- May exclude valid ages if NULL handling unclear
```

### 8. Comment Complex Queries
```sql
-- Get serious adverse events for Arm A patients
-- with their demographics
SELECT 
    s.subjid,
    s.trt,
    e.aeterm,
    e.aestdt
FROM subjinfo s
JOIN events e ON s.subjid = e.subjid
WHERE s.trt = 'Arm A' 
  AND e.saeasflg = 1
LIMIT 100;
```

---

## Advanced Patterns

### Pattern 1: Subqueries
```sql
-- Patients who had grade 3+ events
SELECT * FROM subjinfo
WHERE subjid IN (
    SELECT DISTINCT subjid 
    FROM events 
    WHERE aectc >= 3
);
```

### Pattern 2: Window Functions
```sql
-- Rank events by date for each patient
SELECT 
    subjid,
    aeterm,
    aestdt,
    ROW_NUMBER() OVER (PARTITION BY subjid ORDER BY aestdt) as event_rank
FROM events
LIMIT 100;
```

### Pattern 3: Conditional Aggregation
```sql
-- Count events by severity within treatment
SELECT 
    s.trt,
    COUNT(*) as total_events,
    SUM(CASE WHEN e.aectc >= 3 THEN 1 ELSE 0 END) as grade3_plus_events
FROM subjinfo s
JOIN events e ON s.subjid = e.subjid
GROUP BY s.trt;
```

### Pattern 4: Date Ranges
```sql
-- Events in last 30 days from a date
SELECT * FROM events
WHERE aestdt >= DATE_SUB('2020-12-31', INTERVAL 30 DAY)
  AND aestdt <= '2020-12-31';
```

### Pattern 5: Existence Checks
```sql
-- Patients who had at least one serious event
SELECT * FROM subjinfo s
WHERE EXISTS (
    SELECT 1 FROM events e
    WHERE e.subjid = s.subjid
      AND e.saeasflg = 1
);
```

---

## Query Validation Checklist

Before returning a SQL query, verify:

- [ ] **LIMIT included** (always!)
- [ ] **Correct table names** (use actual table names: `subjinfo`, `events`, etc.)
- [ ] **Correct column names** (check exact spelling: `subjid`, `aeterm`, etc.)
- [ ] **Joins use `subjid`** (primary join key)
- [ ] **Data types match** (numbers vs strings, dates vs strings)
- [ ] **NULL handling** (if needed)
- [ ] **GROUP BY matches SELECT** (all non-aggregated columns in GROUP BY)
- [ ] **Date formats correct** ('YYYY-MM-DD' format)
- [ ] **String comparisons explicit** (case handling)
- [ ] **No Cartesian products** (all joins have conditions)
- [ ] **Appropriate filters** (WHERE clauses are correct)

---

## Quick Reference

### Table → Purpose Mapping
- **Patient info**: `subjinfo`
- **Adverse events**: `events`
- **Tumors/lesions**: `lesions`
- **Visits**: `visit`
- **Vital signs**: `vitals`
- **Medications**: `cmtpy`
- **Treatment**: `sdytrt`
- **Time-to-event**: `ttevent`
- **Best response**: `bor`
- **Disposition**: `disposit`

### Common Column Patterns
- **IDs**: `*id` (e.g., `subjid`, `aeid`, `lsid`)
- **Dates**: `*dt` (DATETIME) or `*dtc` (VARCHAR)
- **Codes**: `*cd` (numeric code)
- **Names**: `*nm` or `*term` (text description)
- **Flags**: `*flg` (0/1 or Y/N)

### Common Filters
- **Treatment**: `WHERE trt = 'Arm A'`
- **Patient**: `WHERE subjid = 1001`
- **Date range**: `WHERE visdt BETWEEN '2020-01-01' AND '2020-12-31'`
- **Severity**: `WHERE aectc >= 3`
- **Serious**: `WHERE saeasflg = 1`
- **Not NULL**: `WHERE ageyr IS NOT NULL`

---

## Final Notes

1. **Always test queries** with LIMIT first
2. **Use EXPLAIN** for complex queries to check performance
3. **Be explicit** - don't rely on defaults
4. **Handle edge cases** - NULLs, empty results, etc.
5. **Document complex logic** - add comments for future reference
6. **Validate data types** - ensure comparisons are appropriate
7. **Consider performance** - use indexes (subjid, dates, etc.)
8. **Error handling** - queries should be robust

---

**Remember**: When in doubt, use a simple query with LIMIT, then build complexity gradually!

---

## Additional Few-Shot Examples with Expected Outputs

### Example 16: Age Distribution
**Question**: "What is the age distribution of patients in the study?"

**SQL**:
```sql
SELECT 
    CASE 
        WHEN ageyr < 50 THEN '<50'
        WHEN ageyr < 60 THEN '50-59'
        WHEN ageyr < 70 THEN '60-69'
        WHEN ageyr < 80 THEN '70-79'
        ELSE '80+'
    END as age_group,
    COUNT(*) as patient_count
FROM subjinfo
WHERE ageyr IS NOT NULL
GROUP BY age_group
ORDER BY MIN(ageyr);
```

**Expected Output**:
```
age_group | patient_count
----------|---------------
<50       | 15
50-59     | 45
60-69     | 78
70-79     | 38
80+       | 3
```

---

### Example 17: Event Frequency Analysis
**Question**: "What are the most common adverse events?"

**SQL**:
```sql
SELECT 
    aeterm,
    COUNT(*) as event_count,
    COUNT(DISTINCT subjid) as patient_count
FROM events
WHERE aeterm IS NOT NULL
GROUP BY aeterm
ORDER BY event_count DESC
LIMIT 20;
```

**Expected Output**:
```
aeterm              | event_count | patient_count
--------------------|-------------|---------------
Fatigue             | 450         | 120
Nausea              | 380         | 95
Diarrhea            | 320         | 88
...
```

---

### Example 18: Treatment Comparison
**Question**: "Compare the number of serious adverse events between treatment arms"

**SQL**:
```sql
SELECT 
    s.trt,
    COUNT(*) as total_patients,
    COUNT(DISTINCT e.subjid) as patients_with_sae,
    COUNT(e.aeid) as total_sae_count
FROM subjinfo s
LEFT JOIN events e ON s.subjid = e.subjid AND e.saeasflg = 1
GROUP BY s.trt
ORDER BY s.trt;
```

**Expected Output**:
```
trt    | total_patients | patients_with_sae | total_sae_count
-------|----------------|-------------------|----------------
Arm A  | 89             | 25                | 42
Arm B  | 90             | 30                | 55
```

---

### Example 19: Visit Compliance
**Question**: "How many visits did each patient complete?"

**SQL**:
```sql
SELECT 
    s.subjid,
    s.trt,
    COUNT(v.visfwdid) as visit_count
FROM subjinfo s
LEFT JOIN visit v ON s.subjid = v.subjid
GROUP BY s.subjid, s.trt
ORDER BY visit_count DESC
LIMIT 100;
```

**Expected Output**:
```
subjid | trt    | visit_count
-------|--------|------------
1001   | Arm A  | 12
1002   | Arm B  | 11
...
```

---

### Example 20: Response Rate Calculation
**Question**: "What is the response rate (complete + partial response) by treatment?"

**SQL**:
```sql
SELECT 
    s.trt,
    COUNT(*) as total_patients,
    SUM(CASE WHEN b.borcd IN (1, 2) THEN 1 ELSE 0 END) as responders,
    ROUND(SUM(CASE WHEN b.borcd IN (1, 2) THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as response_rate
FROM subjinfo s
LEFT JOIN bor b ON s.subjid = b.subjid
GROUP BY s.trt;
```

**Expected Output**:
```
trt    | total_patients | responders | response_rate
-------|---------------|------------|---------------
Arm A  | 89             | 35         | 39.33
Arm B  | 90             | 42         | 46.67
```

---

## Error Handling Patterns

### Pattern 1: Handle Missing Data
```sql
-- Always check for NULLs when needed
SELECT 
    subjid,
    COALESCE(ageyr, 0) as age,
    CASE WHEN sex IS NULL THEN 'Unknown' ELSE CAST(sex AS CHAR) END as sex_display
FROM subjinfo;
```

### Pattern 2: Safe Division
```sql
-- Avoid division by zero
SELECT 
    trt,
    total_events,
    total_patients,
    CASE 
        WHEN total_patients > 0 THEN total_events / total_patients 
        ELSE 0 
    END as events_per_patient
FROM (
    SELECT trt, COUNT(*) as total_events, COUNT(DISTINCT subjid) as total_patients
    FROM events e
    JOIN subjinfo s ON e.subjid = s.subjid
    GROUP BY trt
) t;
```

### Pattern 3: Date Range Validation
```sql
-- Ensure start date <= end date
SELECT * FROM events
WHERE aestdt IS NOT NULL
  AND aeendt IS NOT NULL
  AND aestdt <= aeendt;
```

---

## Edge Cases

### Edge Case 1: Patient with No Events
**Question**: "Which patients had no adverse events?"

**SQL**:
```sql
SELECT s.subjid, s.trt
FROM subjinfo s
LEFT JOIN events e ON s.subjid = e.subjid
WHERE e.subjid IS NULL;
```

### Edge Case 2: Events with Missing Dates
**Question**: "Find adverse events where start date is missing"

**SQL**:
```sql
SELECT * FROM events
WHERE aestdt IS NULL
LIMIT 100;
```

### Edge Case 3: Duplicate Prevention
**Question**: "Get unique patients who had grade 3+ events"

**SQL**:
```sql
SELECT DISTINCT subjid
FROM events
WHERE aectc >= 3;
```

---

## Clinical Trial Specific Patterns

### Pattern 1: Intent-to-Treat Analysis
```sql
-- All randomized patients
SELECT * FROM subjinfo
WHERE trtsort IS NOT NULL;
```

### Pattern 2: Per-Protocol Analysis
```sql
-- Patients who completed study
SELECT s.* 
FROM subjinfo s
JOIN disposit d ON s.subjid = d.subjid
WHERE d.dsstat = 1;  -- Completed
```

### Pattern 3: Safety Population
```sql
-- Patients who received at least one dose
SELECT DISTINCT s.subjid
FROM subjinfo s
JOIN sdytrt t ON s.subjid = t.subjid;
```

---

## Natural Language to SQL Mapping

### Common Question Patterns

| Question Pattern | SQL Pattern |
|-----------------|-------------|
| "How many..." | `SELECT COUNT(*) ...` |
| "What is the average..." | `SELECT AVG(...) ...` |
| "Show me..." | `SELECT ... LIMIT ...` |
| "List..." | `SELECT ... ORDER BY ... LIMIT ...` |
| "Which patients..." | `SELECT ... WHERE ...` |
| "Compare..." | `SELECT ... GROUP BY ...` |
| "Over time" | `SELECT ... ORDER BY [date] ...` |
| "By treatment" | `SELECT ... GROUP BY trt ...` |
| "More than X" | `SELECT ... HAVING COUNT(*) > X` |
| "Between dates" | `SELECT ... WHERE [date] BETWEEN ...` |

### Entity Recognition

| Entity Mention | Maps To |
|----------------|---------|
| "patient", "subject" | `subjinfo` table |
| "adverse event", "AE", "side effect" | `events` table |
| "lesion", "tumor" | `lesions` table |
| "visit", "appointment" | `visit` table |
| "vital sign", "blood pressure" | `vitals` table |
| "medication", "drug" | `cmtpy` table |
| "treatment", "dose" | `sdytrt` table |
| "response", "BOR" | `bor` table |

---

## Query Templates

### Template 1: Patient List with Filter
```sql
SELECT 
    subjid,
    usubjid,
    ageyr,
    sex,
    trt
FROM subjinfo
WHERE [condition]
LIMIT [number];
```

### Template 2: Event Count by Group
```sql
SELECT 
    [grouping_column],
    COUNT(*) as event_count
FROM events
[JOIN other_tables]
WHERE [condition]
GROUP BY [grouping_column]
ORDER BY event_count DESC
LIMIT [number];
```

### Template 3: Time Series Data
```sql
SELECT 
    [date_column],
    [other_columns]
FROM [table]
WHERE subjid = [id]
ORDER BY [date_column]
LIMIT [number];
```

---

## Final Checklist Before Generating SQL

1. ✅ **Question understood**: What entity? What action? What filters?
2. ✅ **Table identified**: Correct table(s) selected?
3. ✅ **Columns identified**: Correct column names (check spelling)?
4. ✅ **Joins needed**: All joins use `subjid`?
5. ✅ **Filters correct**: Appropriate WHERE conditions?
6. ✅ **Aggregations**: GROUP BY matches SELECT?
7. ✅ **Data types**: Numbers vs strings, dates vs strings?
8. ✅ **NULL handling**: Checked for NULLs where needed?
9. ✅ **LIMIT included**: Always include LIMIT!
10. ✅ **Ordering**: Results ordered logically?
11. ✅ **Performance**: Uses indexed columns?
12. ✅ **Validation**: Query makes logical sense?

---

## Quick Reference Card

### Most Common Tables
- **Patients**: `subjinfo`
- **Events**: `events`
- **Lesions**: `lesions`
- **Visits**: `visit`
- **Vitals**: `vitals`

### Most Common Joins
```sql
JOIN subjinfo s ON [table].subjid = s.subjid
```

### Most Common Filters
```sql
WHERE subjid = [id]
WHERE trt = 'Arm A'
WHERE aectc >= 3
WHERE saeasflg = 1
WHERE [date] BETWEEN '2020-01-01' AND '2020-12-31'
```

### Always Remember
- ✅ Use `subjid` for joins
- ✅ Include `LIMIT`
- ✅ Handle NULLs
- ✅ Use correct data types
- ✅ Check table/column names

---

**END OF GUIDE**

This document should be used as the primary reference when generating SQL queries from natural language questions about the H3E-US-S130 clinical trial database.

