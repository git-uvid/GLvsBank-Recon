import pandas as pd
import numpy as np
import logging

# Import constants from config.py
from config import (
    GL_TRANSACTION_NUMBER_COL, OUTSTANDING_CHECK_NUMBER_COL, OUTSTANDING_AMOUNT_COL,
    OUTSTANDING_CLEARED_COL, OUTSTANDING_DATE_POSTED_COL, OUTSTANDING_VENDOR_NAME_COL,
    BANK_CREDIT_AMOUNT_COL, BANK_DEBIT_AMOUNT_COL, CUSTOMER_REFERENCE_COL,
    GL_TYPE_COL, COMMENT_GL_YES_BANK_NO, BANK_REFERENCE_COL, BANK_TRN_TYPE_COL
)

logger = logging.getLogger(__name__)


def get_party_dimension_table(gl_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts and cleans a dimension table for Party Number and Party Name
    from the GL DataFrame.

    Args:
        gl_df (pd.DataFrame): The GL DataFrame, expected to have
                              'Transaction Number', 'Party Number', 'Party Name' columns.

    Returns:
        pd.DataFrame: A DataFrame with unique 'Transaction Number', 'Party Name', 'Party Number'.
    """
    logger.info("Creating party dimension table.")
    
    required_cols = ['Transaction Number', 'Party Number', 'Party Name']
    if not all(col in gl_df.columns for col in required_cols):
        logger.error(f"Missing required columns for party dimension table: {required_cols}.")
        return pd.DataFrame()

    df_party_pname_trans = gl_df[required_cols].drop_duplicates().copy()

    df_party_pname_uniq = df_party_pname_trans[['Party Number', 'Party Name']].drop_duplicates()
    df_party_pname_uniq = df_party_pname_uniq[df_party_pname_uniq['Party Number'] != 'NA'].copy()

    df_partyname = df_party_pname_trans['Party Name'].drop_duplicates().to_frame()

    mrg_partynum_pname = pd.merge(df_partyname, df_party_pname_uniq, on='Party Name', how='left')

    mrg_party_pname_trans = pd.merge(df_party_pname_trans, mrg_partynum_pname, on='Party Name', how='left', suffixes=('_x', '_y'))
    mrg_part_pname_trans_nonull = mrg_party_pname_trans[mrg_party_pname_trans['Party Number_y'].notna()].copy()
    mrg_part_pname_trans_nonull = mrg_part_pname_trans_nonull.drop_duplicates(subset=['Transaction Number', 'Party Name'])

    df_trans_uniq = df_party_pname_trans['Transaction Number'].drop_duplicates().to_frame()

    mrg_final_party_df = pd.merge(df_trans_uniq ,mrg_part_pname_trans_nonull,
                                  how='left',
                                  on = 'Transaction Number',suffixes=('_x', '_y'))

    # Rename and drop cols in final party df
    if 'Party Number_x' in mrg_final_party_df.columns:
        mrg_final_party_df = mrg_final_party_df.drop('Party Number_x', axis=1)

    mrg_final_party_df.columns = [GL_TRANSACTION_NUMBER_COL, 'Party Name', 'Party Number'] # Ensure consistent naming
    mrg_final_party_df['Party Number'] = mrg_final_party_df['Party Number'].fillna("NA")

    logger.info("Party dimension table created successfully.")
    return mrg_final_party_df


def process_outstanding_bank_checks(outstanding_df: pd.DataFrame, bank_df: pd.DataFrame) -> pd.DataFrame:
    """
    Processes outstanding checks from a source DataFrame by merging with bank data
    to determine clearance status and variance.

    Args:
        outstanding_df (pd.DataFrame): DataFrame containing outstanding checks (e.g., from GL).
                                       Expected to have 'Check number', 'Amount'.
        bank_df (pd.DataFrame): Bank DataFrame, expected to have 'Customer reference',
                                'Credit amount', 'Debit amount'.

    Returns:
        pd.DataFrame: DataFrame with processed outstanding checks, including variance
                      and updated status.
    """
    logger.info("Processing outstanding bank checks.")
    
    # Ensure required columns exist
    if not all(col in outstanding_df.columns for col in [OUTSTANDING_CHECK_NUMBER_COL, OUTSTANDING_AMOUNT_COL]):
        logger.error(f"Missing required columns in outstanding_df for processing: '{OUTSTANDING_CHECK_NUMBER_COL}', '{OUTSTANDING_AMOUNT_COL}'.")
        return pd.DataFrame()
    if not all(col in bank_df.columns for col in [CUSTOMER_REFERENCE_COL, BANK_CREDIT_AMOUNT_COL, BANK_DEBIT_AMOUNT_COL]):
        logger.error(f"Missing required columns in bank_df for processing: '{CUSTOMER_REFERENCE_COL}', '{BANK_CREDIT_AMOUNT_COL}', '{BANK_DEBIT_AMOUNT_COL}'.")
        return pd.DataFrame()

    ost_bank_chks = pd.merge(
        outstanding_df,
        bank_df,
        left_on=OUTSTANDING_CHECK_NUMBER_COL,
        right_on=CUSTOMER_REFERENCE_COL,
        how='left',
        suffixes=('_ost', '_bank') # Add suffixes to avoid potential column name conflicts
    )

    

    # Ensure amount columns are numeric and fill NA
    for col in [OUTSTANDING_AMOUNT_COL, BANK_CREDIT_AMOUNT_COL, BANK_DEBIT_AMOUNT_COL]:
        if col in ost_bank_chks.columns:
            ost_bank_chks[col] = pd.to_numeric(ost_bank_chks[col], errors='coerce').fillna(0)
        else:
            logger.warning(f"Column '{col}' not found in merged outstanding checks for numeric conversion/NA fill.")


    # Calculate variance
    # Variance is Amount - (Credit + Debit) if matched in bank, else NaN
    ost_bank_chks['variance'] = np.where(
        pd.notnull(ost_bank_chks[CUSTOMER_REFERENCE_COL]),
        ost_bank_chks[OUTSTANDING_AMOUNT_COL] - ost_bank_chks[BANK_CREDIT_AMOUNT_COL] - ost_bank_chks[BANK_DEBIT_AMOUNT_COL],
        np.nan
    )

    # Determine updated status
    conditions = [
        (ost_bank_chks['variance'] == 0) & (pd.notnull(ost_bank_chks['variance'])),
        (ost_bank_chks['variance'] != 0) & (pd.notnull(ost_bank_chks['variance'])),
        pd.isna(ost_bank_chks['variance']) # If variance is NaN, it means no match in bank
    ]
    choices = [
        "Check cleared",
        "Check cleared but difference in transaction amount",
        "check not cleared"
    ]
    ost_bank_chks['updated status'] = np.select(conditions, choices, default="")

    # Update 'Cleared?' column
    ost_bank_chks[OUTSTANDING_CLEARED_COL] = np.where(ost_bank_chks['updated status'] == "Check cleared", "yes", 'no')
    logger.info("Outstanding bank checks processed.")

    #ost_bank_chks.to_excel('ost_test.xlsx', index= False)
    return ost_bank_chks


def get_new_outstanding_from_gl(comments_data: pd.DataFrame, existing_outstanding_df: pd.DataFrame, party_dim_df, gl_date_posted_df) -> pd.DataFrame:
    """
    Identifies new outstanding checks from GL data that are not present in
    the existing outstanding check report.

    Args:
        comments_data (pd.DataFrame): The DataFrame containing reconciliation comments,
                                      expected to have 'comment', 'Type', 'Transaction Number',
                                      'Accounted Sum'.
        existing_outstanding_df (pd.DataFrame): The DataFrame of already processed
                                                outstanding checks (from bank/GL merge).
                                                Expected to have 'Check number'.

    Returns:
        pd.DataFrame: DataFrame of newly identified outstanding checks from GL.
    """
    logger.info("Identifying new outstanding checks from GL not in existing report.")
    
    required_cols_comments = ['comment', GL_TYPE_COL, GL_TRANSACTION_NUMBER_COL, 'Accounted Sum']
    if not all(col in comments_data.columns for col in required_cols_comments):
        logger.error(f"Missing required columns in comments_data for new outstanding checks: {required_cols_comments}.")
        return pd.DataFrame()
    if OUTSTANDING_CHECK_NUMBER_COL not in existing_outstanding_df.columns:
        logger.error(f"Missing required column in existing_outstanding_df: '{OUTSTANDING_CHECK_NUMBER_COL}'.")
        return pd.DataFrame()
    
    # Filter GL data for checks not in bank statement
    trans_not_inbank = comments_data[
        (comments_data['comment'] == COMMENT_GL_YES_BANK_NO) &
        (comments_data[GL_TYPE_COL] == 'Checks')
    ].copy()

    trans_not_inbank_reqcols = trans_not_inbank[[GL_TRANSACTION_NUMBER_COL, 'Accounted Sum']]
    trans_not_inbank_reqcols_ost = trans_not_inbank_reqcols.copy()

    # Rename columns to match outstanding check report format
    trans_not_inbank_reqcols_ost.rename(columns={
        GL_TRANSACTION_NUMBER_COL: OUTSTANDING_CHECK_NUMBER_COL,
        'Transaction Date': 'Date posted',
        'Party Name': 'Vendor Name',
        'Accounted Sum': 'Amount'
    }, inplace=True)

    # Add default values for new outstanding checks
    #trans_not_inbank_reqcols_ost.loc[:, OUTSTANDING_CLEARED_COL] = 'no'
    if not trans_not_inbank_reqcols_ost.empty:
        trans_not_inbank_reqcols_ost.loc[:, OUTSTANDING_CLEARED_COL] = 'no'
    else:
        trans_not_inbank_reqcols_ost[OUTSTANDING_CLEARED_COL] = pd.Series(dtype='object')

    
    trans_not_inbank_reqcols_ost.loc[:, 'updated status'] = 'Check not cleared.New entires from gl'

    # Filter out checks already present in the existing outstanding report
    trans_not_inbank_reqcols_ost['Exists in Existing Outstanding'] = \
        trans_not_inbank_reqcols_ost[OUTSTANDING_CHECK_NUMBER_COL].isin(existing_outstanding_df[OUTSTANDING_CHECK_NUMBER_COL])
    
    new_ost_checks = trans_not_inbank_reqcols_ost[
        trans_not_inbank_reqcols_ost['Exists in Existing Outstanding'] == False
    ].drop('Exists in Existing Outstanding', axis=1).copy()

    logger.info(f"Identified {len(new_ost_checks)} new outstanding checks from GL.")

    
    cols_to_select = [GL_TRANSACTION_NUMBER_COL, 'Party Name'] + \
    [col for col in party_dim_df.columns if col.startswith('Bnk')] + \
    (['variance'] if 'variance' in party_dim_df.columns else [])
    party_dim_df = party_dim_df[cols_to_select]

     # Merge with party dim df to get vendor name
    if not party_dim_df.empty:
        new_ost_checks_final = pd.merge(
            new_ost_checks,
            party_dim_df[[GL_TRANSACTION_NUMBER_COL, 'Party Name']], # Only merge necessary columns
            left_on=OUTSTANDING_CHECK_NUMBER_COL,
            right_on=GL_TRANSACTION_NUMBER_COL,
            how='left',
            suffixes=('_current', '_party_dim') # Avoid column name conflicts
        )
    
    # Merge with date posted dim df
    if not gl_date_posted_df.empty:
        print( 'nOT EMPTY')
        new_ost_checks_final = pd.merge(
            new_ost_checks_final,
            gl_date_posted_df[[GL_TRANSACTION_NUMBER_COL, 'Transaction Date']], # Only merge necessary columns
            left_on=OUTSTANDING_CHECK_NUMBER_COL,
            right_on=GL_TRANSACTION_NUMBER_COL,
            how='left',
            suffixes=('_current', '_date_dim')
        )

        if OUTSTANDING_DATE_POSTED_COL not in new_ost_checks_final.columns:
            new_ost_checks_final[OUTSTANDING_DATE_POSTED_COL] = new_ost_checks_final['Transaction Date']

            new_ost_checks_final[OUTSTANDING_DATE_POSTED_COL] = np.where(
                new_ost_checks_final[OUTSTANDING_DATE_POSTED_COL].isnull(),
                new_ost_checks_final['Transaction Date'],
                new_ost_checks_final[OUTSTANDING_DATE_POSTED_COL]
            )

        new_ost_checks_final = new_ost_checks_final.drop(columns=['Transaction Date', GL_TRANSACTION_NUMBER_COL + '_date_dim'], errors='ignore')
    
    return new_ost_checks_final

def consolidate_outstanding_checks(
    ost_bank_chks: pd.DataFrame,
    new_gl_ost_chks: pd.DataFrame#,
    # party_dim_df: pd.DataFrame,
    # gl_date_posted_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Consolidates all outstanding checks, merges with party dimension and date posted data,
    and formats the final DataFrame.

    Args:
        ost_bank_chks (pd.DataFrame): DataFrame of outstanding checks processed against bank.
        new_gl_ost_chks (pd.DataFrame): DataFrame of new outstanding checks from GL.
        party_dim_df (pd.DataFrame): Party dimension DataFrame.
        gl_date_posted_df (pd.DataFrame): GL DataFrame with Transaction Number and Transaction Date.

    Returns:
        pd.DataFrame: Final consolidated and formatted outstanding checks DataFrame.
    """
    logger.info("Consolidating and formatting outstanding checks.")
    
    # Ensure columns exist before concatenation
    # Align columns before concat to avoid issues if one df has more columns than other
    common_cols = list(set(ost_bank_chks.columns) & set(new_gl_ost_chks.columns))
    
    # Ensure 'Amount', 'Credit amount', 'Debit amount' are numeric before fillna
    for df in [ost_bank_chks, new_gl_ost_chks]:
        for col in [OUTSTANDING_AMOUNT_COL, BANK_CREDIT_AMOUNT_COL, BANK_DEBIT_AMOUNT_COL]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')


    #ost_bank_chks_final = pd.concat([ost_bank_chks[common_cols], new_gl_ost_chks[common_cols]], ignore_index=True)
    ost_bank_chks_final = pd.concat([ost_bank_chks, new_gl_ost_chks], ignore_index=True)
    # Fill NA for amount columns after concat
    for col in [OUTSTANDING_AMOUNT_COL, BANK_CREDIT_AMOUNT_COL, BANK_DEBIT_AMOUNT_COL]:
        if col in ost_bank_chks_final.columns:
            ost_bank_chks_final[col] = ost_bank_chks_final[col].fillna(0)


    # # Merge with party dim df to get vendor name
    # if not party_dim_df.empty:
    #     ost_bank_chks_final = pd.merge(
    #         ost_bank_chks_final,
    #         party_dim_df[[GL_TRANSACTION_NUMBER_COL, 'Party Name']], # Only merge necessary columns
    #         left_on=OUTSTANDING_CHECK_NUMBER_COL,
    #         right_on=GL_TRANSACTION_NUMBER_COL,
    #         how='left',
    #         suffixes=('_current', '_party_dim') # Avoid column name conflicts
    #     )

        

    ost_bank_chks_final[OUTSTANDING_VENDOR_NAME_COL] = np.where(
    ost_bank_chks_final['Vendor Name'].isnull() ,
    ost_bank_chks_final[OUTSTANDING_VENDOR_NAME_COL],
    ost_bank_chks_final['Vendor Name']
    )

    #ost_bank_chks_final.to_excel('ost_test.xlsx', index=False)

    #     ost_bank_chks_final = ost_bank_chks_final.drop(columns=[ GL_TRANSACTION_NUMBER_COL + '_party_dim'], errors='ignore')
    # else:
    #     logger.warning("Party dimension DataFrame is empty. Skipping merge for Vendor Name.")

    

    # # Merge with date posted dim df
    # if not gl_date_posted_df.empty:
    #     ost_bank_chks_final = pd.merge(
    #         ost_bank_chks_final,
    #         gl_date_posted_df[[GL_TRANSACTION_NUMBER_COL, 'Transaction Date']], # Only merge necessary columns
    #         left_on=OUTSTANDING_CHECK_NUMBER_COL,
    #         right_on=GL_TRANSACTION_NUMBER_COL,
    #         how='left',
    #         suffixes=('_current', '_date_dim')
    #     )

    #     ost_bank_chks_final[OUTSTANDING_DATE_POSTED_COL] = np.where(
    #         ost_bank_chks_final[OUTSTANDING_DATE_POSTED_COL].isnull(),
    #         ost_bank_chks_final['Transaction Date'],
    #         ost_bank_chks_final[OUTSTANDING_DATE_POSTED_COL]
    #     )
    #     ost_bank_chks_final = ost_bank_chks_final.drop(columns=['Transaction Date', GL_TRANSACTION_NUMBER_COL + '_date_dim'], errors='ignore')
    # else:
    #     logger.warning("GL Date Posted DataFrame is empty. Skipping merge for Date posted.")


    # Define the final desired column order for the output
    final_cols_order = [
        OUTSTANDING_CHECK_NUMBER_COL, OUTSTANDING_DATE_POSTED_COL, OUTSTANDING_VENDOR_NAME_COL, OUTSTANDING_AMOUNT_COL,
        OUTSTANDING_CLEARED_COL, BANK_REFERENCE_COL, CUSTOMER_REFERENCE_COL, BANK_TRN_TYPE_COL, 'TRN status',
        'Value date', BANK_CREDIT_AMOUNT_COL, BANK_DEBIT_AMOUNT_COL, 'Time', 'Post date', 'comparsion_key',
        'variance', 'updated status'
    ]
    
    # Filter and reorder columns, handling cases where columns might be missing
    final_df_cols = [col for col in final_cols_order if col in ost_bank_chks_final.columns]
    ost_bank_chks_final = ost_bank_chks_final[final_df_cols].copy()

    logger.info("Outstanding checks consolidation complete.")
    return ost_bank_chks_final
