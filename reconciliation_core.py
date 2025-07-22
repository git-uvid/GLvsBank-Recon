import pandas as pd
import io
import logging

# Import functions from other modules
from stCreatePivot import create_bank_pivot, create_gl_pivot, create_difference_grid
from stExportXl import write_reconciliation_summary_sheet, export_formatted_excel, get_comment_format_style
from stBankGL import clean_and_prepare_gl_bank_data, create_bank_comparison_key, calculate_variance_and_comments, rename_bank_trn_type
from stOutstanding import get_party_dimension_table, process_outstanding_bank_checks, get_new_outstanding_from_gl, consolidate_outstanding_checks
from category_gl import gl_type

# Import constants from config.py
from config import (
    GL_TRANSACTION_NUMBER_COL, GL_ACCOUNTED_SUM_COL, BANK_COMPARISON_KEY_COL,
    GL_TYPE_COL, BANK_TRN_TYPE_COL, PIVOT_SHEET_NAME, GL_VS_BANK_SHEET_NAME,
    OUTSTANDING_CHECK_SHEET_NAME, HEADER_BG_COLOR_PIVOT, HEADER_TEXT_COLOR_PIVOT,
    DATA_CELL_BORDER_COLOR_PIVOT, HEADER_BG_COLOR_RECON, HEADER_TEXT_COLOR_RECON,
    BANK_REFERENCE_COL, CUSTOMER_REFERENCE_COL, GL_VS_BANK_COL
)

logger = logging.getLogger(__name__)

def run_full_reconciliation(gl_df: pd.DataFrame, bank_df: pd.DataFrame, outstanding_df: pd.DataFrame) -> io.BytesIO | None:
    """
    Orchestrates the entire bank reconciliation process.
    Performs data cleaning, matching, pivot table generation, and prepares an Excel report.

    Args:
        gl_df (pd.DataFrame): The raw GL DataFrame.
        bank_df (pd.DataFrame): The raw Bank DataFrame.
        outstanding_df (pd.DataFrame): The raw Outstanding Checks DataFrame.

    Returns:
        io.BytesIO | None: BytesIO object of the Excel report if successful, None otherwise.
    """
    logger.info("Starting comprehensive reconciliation process.")
    try:
        # 1. Clean and prepare GL and Bank data
        gl_cleaned, bank_cleaned = clean_and_prepare_gl_bank_data(gl_df, bank_df)
        bank_cleaned = rename_bank_trn_type(bank_cleaned)
        bank_cleaned[BANK_COMPARISON_KEY_COL] = bank_cleaned.apply(create_bank_comparison_key, axis=1)
        
        # Add Type Column in GL
        
        # gl_cleaned = gl_type(gl_cleaned, bank_cleaned)
        # logger.info(f"Added '{GL_TYPE_COL}' in GL")

        logger.info("GL and Bank data cleaned and prepared.")

        # 2. Aggregate GL data
        gl_cleaned[GL_ACCOUNTED_SUM_COL] = pd.to_numeric(gl_cleaned[GL_ACCOUNTED_SUM_COL], errors="coerce")
        

        gl_agg = gl_cleaned.groupby([
            'CO', 'AU', 'Acct', 'Sub Acct', 'Project', 'Period Name','Source',
            GL_TRANSACTION_NUMBER_COL, GL_TYPE_COL,
        ], as_index=False)[GL_ACCOUNTED_SUM_COL].sum()
        gl_agg = gl_agg[gl_agg[GL_ACCOUNTED_SUM_COL] != 0].copy() # Filter out zero accounted sum
        logger.info("GL data aggregated.")

          
        # 3. Merge GL and bank data for matching
        matched_gl_bank = pd.merge(
            gl_agg,
            bank_cleaned,
            left_on=GL_TRANSACTION_NUMBER_COL,
            right_on=BANK_COMPARISON_KEY_COL,
            how='outer'
        )
        
        matched_gl_bank_with_comments = calculate_variance_and_comments(matched_gl_bank)
        logger.info("GL and Bank data matched and comments generated.")


        # 4. Format matched GL and bank data for export
        matched_gl_bank_formatted = matched_gl_bank_with_comments.copy()
        # Drop columns that are no longer needed or will be consolidated
        matched_gl_bank_formatted.drop(columns=[BANK_REFERENCE_COL, CUSTOMER_REFERENCE_COL], errors='ignore', inplace=True)
        
        # Consolidate 'Type' and 'TRN TYPE' into 'Key_Type'
        matched_gl_bank_formatted[GL_TYPE_COL] = matched_gl_bank_formatted[GL_TYPE_COL].fillna(matched_gl_bank_formatted[BANK_TRN_TYPE_COL])
        matched_gl_bank_formatted.drop(columns=[BANK_TRN_TYPE_COL], errors='ignore', inplace=True)

        # Rename columns for clarity in the output report
        matched_gl_bank_formatted.columns = [
             'GL_CO', 'GL_AU', 'GL_Acct', 'GL_Sub Acct', 'GL_Project',
            'GL_Period Name','GL_Source','Key_Type','Key_Transaction Number', 'GL_Accounted Sum', 'Bnk_TRN status',
            'Bnk_Value date', 'Bnk_Credit amount', 'Bnk_Debit amount','Bnk_Time', 'Bnk_Post date', 'Bnk_Comparsion_Key','Bnk_Accounted Sum',
            'variance', 'comment'
        ]

        # Reorder columns for clarity in the output report
        matched_gl_bank_formatted = matched_gl_bank_formatted.reindex(columns=GL_VS_BANK_COL, fill_value='')


        # Apply styling for the 'comment' column
        styled_matched_gl_bank = matched_gl_bank_formatted.style.map(get_comment_format_style, subset=['comment']) \
                                .set_properties(**{'border': '1px solid black', 'border-color': 'black'})
        logger.info("Matched GL and Bank data formatted.")


        # 5. Process Outstanding Checks
        # Get party dimension table
        mrg_final_party_df = get_party_dimension_table(gl_cleaned)
        


        # Prepare date posted dim table

        dateposted_req_cols = gl_cleaned[[GL_TRANSACTION_NUMBER_COL, 'Transaction Date', GL_TYPE_COL]]
        dateposted_req_cols = dateposted_req_cols[dateposted_req_cols[GL_TYPE_COL] == 'Checks']
        dateposted_req_cols = dateposted_req_cols[[GL_TRANSACTION_NUMBER_COL, 'Transaction Date']].drop_duplicates()


        # Process existing outstanding checks against bank data
        ost_bank_chks = process_outstanding_bank_checks(outstanding_df, bank_cleaned)

        # Identify new outstanding checks from GL
        trans_not_inbank_reqcols_ost = get_new_outstanding_from_gl(matched_gl_bank_with_comments, ost_bank_chks)

        # Consolidate all outstanding checks and merge with dimension tables
        ost_bank_chks_final = consolidate_outstanding_checks(
            ost_bank_chks,
            trans_not_inbank_reqcols_ost,
            mrg_final_party_df,
            dateposted_req_cols
        )
        styled_ost_bank_chks = ost_bank_chks_final.style \
            .set_properties(**{'border': '1px solid black', 'border-color': 'black'})
        logger.info("Outstanding checks processed and consolidated.")

        # 6. Create Pivot Tables
        bank_pivot = create_bank_pivot(bank_cleaned)
        gl_pivot = create_gl_pivot(gl_cleaned)
        diff_grid = create_difference_grid(bank_pivot, gl_pivot)
        logger.info("Pivot tables created.")

        # 7. Orchestrate Excel Writing
        output_buffer = io.BytesIO()
        writer = pd.ExcelWriter(output_buffer, engine='xlsxwriter')

        # Write the combined reconciliation summary sheet (pivot tables)
        summary_sheet_write_status = write_reconciliation_summary_sheet(
            writer,
            bank_pivot,
            gl_pivot,
            diff_grid,
            sheet_name=PIVOT_SHEET_NAME,
            header_bg_color=HEADER_BG_COLOR_PIVOT,
            header_text_color=HEADER_TEXT_COLOR_PIVOT,
            data_cell_border_color=DATA_CELL_BORDER_COLOR_PIVOT,
            spacing_rows = 2,
            spacing_cols = 2
        )
        if summary_sheet_write_status == False:
            logger.error("Failed to write reconciliation summary sheet.")
            writer.close()
            return None

        # Prepare other dataframes for export
        #dataframes_to_export = {
           # GL_VS_BANK_SHEET_NAME: styled_matched_gl_bank,
           # OUTSTANDING_CHECK_SHEET_NAME: styled_ost_bank_chks
        #}

        dataframes_to_export = {
            GL_VS_BANK_SHEET_NAME: styled_matched_gl_bank,
            OUTSTANDING_CHECK_SHEET_NAME: styled_ost_bank_chks
        }



        # Write other sheets using the same writer
        other_sheets_export_status = export_formatted_excel(
            dataframes_to_export,
            writer_obj=writer,
            header_bg_color=HEADER_BG_COLOR_RECON,
            header_text_color=HEADER_TEXT_COLOR_RECON,
        )

        if other_sheets_export_status == False:
            logger.error("Failed to export other formatted Excel sheets.")
            writer.close()
            return None

        writer.close()
        output_buffer.seek(0)
        logger.info("Excel report generated successfully.")
        return output_buffer

    except Exception as e:
        logger.error(f"An unhandled error occurred during the full reconciliation process: {e}", exc_info=True)
        return None