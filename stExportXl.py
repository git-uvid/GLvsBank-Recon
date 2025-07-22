import pandas as pd
import streamlit as st
import io
import logging

# Import constants from config.py
from config import (
    COMMENT_FULL_MATCH, COMMENT_GL_YES_BANK_NO, COMMENT_PARTIAL_MATCH,
    HEADER_BG_COLOR_PIVOT, HEADER_TEXT_COLOR_PIVOT, DATA_CELL_BORDER_COLOR_PIVOT,
    HEADER_BG_COLOR_RECON, HEADER_TEXT_COLOR_RECON, DATA_CELL_BORDER_COLOR_RECON,
    GL_VS_BANK_SHEET_NAME, OUTSTANDING_CHECK_SHEET_NAME, # Import sheet names
    CURRENCY_COLUMNS
)

logger = logging.getLogger(__name__)


def get_comment_format_style(comment: str) -> str:
    """
    Returns CSS style string based on the comment value for conditional formatting.
    This function is primarily used for pandas Styler objects.

    Args:
        comment (str): The comment string.

    Returns:
        str: CSS style string.
    """
    if comment == COMMENT_FULL_MATCH:
        return 'background-color: green; color: white'
    elif comment == COMMENT_GL_YES_BANK_NO:
        return 'background-color: blue; color: white'
    elif comment == COMMENT_PARTIAL_MATCH:
        return 'background-color: yellow; color: Black'
    else:
        return 'background-color: red; color: white'

def write_reconciliation_summary_sheet(
    writer: pd.ExcelWriter,
    bank_pivot_df: pd.DataFrame,
    gl_pivot_df: pd.DataFrame,
    difference_df: pd.DataFrame,
    sheet_name: str = "pivot",
    header_bg_color: str = HEADER_BG_COLOR_PIVOT,
    header_text_color: str = HEADER_TEXT_COLOR_PIVOT,
    data_cell_border_color: str = DATA_CELL_BORDER_COLOR_PIVOT,
    spacing_rows: int = 2,
    spacing_cols: int = 2,
) -> bool:
    """
    Writes reconciliation summary (Bank Pivot, GL Pivot, Difference Grid)
    to a single Excel sheet with formatting.

    Args:
        writer (pd.ExcelWriter): An existing pd.ExcelWriter object.
        bank_pivot_df (pd.DataFrame): DataFrame for Bank Pivot Summary.
        gl_pivot_df (pd.DataFrame): DataFrame for GL Pivot Summary.
        difference_df (pd.DataFrame): DataFrame for Category Variance.
        sheet_name (str): Name of the sheet to write to.
        header_bg_color (str): Background color for headers.
        header_text_color (str): Text color for headers.
        data_cell_border_color (str): Border color for data cells.
        spacing_rows (int): Number of empty rows between tables.
        spacing_cols (int): Number of empty columns between tables.

    Returns:
        bool: True if successful, False otherwise.
    """
    logger.info(f"Writing reconciliation summary to sheet: '{sheet_name}'.")
    try:
        workbook = writer.book
        worksheet = workbook.add_worksheet(sheet_name)

        # --- Define Formats ---
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'vcenter',
            'align': 'center',
            'fg_color': header_bg_color,
            'font_color': header_text_color,
            'border': 1
        })

        # Data cell format (for non-currency, no border here, border applied conditionally)
        data_cell_format = workbook.add_format({}) # No border here

        # Number format for currency in pivot sheet (no border here, border applied conditionally)
        currency_format = workbook.add_format({
            'num_format': '$#,##0.00', # Dollar sign, comma separator, 2 decimal places
        })

        # Format specifically for applying borders to non-empty data cells
        border_only_format = workbook.add_format({
            'border': 1,
            'border_color': data_cell_border_color
        })

        # --- Determine Placement for each table ---
        tables_to_export_and_layout = [
            {'df': bank_pivot_df, 'name': 'Bank Pivot Summary'},
            {'df': gl_pivot_df, 'name': 'GL Pivot Summary'},
            {'df': difference_df, 'name': 'Category Variance'}
        ]

        table_dims = []
        for item in tables_to_export_and_layout:
            df_curr = item['df']
            # +1 for header row, +1 for index column if present
            height = len(df_curr) + 1
            width = len(df_curr.columns) + (1 if df_curr.index.name else 0)
            table_dims.append({'height': height, 'width': width})

        # Calculate positions: (start_row, start_col)
        # Assuming tables are placed side-by-side on the first row, then below
        bank_pivot_pos = (1, 0) # Data starts at row 1 (0-indexed) after a title row
        gl_pivot_pos = (1, table_dims[0]['width'] + spacing_cols)

        # Max height of the top row tables to determine start of the next row
        max_height_top_row = max(table_dims[0]['height'], table_dims[1]['height'])
        difference_table_pos = (max_height_top_row + spacing_rows + 1, 0) # +1 for table title

        all_positions = [bank_pivot_pos, gl_pivot_pos, difference_table_pos]

        # --- Write each table to the single sheet ---
        for i, item in enumerate(tables_to_export_and_layout):
            df_to_write = item['df']
            table_name = item['name']
            start_row, start_col = all_positions[i]

            logger.debug(f"Writing '{table_name}' to Excel. Columns: {df_to_write.columns.tolist()}, Dtypes: {df_to_write.dtypes.to_dict()}")


            # Write table name (title) above the table
            worksheet.write(start_row - 1, start_col, table_name, workbook.add_format({'bold': True, 'font_size': 12}))

            # Write DataFrame to Excel, excluding header and index for now
            # We'll write header and index separately for custom formatting
            df_to_write.to_excel(writer, sheet_name=sheet_name, index=True, header=False,
                                 startrow=start_row + 1, startcol=start_col, na_rep='')

            # Write custom index header if exists
            if df_to_write.index.name:
                worksheet.write(start_row, start_col, df_to_write.index.name, header_format)
            else:
                # If no index name, write a generic "Index" or leave blank based on preference
                worksheet.write(start_row, start_col, "Index", header_format)


            # Write custom column headers
            for col_num, value in enumerate(df_to_write.columns.values):
                worksheet.write(start_row, start_col + col_num + 1, value, header_format)

            # Adjust column widths and apply data cell formats (currency or general)
            # For index column
            index_col_len = len(str(df_to_write.index.name)) if df_to_write.index.name else 5
            if isinstance(df_to_write.index, pd.MultiIndex):
                for level_name in df_to_write.index.names:
                    if level_name:
                        index_col_len = max(index_col_len, len(str(level_name)))
            worksheet.set_column(start_col, start_col, index_col_len + 5, data_cell_format) # Apply data cell format to index column

            # For data columns
            for col_idx, col_name in enumerate(df_to_write.columns):
                excel_col_num = start_col + col_idx + 1 # +1 because index is at start_col
                col_data_max_len = 0
                if not df_to_write[col_name].empty:
                    # Calculate max length of data in the column
                    lengths = df_to_write[col_name].astype(str).map(len)
                    col_data_max_len = lengths.max()
                    if pd.isna(col_data_max_len): # Handle case where max() might return NaN for empty series
                        col_data_max_len = 0

                # Max length is either header length or max data length, plus some padding
                max_len = max(int(col_data_max_len), len(str(col_name))) + 2

                # Apply currency format if column name is in CURRENCY_COLUMNS, otherwise general data format
                if col_name in CURRENCY_COLUMNS:
                    worksheet.set_column(excel_col_num, excel_col_num, max_len, currency_format)
                else:
                    worksheet.set_column(excel_col_num, excel_col_num, max_len, data_cell_format)

            # Apply borders only to non-empty data cells within the table's data range
            data_start_row_excel = start_row + 1
            data_end_row_excel = start_row + len(df_to_write)
            data_start_col_excel = start_col
            data_end_col_excel = start_col + len(df_to_write.columns) # Covers index column + all data columns

            worksheet.conditional_format(
                data_start_row_excel, data_start_col_excel,
                data_end_row_excel, data_end_col_excel,
                {'type': 'no_blanks', 'format': border_only_format}
            )


        logger.info(f"Reconciliation summary written to sheet '{sheet_name}' successfully.")
        return True
    except Exception as e:
        logger.error(f"Error writing combined summary sheet '{sheet_name}': {e}", exc_info=True)
        st.error(f"An error occurred during Excel summary export: {e}")
        return False

def export_formatted_excel(dataframes_dict: dict, writer_obj: pd.ExcelWriter = None,
                           header_bg_color: str = HEADER_BG_COLOR_RECON,
                           header_text_color: str = HEADER_TEXT_COLOR_RECON) -> io.BytesIO | None:
    """
    Exports multiple Pandas DataFrames to different sheets in a single Excel file
    with formatted headers, conditional row styling for the 'comment' column
    (if present), and cell borders.
    Can write to an existing ExcelWriter object or create a new one.

    Args:
        dataframes_dict (dict): A dictionary where keys are sheet names (str) and
                                values are Pandas DataFrames or Styler objects.
        writer_obj (pd.ExcelWriter, optional): An existing pd.ExcelWriter object.
                                              If None, a new one is created. Defaults to None.
        header_bg_color (str): Background color for headers.
        header_text_color (str): Text color for headers.

    Returns:
        io.BytesIO | None: A BytesIO object containing the Excel file if created internally,
                           otherwise None (if writer_obj was provided). Returns None on error.
    """
    logger.info("Starting formatted Excel export.")
    output = None

    try:
        if not isinstance(dataframes_dict, dict) or not dataframes_dict:
            raise ValueError("Input 'dataframes_dict' must be a non-empty dictionary of DataFrames.")

        # Use existing writer or create a new one
        if writer_obj is None:
            output = io.BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            created_writer_internally = True
        else:
            writer = writer_obj
            created_writer_internally = False

        workbook = writer.book

        header_format_excel = workbook.add_format({
            'bold': True,
            'text_wrap': False,
            'valign': 'vcenter',
            'align': 'center',
            'fg_color': header_bg_color,
            'font_color': header_text_color,
            'border': 1
        })
        
        # Data cell format (no border by default, will be applied conditionally)
        data_cell_format = workbook.add_format({})

        # Number format for currency in reconciliation sheets (no border by default, will be applied conditionally)
        currency_format_reconciliation = workbook.add_format({
            'num_format': '$#,##0.00',
        })

        # Format specifically for applying borders to non-empty cells
        border_only_format_reconciliation = workbook.add_format({
            'border': 1,
            'border_color': 'black'
        })

        # Define formats for comment cells
        comment_green_format = workbook.add_format({'bg_color': 'green', 'font_color': 'white', 'border': 1, 'border_color': 'black'})
        comment_blue_format = workbook.add_format({'bg_color': 'blue', 'font_color': 'white', 'border': 1, 'border_color': 'black'})
        comment_yellow_format = workbook.add_format({'bg_color': 'yellow', 'font_color': 'black', 'border': 1, 'border_color': 'black'})
        comment_red_format = workbook.add_format({'bg_color': 'red', 'font_color': 'white', 'border': 1, 'border_color': 'black'})

        # Map comment values to xlsxwriter formats
        comment_formats = {
            COMMENT_FULL_MATCH: comment_green_format,
            COMMENT_GL_YES_BANK_NO: comment_blue_format,
            COMMENT_PARTIAL_MATCH: comment_yellow_format,
            # Default for other comments (e.g., COMMENT_GL_NO_BANK_YES, COMMENT_TRANS_MATCH_DIFF_AMT)
            'default': comment_red_format
        }

        # Helper function to convert column index to Excel column letter
        def get_excel_column_letter(col_idx):
            result = ""
            while col_idx >= 0:
                result = chr(65 + (col_idx % 26)) + result
                col_idx = (col_idx // 26) - 1
            return result

        for sheet_name, df in dataframes_dict.items():
            # Ensure original_df_data is always a DataFrame, even if df is a Styler
            if isinstance(df, pd.io.formats.style.Styler):
                original_df_data = df.data
            else:
                original_df_data = df

            # Write the DataFrame data first, starting from row 1 (after headers)
            original_df_data.to_excel(writer, sheet_name=sheet_name, index=False, header=False, startrow=1, na_rep='')

            worksheet = writer.sheets[sheet_name]

            logger.debug(f"Writing sheet '{sheet_name}'. Columns: {original_df_data.columns.tolist()}, Dtypes: {original_df_data.dtypes.to_dict()}")

            # Write headers with formatting at row 0
            for col_num, value in enumerate(original_df_data.columns.values):
                worksheet.write(0, col_num, value, header_format_excel)

            # Adjust column widths and apply data cell formats (currency or general)
            # These formats now do NOT include borders by default
            for i, col in enumerate(original_df_data.columns):
                col_data_max_len = 0
                if not original_df_data[col].empty:
                    # Calculate max length of data in the column
                    lengths = original_df_data[col].astype(str).map(len)
                    col_data_max_len = lengths.max()
                    if pd.isna(col_data_max_len):
                        col_data_max_len = 0
                max_len = max(int(col_data_max_len), len(str(col))) + 2

                # Apply currency format if column name is in CURRENCY_COLUMNS, otherwise general data format
                if col in CURRENCY_COLUMNS:
                    worksheet.set_column(i, i, max_len, currency_format_reconciliation)
                else:
                    worksheet.set_column(i, i, max_len, data_cell_format)

            # Determine the end column for borders based on sheet name
            data_start_row_excel = 1 # Data starts at row 1 after header
            data_end_row_excel = len(original_df_data) # Last row of data
            data_start_col_excel = 0

            # Set the specific end column index for borders for each sheet
            if sheet_name == GL_VS_BANK_SHEET_NAME:
                data_end_col_excel_for_border = 19 # Column 'T' (0-indexed)
            elif sheet_name == OUTSTANDING_CHECK_SHEET_NAME:
                data_end_col_excel_for_border = 15 # Column 'P' (0-indexed)
            else:
                # Fallback to the last column of the DataFrame if sheet name is not specifically handled
                data_end_col_excel_for_border = len(original_df_data.columns) - 1
            
            # Apply borders only to non-empty rows within the specified range
            # The formula checks if any cell in the row from 'first_col_letter' to 'last_col_letter' is non-empty.
            first_col_letter = get_excel_column_letter(data_start_col_excel)
            last_col_letter = get_excel_column_letter(data_end_col_excel_for_border)
            
            # Formula is relative to the top-left cell of the conditional format range.
            # Excel rows are 1-indexed, so add 1 to data_start_row_excel.
            # We want borders IF the row is NOT empty.
            formula = f'=COUNTA(${first_col_letter}{data_start_row_excel + 1}:${last_col_letter}{data_start_row_excel + 1})>0'

            # Apply the border_only_format_reconciliation if the row is NOT empty
            worksheet.conditional_format(
                data_start_row_excel, data_start_col_excel,
                data_end_row_excel, data_end_col_excel_for_border, # Apply to the specific range
                {'type': 'formula', 'criteria': formula, 'format': border_only_format_reconciliation}
            )

            # Apply conditional formatting for the 'comment' column if it exists
            if 'comment' in original_df_data.columns:
                comment_col_idx = original_df_data.columns.get_loc('comment')
                # Iterate through rows to apply format to the specific comment cell
                for row_num, comment_value in enumerate(original_df_data['comment']):
                    excel_row = row_num + 1 # Data starts at row 1
                    
                    # Get the format from the dictionary, defaulting if not found
                    format_to_apply = comment_formats.get(comment_value, comment_formats['default'])
                    
                    # Apply format to the specific comment cell, preserving other column formats
                    worksheet.write(excel_row, comment_col_idx, comment_value, format_to_apply)


        # Only close the writer if it was created internally
        if created_writer_internally:
            writer.close()
            output.seek(0)
            return output
        else:
            return None # Indicate that the writer was passed in and not closed here

    except Exception as e:
        logger.error(f"An error occurred during Excel export: {e}", exc_info=True)
        st.error(f"An error occurred during Excel export: {e}")
        # If an error occurs and writer was created internally, ensure it's closed
        if created_writer_internally and writer:
            try:
                writer.close()
                logger.info("Internal ExcelWriter closed due to error.")
            except Exception as close_e:
                logger.error(f"Error closing internal ExcelWriter after failure: {close_e}")
        return None