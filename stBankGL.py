import pandas as pd
import numpy as np
import difflib
import re
import logging

# Import constants from config.py
from config import (
    GL_TRANSACTION_NUMBER_COL, GL_COLUMNS_TO_FILL_NA, BANK_REFERENCE_COL,
    CUSTOMER_REFERENCE_COL, BANK_CREDIT_AMOUNT_COL, BANK_DEBIT_AMOUNT_COL,
    GL_ACCOUNTED_SUM_COL, BANK_COMPARISON_KEY_COL, GL_NO_TRANS_NUMBER,
    NO_REFERENCE_NUMBER, COMMENT_GL_NO_BANK_YES, COMMENT_GL_YES_BANK_NO,
    COMMENT_FULL_MATCH, COMMENT_PARTIAL_MATCH, BANK_TRN_TYPE_COL,BANK_CATEGORY_LIST,
    DESCRIPTION_COL,DESC_CHECK_SEARCH1,DESC_CHECK_SEARCH2
)

# Configure logging
logger = logging.getLogger(__name__)

def fill_transaction_number_basedonDesc(df:pd.DataFrame,transCol:str,descCol:str,
                                        descSearch1:str,descSearch2:str) ->pd.DataFrame:
    """
    Fills transaction number based on the description Manual checks and CK#
    This function is specifically implemented to handle check reversals

    Args:
    df : Input data frame
    transCol: transaction number column
    descCol: Description column
    """
    logger.info("get transaction number from CK#")

    def extract_ck(desc: str) -> str:
        lower_desc = desc.lower()
        if descSearch1.lower() in lower_desc and descSearch2.lower() in lower_desc:
            match = re.search(pattern, desc,flags=re.IGNORECASE)
            if match and len(match.group(1).strip()) <= 9:
                return match.group(1).strip()
            return None
            
    if descCol in df.columns and transCol in df.columns:
        df = df.copy()
        pattern = rf"{descSearch2}\s*(\S+)"
        # Ensure text data
        df[transCol] = df[transCol].fillna('').astype(str)
        df[descCol] = df[descCol].fillna('').astype(str)
        mask = df[transCol].isin(['', 'No_Transaction_Number']) | df[transCol].isna()
        extracted = df.loc[mask, descCol].apply(extract_ck)
        df.loc[mask & extracted.notna(), transCol] = extracted
        logger.info("Completed CK# extraction and DataFrame update.")
        
        return df

    else:
        logger.error(f"Require column '{descCol}' or '{transCol}' not found in DataFrame.")
        return df  

def handle_missing_transaction_numbers(df: pd.DataFrame, col: str, tag: str) -> pd.DataFrame:
    """
    
    Fills missing or empty values in a specified column with a generated unique tag.
    This function operates on a copy of the DataFrame to avoid modifying the original
    DataFrame in-place, which is generally better for predictability and testing.

    Args:
        df (pd.DataFrame): The input DataFrame.
        col (str): The name of the column to process for missing values.
        tag (str): A tag prefix for the generated missing value string (e.g., "Tr").

    Returns:
        pd.DataFrame: A new DataFrame with missing values handled.
    """
    logger.info(f"Handling missing elements in column '{col}' with tag '{tag}'.")
    data_copy = df.copy()



    missing_indices = data_copy[data_copy[col].isna() | (data_copy[col] == '')].index
    
    if not missing_indices.empty:
        logger.info(f"Found {len(missing_indices)} missing values in '{col}'. Filling them.")
        # Generate unique missing tags for each missing value
        for i, index in enumerate(missing_indices):
            data_copy.at[index, col] = f"Missing {tag} No.{i + 1}"
    else:
        logger.info(f"No missing values found in column '{col}'.")
        
    return data_copy

def create_bank_comparison_key(row: pd.Series) -> str:
    """
    Creates a comparison key for bank data based on 'Bank reference' and 'Customer reference'.

    Args:
        row (pd.Series): A row from the bank DataFrame.

    Returns:
        str: The comparison key.
    """
    if row[BANK_TRN_TYPE_COL] == BANK_CATEGORY_LIST[3]: #condition for checks
        return row[CUSTOMER_REFERENCE_COL]
    elif row[BANK_TRN_TYPE_COL] == BANK_CATEGORY_LIST[14]: #condition for wire
        return row[BANK_REFERENCE_COL]
    elif row[BANK_REFERENCE_COL] == "NONREF":
        return row[CUSTOMER_REFERENCE_COL]
    else:
        return row[BANK_REFERENCE_COL]

def filter_dataframe_by_column_values(df: pd.DataFrame, col: str, filter_list: list) -> pd.DataFrame:
    """
    Filters a DataFrame to include only rows where the specified column's value
    is present in the given filter list.

    Args:
        df (pd.DataFrame): The input DataFrame.
        col (str): The name of the column to filter by.
        filter_list (list): A list of values to keep in the specified column.

    Returns:
        pd.DataFrame: A new DataFrame containing only the filtered rows.
    """
    logger.info(f"Filtering DataFrame by column '{col}' for values in {filter_list}.")
    if col not in df.columns:
        logger.warning(f"Column '{col}' not found in DataFrame for filtering.")
        return df.copy() # Return a copy to maintain consistency
    
    return df[df[col].isin(filter_list)].copy()

def calculate_variance_and_comments(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the variance between 'Accounted Sum' and 'Bnk Accounted Sum'
    and assigns comments based on matching criteria.

    Args:
        df (pd.DataFrame): The input DataFrame, expected to have
                           'Accounted Sum', 'Credit amount', 'Debit amount',
                           'Transaction Number', and 'comparsion_key' columns.

    Returns:
        pd.DataFrame: A new DataFrame with 'Bnk Accounted Sum', 'variance', and 'comment' columns added.
    """
    logger.info("Calculating variance and assigning comments to matched data.")
    data_copy = df.copy()

    # Handle missing values for calculations
    cols_to_fill_zero = [GL_ACCOUNTED_SUM_COL, BANK_CREDIT_AMOUNT_COL, BANK_DEBIT_AMOUNT_COL]
    for col in cols_to_fill_zero:
        if col in data_copy.columns:
            data_copy[col] = pd.to_numeric(data_copy[col], errors='coerce').fillna(0)
        else:
            logger.warning(f"Column '{col}' not found for filling NA with 0.")

    # Add Bank_Accounted Sum
    data_copy['Bnk Accounted Sum'] = data_copy[BANK_CREDIT_AMOUNT_COL] + data_copy[BANK_DEBIT_AMOUNT_COL]

    # Fill missing transaction numbers and comparison keys
    if GL_TRANSACTION_NUMBER_COL in data_copy.columns:
        data_copy[GL_TRANSACTION_NUMBER_COL] = data_copy[GL_TRANSACTION_NUMBER_COL].fillna(GL_NO_TRANS_NUMBER)
    else:
        logger.warning(f"Column '{GL_TRANSACTION_NUMBER_COL}' not found for filling NA.")

    if BANK_COMPARISON_KEY_COL in data_copy.columns:
        data_copy[BANK_COMPARISON_KEY_COL] = data_copy[BANK_COMPARISON_KEY_COL].fillna(NO_REFERENCE_NUMBER)
    else:
        logger.warning(f"Column '{BANK_COMPARISON_KEY_COL}' not found for filling NA.")

    # Calculate variance
    if GL_ACCOUNTED_SUM_COL in data_copy.columns:
        data_copy['variance'] = data_copy[GL_ACCOUNTED_SUM_COL] - data_copy['Bnk Accounted Sum']
    else:
        logger.error(f"Cannot calculate variance: '{GL_ACCOUNTED_SUM_COL}' column missing.")
        data_copy['variance'] = np.nan # Assign NaN if column is missing

    # Assign comments based on conditions
    conditions = [
        data_copy[GL_TRANSACTION_NUMBER_COL] == GL_NO_TRANS_NUMBER,
        data_copy[BANK_COMPARISON_KEY_COL] == NO_REFERENCE_NUMBER,
        data_copy['variance'] == 0,
        data_copy['variance'] != 0
    ]
    choices = [
        COMMENT_GL_NO_BANK_YES,
        COMMENT_GL_YES_BANK_NO,
        COMMENT_FULL_MATCH,
        COMMENT_PARTIAL_MATCH
    ]
    data_copy['comment'] = np.select(conditions, choices, default="")

    logger.info("Variance and comments calculation complete.")
    return data_copy

def clean_and_prepare_gl_bank_data(gl_df: pd.DataFrame, bank_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Performs initial cleaning and preparation steps for GL and Bank DataFrames.

    Args:
        gl_df (pd.DataFrame): The GL DataFrame.
        bank_df (pd.DataFrame): The Bank DataFrame.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: Cleaned GL and Bank DataFrames.
    """
    logger.info("Starting initial cleaning and preparation of GL and Bank data.")

    gl_withtrans_basedonDesc = fill_transaction_number_basedonDesc(gl_df,GL_TRANSACTION_NUMBER_COL,DESCRIPTION_COL,
                                                                   DESC_CHECK_SEARCH1,DESC_CHECK_SEARCH2)

    # Handle missing transaction numbers in GL
    gl_df_cleaned = handle_missing_transaction_numbers(gl_withtrans_basedonDesc, GL_TRANSACTION_NUMBER_COL, 'Tr')

    # Fill other specified GL missing columns with 'NA'
    for col in GL_COLUMNS_TO_FILL_NA:
        if col in gl_df_cleaned.columns:
            gl_df_cleaned[col] = gl_df_cleaned[col].fillna('NA')
        else:
            logger.warning(f"Column '{col}' not found in GL data for filling with 'NA'.")

    # Remove leading zeroes from reference columns
    for col in [GL_TRANSACTION_NUMBER_COL]:
        if col in gl_df_cleaned.columns:
            gl_df_cleaned[col] = gl_df_cleaned[col].astype(str).str.lstrip('0')
        else:
            logger.warning(f"Column '{col}' not found in GL data for stripping leading zeros.")

    

    for col in [BANK_REFERENCE_COL, CUSTOMER_REFERENCE_COL]:
        if col in bank_df.columns:
            bank_df[col] = bank_df[col].astype(str).str.lstrip('0')
        else:
            logger.warning(f"Column '{col}' not found in Bank data for stripping leading zeros.")

    logger.info("Initial cleaning and preparation complete.")
    return gl_df_cleaned, bank_df

def rename_bank_trn_type(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renames specific 'TRN TYPE' values in the bank DataFrame.

    Args:
        df (pd.DataFrame): The bank DataFrame.

    Returns:
        pd.DataFrame: DataFrame with 'TRN TYPE' renamed.
    """
    logger.info("Renaming 'TRN TYPE' in bank data.")

    def find_best_match(value)->str:
        str_value = value
        best_match = str_value
        highest_ratio = 0.0

        for category in category_list_str:
            ratio = difflib.SequenceMatcher(None,str_value,category).ratio()
            if ratio > highest_ratio:
                highest_ratio = ratio
                best_match = category
        if highest_ratio >= threshold_match:
            return best_match
        else:
            return value
        
    data_copy = df.copy()
    if BANK_TRN_TYPE_COL in data_copy.columns:
        category_list_str = BANK_CATEGORY_LIST
        threshold_match = 0.80

        #Fill empty transaction type with NoCategory
        data_copy[BANK_TRN_TYPE_COL] = data_copy[BANK_TRN_TYPE_COL].fillna("NoCategory")
        #Find the best match
        data_copy[BANK_TRN_TYPE_COL] = data_copy[BANK_TRN_TYPE_COL].apply(find_best_match)

        data_copy.to_excel('banktrantype_modified.xlsx')
        """"
        if BANK_TRN_TYPE_COL in data_copy.columns:
            data_copy[BANK_TRN_TYPE_COL] = np.where(
            data_copy[BANK_TRN_TYPE_COL] == "AR Module", 'AR',
            np.where(data_copy[BANK_TRN_TYPE_COL] == "Autodebits", 'Autodebit', data_copy[BANK_TRN_TYPE_COL])
        )"""
    else:
        logger.error(f"Column '{BANK_TRN_TYPE_COL}' not found for renaming TRN types.")
    return data_copy

    