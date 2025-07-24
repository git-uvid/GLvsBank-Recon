import pandas as pd
import numpy as np
import logging

# Import constants from config.py
from config import (
    BANK_CREDIT_AMOUNT_COL, BANK_DEBIT_AMOUNT_COL, BANK_TRN_TYPE_COL,
    GL_ACCOUNTED_CR_COL, GL_ACCOUNTED_DR_COL, GL_TYPE_COL
)

logger = logging.getLogger(__name__)

def create_bank_pivot(bank_df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates a pivot table for bank data, summarizing credit and debit amounts
    by 'TRN TYPE'.

    Args:
        bank_df (pd.DataFrame): The bank DataFrame, expected to have
                                'Credit amount', 'Debit amount', and 'TRN TYPE' columns.

    Returns:
        pd.DataFrame: A pivot table with 'Banking Credit amount', 'Banking Debit amount',
                      and 'Banking sum Cr Dr' columns.
    """
    logger.info("Creating bank pivot table.")
    bank_data_copy = bank_df.copy()

    # Ensure numeric types and fill NA
    for col in [BANK_DEBIT_AMOUNT_COL,BANK_CREDIT_AMOUNT_COL]:
        if col in bank_data_copy.columns:
            bank_data_copy[col] = pd.to_numeric(bank_data_copy[col], errors='coerce').fillna(0)
        else:
            logger.warning(f"Column '{col}' not found in bank data for pivot. Filling NA with 0.")

    # Calculate cr-dr (Credit - Debit)
    if BANK_CREDIT_AMOUNT_COL in bank_data_copy.columns and BANK_DEBIT_AMOUNT_COL in bank_data_copy.columns:
        bank_data_copy['cr-dr'] = bank_data_copy[BANK_CREDIT_AMOUNT_COL] - bank_data_copy[BANK_DEBIT_AMOUNT_COL]
    else:
        logger.error("Cannot calculate 'cr-dr': Missing Credit or Debit amount columns in bank data.")
        bank_data_copy['cr-dr'] = np.nan

    # Pivot table creation
    try:
        bank_pivot = pd.pivot_table(
            bank_data_copy,
            values=[BANK_DEBIT_AMOUNT_COL,BANK_CREDIT_AMOUNT_COL],
            index=BANK_TRN_TYPE_COL,
            aggfunc='sum',
            margins= True,
            margins_name='Total',
            fill_value=0
        )
        bank_pivot['sum Cr Dr'] = bank_pivot[BANK_CREDIT_AMOUNT_COL] + bank_pivot[BANK_DEBIT_AMOUNT_COL]
        bank_pivot.columns = ['Banking ' + col for col in bank_pivot.columns.values] # Flatten columns
        logger.info("Bank pivot table created successfully.")
        return bank_pivot
    except KeyError as e:
        logger.error(f"KeyError during bank pivot creation: {e}. Check column names.")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"An unexpected error occurred during bank pivot creation: {e}")
        return pd.DataFrame()

def create_gl_pivot(gl_df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates a pivot table for GL data, summarizing accounted credit and debit amounts
    by 'Type'.

    Args:
        gl_df (pd.DataFrame): The GL DataFrame, expected to have
                              'Accounted CR', 'Accounted DR', and 'Type' columns.

    Returns:
        pd.DataFrame: A pivot table with 'GL Accounted CR', 'GL Accounted DR',
                      and 'GL sum Accounted Cr Dr' columns.
    """
    logger.info("Creating GL pivot table.")
    gl_data_copy = gl_df.copy()

    # Ensure numeric types and fill NA
    for col in [GL_ACCOUNTED_CR_COL, GL_ACCOUNTED_DR_COL]:
        if col in gl_data_copy.columns:
            gl_data_copy[col] = pd.to_numeric(gl_data_copy[col], errors='coerce').fillna(0)
        else:
            logger.warning(f"Column '{col}' not found in GL data for pivot. Filling NA with 0.")

    # Pivot table creation
    try:
        gl_pivot = pd.pivot_table(
            gl_data_copy,
            values=[GL_ACCOUNTED_CR_COL, GL_ACCOUNTED_DR_COL],
            index=GL_TYPE_COL,
            aggfunc='sum',
            margins= True,
            margins_name='Total',
            fill_value=0
        )
        if GL_ACCOUNTED_DR_COL in gl_pivot.columns and GL_ACCOUNTED_CR_COL in gl_pivot.columns:
            gl_pivot['sum Accounted Cr Dr'] = gl_pivot[GL_ACCOUNTED_DR_COL] - gl_pivot[GL_ACCOUNTED_CR_COL]
        else:
            logger.error("Cannot calculate 'sum Accounted Cr Dr': Missing Accounted DR or CR columns in GL pivot.")
            gl_pivot['sum Accounted Cr Dr'] = np.nan
        gl_pivot.columns = ['GL ' + col for col in gl_pivot.columns.values]
        logger.info("GL pivot table created successfully.")
        return gl_pivot
    except KeyError as e:
        logger.error(f"KeyError during GL pivot creation: {e}. Check column names.")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"An unexpected error occurred during GL pivot creation: {e}")
        return pd.DataFrame()

def create_difference_grid(bank_pivot: pd.DataFrame, gl_pivot: pd.DataFrame) -> pd.DataFrame:
    """
    Creates a difference table by comparing 'Net_Sum' from bank and GL pivot tables.

    Args:
        bank_pivot (pd.DataFrame): The pivot table for bank data.
        gl_pivot (pd.DataFrame): The pivot table for GL data.

    Returns:
        pd.DataFrame: A DataFrame showing 'Bank Sum', 'GL Sum', and 'Difference'
                      by category (index).
    """
    logger.info("Creating difference grid between bank and GL pivot tables.")
    try:
        
        #bank_pivot = bank_pivot[bank_pivot['TRN TYPE'] != 'Total']
        bank_pivot = bank_pivot[bank_pivot.index != 'Total']
        bank_temp = bank_pivot[['Banking Credit amount', 'Banking Debit amount', 'Banking sum Cr Dr']].copy()
        bank_temp.columns = ['Credit', 'Debit', 'Net_Sum']

        gl_pivot = gl_pivot[gl_pivot.index != 'Total'] 
        gl_temp = gl_pivot[['GL Accounted CR', 'GL Accounted DR', 'GL sum Accounted Cr Dr']].copy()
        gl_temp.columns = ['Credit', 'Debit', 'Net_Sum']

        # Align indices (categories/types) for subtraction
        common_indices = bank_temp.index.union(gl_temp.index)

        bank_aligned = bank_temp.reindex(common_indices, fill_value=0)
        gl_aligned = gl_temp.reindex(common_indices, fill_value=0)

        difference_table = pd.DataFrame()
        difference_table['Bank Sum'] = bank_aligned['Net_Sum']
        difference_table['GL Sum'] = gl_aligned['Net_Sum']
        difference_table['Difference'] = difference_table['Bank Sum'] - difference_table['GL Sum']
        difference_table.index.name = "Type" # Consolidated name for difference table index
        # Add grand total row at the bottom
        total_row = pd.DataFrame(
            difference_table.sum(numeric_only=True)
        ).T
        total_row.index = ['Total']
        difference_table = pd.concat([difference_table, total_row])
        
        logger.info("Difference grid created successfully.")
        return difference_table
    except KeyError as e:
        logger.error(f"KeyError during difference grid creation: {e}. Check column names in pivot tables.")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"An unexpected error occurred during difference grid creation: {e}")
        return pd.DataFrame()