"""SQL query generator from natural language queries using LLM."""

import os
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from src.utils.config import Config
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SQLGenerator:
    """Generate SQL queries from natural language using LLM."""

    def __init__(self, config: Config | None = None, use_llm: bool = True):
        """
        Initialize SQL generator.

        Args:
            config: Config instance (uses Config.from_env() if None)
            use_llm: Whether to use LLM for SQL generation (default: True)
        """
        self.config = config or Config.from_env()
        self.use_llm = use_llm
        
        if self.use_llm:
            if OpenAI is None:
                raise ImportError("openai not installed. Install with: pip install openai")
            if not self.config.openai_api_key:
                logger.warning("OPENAI_API_KEY not set, falling back to simple SQL generator")
                self.use_llm = False
            else:
                self.client = OpenAI(api_key=self.config.openai_api_key)
                self.model = os.getenv("SQL_MODEL", "gpt-4o-mini")  # Fast model for SQL generation
                self._load_sql_guide()
        
        # Fallback: Simple keyword-based mappings (kept for backward compatibility)
        self.TABLE_MAPPINGS = {
        # Patient/Subject tables
        "patient": "subjinfo",
        "patients": "subjinfo",
        "subject": "subjinfo",
        "subjects": "subjinfo",
        "demographic": "subjinfo",
        "demographics": "subjinfo",
        "baseline": "subjinfo",
        
        # Adverse events
        "event": "events",
        "events": "events",
        "adverse": "events",
        "adverse_event": "events",
        "adverse_events": "events",
        "ae": "events",
        "safety": "events",
        
        # Lesions
        "lesion": "lesions",
        "lesions": "lesions",
        "tumor": "lesions",
        "tumors": "lesions",
        "response": "lesions",
        
        # Visits
        "visit": "visit",
        "visits": "visit",
        "schedule": "visit",
        
        # Vital signs
        "vital": "vitals",
        "vitals": "vitals",
        "vital_sign": "vitals",
        "vital_signs": "vitals",
        
        # Medications
        "medication": "cmtpy",
        "medications": "cmtpy",
        "concomitant": "cmtpy",
        "cm": "cmtpy",
        
        # Treatment
        "treatment": "sdytrt",
        "treatments": "sdytrt",
        "dose": "sdytrt",
        "dosing": "sdytrt",
        "study_treatment": "sdytrt",
        
        # Time to event
        "time_to_event": "ttevent",
        "survival": "ttevent",
        "progression": "ttevent",
        "tte": "ttevent",
        
        # Disposition
        "disposition": "disposit",
        "completion": "disposit",
        "status": "disposit",
        
        # Best overall response
        "bor": "bor",
        "best_response": "bor",
        "response": "bor",
        
        # Diagnosis
        "diagnosis": "diag",
        "diagnostic": "diag",
        
        # Exposure
        "exposure": "exsum",
        "exposure_summary": "exsum",
        
        # History
        "history": "history",
        "medical_history": "history",
        "prior": "history",
        
        # Progressive disease
        "progressive_disease": "pdsumm",
        "pd": "pdsumm",
    }

    COLUMN_MAPPINGS = {
        # Demographics
        "age": "ageyr",
        "age_years": "ageyr",
        "sex": "sex",
        "gender": "sex",
        "race": "race",
        "ethnicity": "ethnic",
        "country": "country",
        
        # Identifiers
        "subject_id": "subjid",
        "subjectid": "subjid",
        "patient_id": "subjid",
        "usubjid": "usubjid",
        "unique_subject_id": "usubjid",
        
        # Treatment
        "treatment": "trt",
        "treatment_arm": "trt",
        "arm": "trt",
        "treatment_sort": "trtsort",
        
        # Visits
        "visit": "visfwdid",
        "visit_id": "visfwdid",
        "visit_number": "visfwdid",
        "visit_date": "visdt",
        "visit_date_char": "visdtc",
        
        # Events
        "adverse_event": "aeterm",
        "event_term": "aeterm",
        "event_start": "aestdt",
        "event_end": "aeendt",
        "severity": "aesevvis",
        "serious": "saeasflg",
        
        # Lesions
        "lesion_id": "lsid",
        "lesion_name": "lsname",
        "assessment_date": "lsasmdt",
        
        # Vitals
        "vital_test": "vstestcd",
        "vital_test_name": "vstest",
    }

    def _load_sql_guide(self) -> None:
        """Load the SQL generation guide for LLM context."""
        guide_path = Path(__file__).parent.parent / "docs" / "LLM_SQL_GENERATION_GUIDE.md"
        schema_path = Path(__file__).parent.parent / "docs" / "SQL_SCHEMA.md"
        
        self.sql_guide = ""
        self.schema_info = ""
        
        try:
            if guide_path.exists():
                with open(guide_path, "r", encoding="utf-8") as f:
                    self.sql_guide = f.read()
            if schema_path.exists():
                with open(schema_path, "r", encoding="utf-8") as f:
                    self.schema_info = f.read()
        except Exception as e:
            logger.warning("failed_to_load_sql_guides", error=str(e))

    def generate_sql(self, query: str, limit: int = 10) -> str:
        """
        Generate SQL query from natural language.

        Args:
            query: Natural language query
            limit: Maximum number of results

        Returns:
            SQL query string
        """
        if self.use_llm:
            return self._generate_sql_with_llm(query, limit)
        else:
            return self._generate_sql_simple(query, limit)
    
    def _generate_sql_with_llm(self, query: str, limit: int = 10) -> str:
        """Generate SQL using LLM with the SQL generation guide."""
        system_prompt = """You are an expert SQL query generator for clinical trial data.

Your task is to convert natural language questions into accurate SQL queries for the MySQL database.

CRITICAL RULES:
1. ALWAYS include LIMIT clause (default: 10, but use the provided limit)
2. Use correct table names (see schema below)
3. Use `subjid` for ALL joins between tables
4. For aggregations (COUNT, SUM, AVG, etc.), use GROUP BY appropriately
5. Handle NULL values where appropriate
6. Use correct data types (numbers vs strings, dates vs strings)
7. Return ONLY the SQL query, no explanations

SCHEMA INFORMATION:
""" + (self.schema_info[:2000] if self.schema_info else "See SQL_SCHEMA.md for details")

        user_prompt = f"""Generate a SQL query for this question:

Question: {query}

Requirements:
- Maximum {limit} results (use LIMIT {limit})
- Use the correct table(s) from the schema
- Include proper WHERE filters if needed
- Use GROUP BY for aggregations
- Return only the SQL query, nothing else

SQL Query:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,  # Low temperature for consistent SQL
                max_tokens=500,
            )
            
            sql = response.choices[0].message.content.strip()
            
            # Clean up SQL (remove markdown code blocks if present)
            if sql.startswith("```sql"):
                sql = sql[6:]
            if sql.startswith("```"):
                sql = sql[3:]
            sql = sql.strip().rstrip("```").strip()
            
            # Ensure LIMIT is present
            if "LIMIT" not in sql.upper():
                sql = f"{sql.rstrip(';')} LIMIT {limit}"
            
            logger.debug("sql_generated_llm", query=query[:50], sql=sql[:100])
            return sql
            
        except Exception as e:
            logger.error("llm_sql_generation_failed", query=query[:50], error=str(e))
            # Fallback to simple generator
            return self._generate_sql_simple(query, limit)
    
    def _generate_sql_simple(self, query: str, limit: int = 10) -> str:
        """Fallback: Simple keyword-based SQL generation."""
        query_lower = query.lower()

        # Extract table name
        table = self._extract_table(query_lower)
        
        # Extract WHERE conditions
        conditions = self._extract_conditions(query_lower)
        
        # Extract SELECT columns
        columns = self._extract_columns(query_lower)
        
        # Build SQL
        select_clause = ", ".join(columns) if columns else "*"
        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = f"SELECT {select_clause} FROM {table} WHERE {where_clause} LIMIT {limit}"

        logger.debug("sql_generated_simple", query=query, sql=sql)
        return sql

    def _extract_table(self, query: str) -> str:
        """Extract table name from query."""
        default_table = "events"
        for keyword, table in self.TABLE_MAPPINGS.items():
            if keyword in query:
                return table
        return default_table

    def _extract_conditions(self, query: str) -> list[str]:
        """Extract WHERE conditions from query."""
        conditions = []

        # Age conditions
        age_match = re.search(r"age\s*(>|>=|<|<=|=)\s*(\d+)", query)
        if age_match:
            op = age_match.group(1)
            value = age_match.group(2)
            conditions.append(f"ageyr {op} {value}")

        # Gender/Sex conditions
        if "male" in query and "female" not in query:
            conditions.append("sex = 1")
        elif "female" in query:
            conditions.append("sex = 2")

        # Treatment conditions
        if "treatment" in query or "arm" in query:
            # Try to extract treatment arm
            if "arm a" in query or "arm 1" in query:
                conditions.append("trt = 'Arm A'")
            elif "arm b" in query or "arm 2" in query:
                conditions.append("trt = 'Arm B'")

        # Numeric comparisons
        numeric_patterns = [
            (r"(\w+)\s*(>|>=|<|<=|=)\s*(\d+)", lambda m: f"{m.group(1)} {m.group(2)} {m.group(3)}"),
        ]

        for pattern, formatter in numeric_patterns:
            matches = re.finditer(pattern, query)
            for match in matches:
                col = match.group(1)
                if col in self.COLUMN_MAPPINGS:
                    col = self.COLUMN_MAPPINGS[col]
                    condition = formatter(match)
                    if condition not in conditions:
                        conditions.append(condition)

        return conditions

    def _extract_columns(self, query: str) -> list[str]:
        """Extract SELECT columns from query."""
        columns = []

        # Keywords that suggest specific columns
        if "count" in query or "how many" in query:
            columns.append("COUNT(*) as count")
        elif "age" in query:
            columns.append("ageyr")
        if "sex" in query or "gender" in query:
            columns.append("sex")
        if "treatment" in query:
            columns.append("trt")

        return columns

    def generate_simple_search(self, query: str, table: str, limit: int = 10) -> str:
        """
        Generate a simple text search query (ILIKE pattern matching).

        Args:
            query: Search query
            table: Table name
            limit: Maximum results

        Returns:
            SQL query string
        """
        # Simple text search - looks for query terms in text columns
        # This is a basic implementation - can be enhanced
        search_terms = query.split()
        conditions = []
        
        for term in search_terms:
            # Search in common text columns
            conditions.append(f"(text_data ILIKE '%{term}%' OR description ILIKE '%{term}%')")

        where_clause = " OR ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM {table} WHERE {where_clause} LIMIT {limit}"

        return sql

