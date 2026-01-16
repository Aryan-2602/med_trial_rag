"""Optimized migration script to import SAS files into MySQL with proper schema design."""

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import pyreadstat
except ImportError:
    pyreadstat = None

try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    print("Error: mysql-connector-python not installed. Install with: pip install mysql-connector-python")
    sys.exit(1)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


def read_sas_file(file_path: str) -> pd.DataFrame:
    """Read SAS file using pyreadstat or fallback to pandas."""
    if pyreadstat:
        try:
            df, _ = pyreadstat.read_sas7bdat(file_path)
            return df
        except Exception as e:
            logger.warning("pyreadstat_failed", path=file_path, error=str(e))

    # Fallback: try pandas
    try:
        df = pd.read_sas(file_path)
        return df
    except Exception as e:
        logger.error("pandas_read_failed", path=file_path, error=str(e))
        raise


def get_mysql_connection():
    """Get MySQL connection from environment variables."""
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DB", "cotrial_rag"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
    )


def clean_column_name(col: str) -> str:
    """Clean column name for MySQL compatibility."""
    return col.replace(" ", "_").replace("-", "_").replace(".", "_").lower()


def get_mysql_type(col_name: str, col_type: Any, df: pd.DataFrame) -> str:
    """
    Get appropriate MySQL type for a column.
    
    Args:
        col_name: Column name
        col_type: Pandas dtype
        df: DataFrame to analyze
        
    Returns:
        MySQL type string
    """
    # Handle datetime columns
    if pd.api.types.is_datetime64_any_dtype(col_type):
        return "DATETIME"
    
    # Handle integer columns
    if pd.api.types.is_integer_dtype(col_type):
        # Check if it's a small integer (like flags) or large
        if col_name.endswith("FLG") or col_name.endswith("CD"):
            return "INT"
        return "BIGINT"
    
    # Handle float columns
    if pd.api.types.is_float_dtype(col_type):
        return "DOUBLE"
    
    # Handle boolean columns
    if pd.api.types.is_bool_dtype(col_type):
        return "BOOLEAN"
    
    # Handle string/object columns
    if pd.api.types.is_string_dtype(col_type) or pd.api.types.is_object_dtype(col_type):
        if len(df) > 0:
            max_len = df[col_name].astype(str).str.len().max()
            if pd.isna(max_len) or max_len == 0:
                max_len = 255
        else:
            max_len = 255
        
        # Use appropriate text type
        if max_len > 65535:
            return "LONGTEXT"
        elif max_len > 255:
            return "TEXT"
        else:
            return f"VARCHAR({min(int(max_len * 1.2), 255)})"
    
    # Default to TEXT
    return "TEXT"


def create_table_with_schema(
    conn: mysql.connector.connection,
    table_name: str,
    df: pd.DataFrame,
    table_comment: str = "",
    if_exists: str = "replace"
) -> None:
    """
    Create MySQL table with optimized schema, indexes, and comments.
    
    Args:
        conn: MySQL connection
        table_name: Name for the table
        df: DataFrame with data
        table_comment: Comment describing the table
        if_exists: What to do if table exists ("replace", "append", "fail")
    """
    cursor = conn.cursor()
    
    try:
        # Clean column names
        df_clean = df.copy()
        df_clean.columns = [clean_column_name(col) for col in df_clean.columns]
        
        # Drop table if replacing
        if if_exists == "replace":
            cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
            logger.info("dropped_table", table=table_name)
        
        # Build column definitions with comments
        columns = []
        primary_key_cols = []
        
        # Identify primary key candidates
        if "subjid" in df_clean.columns:
            primary_key_cols.append("subjid")
        if "usubjid" in df_clean.columns and "subjid" not in df_clean.columns:
            primary_key_cols.append("usubjid")
        
        # Add composite keys for multi-row tables
        composite_key_candidates = {
            "events": ["subjid", "aeid", "aeseqid"],
            "lesions": ["subjid", "lsid"],
            "visit": ["subjid", "visfwdid"],
            "vitals": ["subjid", "visfwdid", "vstestcd"],
            "cmtpy": ["subjid", "cmid"],
            "sdytrt": ["subjid", "sdytrtid"],
            "ttevent": ["subjid", "ttecd"],
        }
        
        for col_name, col_type in zip(df_clean.columns, df_clean.dtypes):
            mysql_type = get_mysql_type(col_name, col_type, df_clean)
            
            # Add column comment based on name patterns
            comment = ""
            if col_name == "subjid":
                comment = "Subject ID - Primary identifier for patient"
            elif col_name == "usubjid":
                comment = "Unique Subject ID - Study-wide unique identifier"
            elif col_name.endswith("_dt") or col_name.endswith("dt"):
                comment = "Date field"
            elif col_name.endswith("_flg") or col_name.endswith("flg"):
                comment = "Flag/indicator field (0/1 or Y/N)"
            elif col_name.endswith("_cd") or col_name.endswith("cd"):
                comment = "Code field"
            elif col_name.endswith("_nm") or col_name.endswith("nm"):
                comment = "Name field"
            elif col_name.endswith("_tp") or col_name.endswith("tp"):
                comment = "Type field"
            
            col_def = f"`{col_name}` {mysql_type}"
            if comment:
                col_def += f" COMMENT '{comment}'"
            columns.append(col_def)
        
        # Create table SQL
        create_sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` (\n"
        create_sql += ",\n".join(columns)
        
        # Add primary key
        if primary_key_cols:
            if len(primary_key_cols) == 1:
                create_sql += f",\nPRIMARY KEY (`{primary_key_cols[0]}`)"
            else:
                # For composite keys, check if we should use composite
                if table_name in composite_key_candidates:
                    composite_cols = composite_key_candidates[table_name]
                    existing_cols = [c for c in composite_cols if c in df_clean.columns]
                    if existing_cols:
                        create_sql += f",\nPRIMARY KEY (`{'`, `'.join(existing_cols)}`)"
                else:
                    create_sql += f",\nPRIMARY KEY (`{primary_key_cols[0]}`)"
        
        # Add table comment
        if table_comment:
            create_sql += f"\n) COMMENT='{table_comment}'"
        else:
            create_sql += "\n)"
        
        cursor.execute(create_sql)
        logger.info("created_table", table=table_name, columns=len(columns))
        
        # Create indexes for common query patterns
        create_indexes(conn, table_name, df_clean)
        
        # Insert data in batches
        if len(df_clean) > 0:
            cols = list(df_clean.columns)
            placeholders = ", ".join(["%s"] * len(cols))
            col_list = ", ".join([f"`{c}`" for c in cols])
            insert_sql = f"INSERT INTO `{table_name}` ({col_list}) VALUES ({placeholders})"
            
            # Convert DataFrame to list of tuples, replacing NaN with None
            values = []
            for _, row in df_clean.iterrows():
                row_values = []
                for val in row:
                    if pd.isna(val):
                        row_values.append(None)
                    else:
                        row_values.append(val)
                values.append(tuple(row_values))
            
            # Insert in batches
            batch_size = 1000
            for i in range(0, len(values), batch_size):
                batch = values[i : i + batch_size]
                cursor.executemany(insert_sql, batch)
            
            conn.commit()
            logger.info(
                "inserted_data",
                table=table_name,
                rows=len(df_clean),
                columns=len(df_clean.columns),
            )
        
    except Error as e:
        conn.rollback()
        logger.error("mysql_error", table=table_name, error=str(e))
        raise
    finally:
        cursor.close()


def create_indexes(conn: mysql.connector.connection, table_name: str, df: pd.DataFrame) -> None:
    """Create indexes on columns commonly used in queries."""
    cursor = conn.cursor()
    
    try:
        # Common columns to index based on query patterns
        index_columns = [
            "subjid",  # Most common join key
            "usubjid",  # Alternative subject identifier
            "visfwdid",  # Visit identifier
            "trt",  # Treatment arm
            "trtsort",  # Treatment sort order
            "ageyr",  # Age for filtering
            "sex",  # Gender for filtering
            "race",  # Race for filtering
            "aestdt",  # Event start date
            "aeendt",  # Event end date
            "visdt",  # Visit date
            "lsasmdt",  # Lesion assessment date
            "bordt",  # Best overall response date
        ]
        
        # Table-specific indexes
        table_specific_indexes = {
            "events": ["aeid", "aeseqid", "aeterm", "soccode", "ptcode"],
            "lesions": ["lsid", "lsname", "lsasmdt"],
            "visit": ["vistp", "visdt", "visendt"],
            "vitals": ["vstestcd", "vstest"],
            "cmtpy": ["cmid", "cmterm", "cmname"],
            "sdytrt": ["sdytrtid", "sdytrtname"],
            "ttevent": ["ttecd", "ttetest"],
        }
        
        # Get table-specific indexes
        if table_name in table_specific_indexes:
            index_columns.extend(table_specific_indexes[table_name])
        
        # Create indexes
        for col in index_columns:
            if col in df.columns:
                try:
                    index_name = f"idx_{table_name}_{col}"
                    cursor.execute(f"CREATE INDEX `{index_name}` ON `{table_name}` (`{col}`)")
                    logger.info("created_index", table=table_name, column=col)
                except Error as e:
                    logger.warning("index_creation_failed", table=table_name, column=col, error=str(e))
        
        # Create composite indexes for common query patterns
        composite_indexes = {
            "events": [("subjid", "aestdt"), ("subjid", "aeid")],
            "lesions": [("subjid", "lsasmdt")],
            "visit": [("subjid", "visdt")],
            "vitals": [("subjid", "visfwdid", "vstestcd")],
        }
        
        if table_name in composite_indexes:
            for idx_cols in composite_indexes[table_name]:
                existing_cols = [c for c in idx_cols if c in df.columns]
                if len(existing_cols) > 1:
                    idx_name = f"idx_{table_name}_{'_'.join(existing_cols)}"
                    cols_str = ", ".join([f"`{c}`" for c in existing_cols])
                    try:
                        cursor.execute(f"CREATE INDEX `{idx_name}` ON `{table_name}` ({cols_str})")
                        logger.info("created_composite_index", table=table_name, columns=existing_cols)
                    except Error as e:
                        logger.warning("composite_index_failed", table=table_name, error=str(e))
        
        conn.commit()
    finally:
        cursor.close()


# Table descriptions for LLM context
TABLE_DESCRIPTIONS = {
    "subjinfo": "Patient demographics and baseline information. One row per patient. Key fields: SUBJID (primary key), age, sex, race, treatment assignment.",
    "events": "Adverse events and safety data. Multiple rows per patient. Key fields: SUBJID, AEID, AESTDT (start date), AEENDT (end date), AETERM (event term), severity, seriousness flags.",
    "lesions": "Tumor lesion measurements and assessments. Multiple rows per patient/lesion. Key fields: SUBJID, LSID (lesion ID), LSASMDT (assessment date), lesion location, size measurements.",
    "visit": "Visit schedules and compliance data. Multiple rows per patient. Key fields: SUBJID, VISFWDID (visit ID), VISDT (visit date), visit type, phase.",
    "vitals": "Vital signs measurements (blood pressure, heart rate, temperature, etc.). Multiple rows per patient/visit. Key fields: SUBJID, VISFWDID, VSTESTCD (test code), VSTEST (test name), values.",
    "cmtpy": "Concomitant medications (other medications taken during study). Multiple rows per patient. Key fields: SUBJID, CMID, CMTERM (medication name), start/end dates.",
    "sdytrt": "Study treatment administration and dosing. Multiple rows per patient. Key fields: SUBJID, SDYTRTID, SDYTRTNAME, dose, administration dates.",
    "ttevent": "Time-to-event analyses (survival, progression, etc.). Multiple rows per patient. Key fields: SUBJID, TTECD (event code), TTESTDT (test date), censoring flags.",
    "disposit": "Patient disposition and study completion status. One row per patient. Key fields: SUBJID, disposition status, completion date, reason for discontinuation.",
    "bor": "Best Overall Response assessments. One row per patient. Key fields: SUBJID, BORCD (response code), BORDT (assessment date).",
    "diag": "Diagnostic information and medical history. One row per patient. Key fields: SUBJID, diagnosis date, stage, basis for diagnosis.",
    "syst": "System administration and metadata. Multiple rows per patient. Key fields: SUBJID, system treatment information.",
    "exsum": "Exposure summary and treatment duration. One row per patient. Key fields: SUBJID, exposure duration, mean dose, dose intervals.",
    "history": "Medical history and prior treatments. Multiple rows per patient. Key fields: SUBJID, HXID, HXTERM (history term), end date.",
    "pdsumm": "Progressive disease summaries. Multiple rows per patient. Key fields: SUBJID, VISFWDID, PDBASIS (basis for progression), assessment date.",
    "cmtpyatc": "ATC (Anatomical Therapeutic Chemical) codes for medications. Key fields: CMTERM, ATC codes at multiple levels.",
}


def migrate_sas_files(input_dir: str, mysql_host: str = "localhost") -> None:
    """
    Migrate all SAS files from directory to MySQL with optimized schema.
    
    Args:
        input_dir: Directory containing SAS files
        mysql_host: MySQL host
    """
    input_path = Path(input_dir)
    sas_files = list(input_path.glob("*.sas7bdat"))
    
    if not sas_files:
        logger.error("no_sas_files_found", input_dir=input_dir)
        return
    
    logger.info("migrating_sas_files_optimized", count=len(sas_files))
    
    try:
        conn = get_mysql_connection()
        logger.info("mysql_connected", host=mysql_host)
        
        # Create database if it doesn't exist
        db_name = os.getenv("MYSQL_DB", "cotrial_rag")
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        cursor.execute(f"USE `{db_name}`")
        cursor.close()
        logger.info("database_ready", database=db_name)
        
        # Process files in order: subjects first, then related tables
        priority_order = [
            "subjinfo",  # Base patient table
            "disposit",  # Disposition
            "bor",  # Best overall response
            "diag",  # Diagnosis
            "exsum",  # Exposure summary
            "visit",  # Visits
            "events",  # Adverse events
            "lesions",  # Lesions
            "vitals",  # Vital signs
            "cmtpy",  # Concomitant medications
            "sdytrt",  # Study treatment
            "ttevent",  # Time to event
            "syst",  # System
            "history",  # History
            "pdsumm",  # Progressive disease
            "cmtpyatc",  # ATC codes
        ]
        
        # Sort files by priority
        def get_priority(filename: str) -> int:
            stem = Path(filename).stem.lower()
            if stem in priority_order:
                return priority_order.index(stem)
            return len(priority_order)  # Unknown files go last
        
        sas_files_sorted = sorted(sas_files, key=lambda f: get_priority(str(f)))
        
        for sas_file in sas_files_sorted:
            table_name = sas_file.stem.lower()
            table_comment = TABLE_DESCRIPTIONS.get(table_name, f"Data from {sas_file.name}")
            
            logger.info("processing_file", file=str(sas_file), table=table_name)
            
            try:
                # Read SAS file
                df = read_sas_file(str(sas_file))
                if df.empty:
                    logger.warning("empty_dataframe", file=str(sas_file))
                    continue
                
                # Create table with optimized schema
                create_table_with_schema(
                    conn, table_name, df, table_comment=table_comment, if_exists="replace"
                )
                
                logger.info(
                    "migration_complete",
                    file=str(sas_file),
                    table=table_name,
                    rows=len(df),
                )
                
            except Exception as e:
                logger.error("migration_failed", file=str(sas_file), error=str(e))
                continue
        
        conn.close()
        logger.info("migration_all_complete", total_files=len(sas_files))
        
    except Error as e:
        logger.error("mysql_connection_failed", error=str(e))
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Migrate SAS files to MySQL with optimized schema")
    parser.add_argument("--input-dir", required=True, help="Directory containing SAS files")
    parser.add_argument("--mysql-host", default="localhost", help="MySQL host")
    
    args = parser.parse_args()
    
    migrate_sas_files(args.input_dir, args.mysql_host)


if __name__ == "__main__":
    main()

