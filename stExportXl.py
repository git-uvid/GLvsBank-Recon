import pandas as pd
import streamlit as st
import io

#method to set the bg based on the comment
def formatCommentCol(comment):
    if comment == "Transaction Matched":
        return 'background-color: green; color: white'
    elif comment == "Transaction Number not available in bank statement":
        return 'background-color: blue; color: white'
    elif comment == "Transaction number matched but the transacted amount is different":
        return 'background-color: yellow; color: Black'
    else:
        return 'background-color: red; color: white'

def write_reconciliation_summary_sheet(
    writer, # Accepts an existing pd.ExcelWriter object
    bank_pivot_df_raw,
    gl_pivot_df_raw,
    difference_df,
    sheet_name="pivot",
    header_bg_color='#D9E1F2',
    header_text_color='#333333',
    data_cell_border_color='black',
    spacing_rows=2,
    spacing_cols=2,

):
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

        data_cell_format = workbook.add_format({
            'border': 1,
            'border_color': data_cell_border_color
        })
        
        # A format for cells that should explicitly NOT have borders (for spacing)
        no_border_format = workbook.add_format({'border': 0})


        # --- Determine Placement for each table ---
        tables_to_export_and_layout = [
            {'df': bank_pivot_df_raw, 'name': 'Bank Pivot Summary'},
            {'df': gl_pivot_df_raw, 'name': 'GL Pivot Summary'},
            {'df': difference_df, 'name': 'Category Variance'}
        ]

        table_dims = []
        for item in tables_to_export_and_layout:
            df_curr = item['df']
            height = len(df_curr) + 1
            width = len(df_curr.columns) + 1
            table_dims.append({'height': height, 'width': width})

        # Calculate positions: (start_row, start_col)
        bank_pivot_pos = (0, 0)
        gl_pivot_pos = (0, table_dims[0]['width'] + spacing_cols)
        
        max_height_top_row = max(table_dims[0]['height'], table_dims[1]['height'])
        difference_table_pos = (max_height_top_row + spacing_rows, 0)

        all_positions = [bank_pivot_pos, gl_pivot_pos, difference_table_pos]

        # --- Write each table to the single sheet ---
        for i, item in enumerate(tables_to_export_and_layout):
            df_to_write = item['df']
            table_name = item['name']
            start_row, start_col = all_positions[i]

            worksheet.write(start_row - 1, start_col, table_name, workbook.add_format({'bold': True, 'font_size': 12}))
            
            # Removed the problematic float_format argument. Borders handled by set_column and conditional_format.
            df_to_write.to_excel(writer, sheet_name=sheet_name, index=True, header=False,
                                 startrow=start_row + 1, startcol=start_col,
                                 na_rep='')

            worksheet.write(start_row, start_col, df_to_write.index.name if df_to_write.index.name else "Index", header_format)
            for col_num, value in enumerate(df_to_write.columns.values):
                worksheet.write(start_row, start_col + col_num + 1, value, header_format)

            # Adjust column widths. DO NOT apply data_cell_format here if you want empty spaces to be borderless.
            index_col_len = len(str(df_to_write.index.name)) if df_to_write.index.name is not None else 5
            if isinstance(df_to_write.index, pd.MultiIndex):
                for level_name in df_to_write.index.names:
                    if level_name:
                        index_col_len = max(index_col_len, len(str(level_name)))
            # Set column width without applying data_cell_format to the entire column.
            worksheet.set_column(start_col, start_col, index_col_len + 5)

            for col_idx, col_name in enumerate(df_to_write.columns):
                excel_col_num = start_col + col_idx + 1
                col_data_max_len = 0
                if not df_to_write[col_name].empty:
                    lengths = df_to_write[col_name].astype(str).map(len)
                    col_data_max_len = lengths.max()
                    if pd.isna(col_data_max_len):
                        col_data_max_len = 0
                
                max_len = max(int(col_data_max_len), len(str(col_name))) + 2
                # Set column width without applying data_cell_format to the entire column.
                worksheet.set_column(excel_col_num, excel_col_num, max_len)

            # Robustly apply data cell borders to the *actual data range* of the current table.
            # This ensures only the cells containing data (including index data) get borders.
            data_start_row_excel = start_row + 1
            data_end_row_excel = start_row + len(df_to_write)
            data_start_col_excel = start_col
            data_end_col_excel = start_col + len(df_to_write.columns) # Covers index column + all data columns
            
            worksheet.conditional_format(
                data_start_row_excel, data_start_col_excel,
                data_end_row_excel, data_end_col_excel,
                {'type': 'no_errors', 'format': data_cell_format}
            )

        # --- Ensure spacing columns/rows are truly empty/borderless ---
        # If there are explicit spacing columns, ensure they have no formatting
        if spacing_cols > 0:
            start_spacing_col = table_dims[0]['width']
            end_spacing_col = start_spacing_col + spacing_cols -1
            worksheet.set_column(start_spacing_col, end_spacing_col, None, no_border_format) # Set no format for spacing columns

        # Similarly, for spacing rows if needed.
        # This is more complex as it depends on where the difference table is relative to the others.
        # The conditional_format and default no-format for cells should mostly handle this.
        # But if explicit blank rows are added with write_blank calls, ensure no_border_format.
        # Given current implementation, spaces are created by startrow offsets, so no direct `write_blank` is needed for styling.

        return True # Indicate success
    except Exception as e:
        st.error(f"Error writing combined sheet: {e}")
        return False

#-------------------------------------------------Export excel-----------------------------------------------------------------    
def export_formatted_excel(dataframes_dict, writer_obj=None,
                           header_bg_color='#4472C4', header_text_color='white'):
    """
    Exports multiple Pandas DataFrames to different sheets in a single Excel file
    with formatted headers, conditional row styling for the 'comment' column
    (if present), and cell borders.
    Can write to an existing ExcelWriter object or create a new one.
    """
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
        
        # Data cell format (for borders)
        data_cell_format = workbook.add_format({
            'border': 1, # Border for data cells
            'border_color': 'black' # Default border color for data cells
        })


        for sheet_name, df in dataframes_dict.items():
            if isinstance(df, pd.io.formats.style.Styler):
                styled_df = df
                original_df_data = df.data
            else:
                styled_df = df.style
                if 'comment' in df.columns:
                    styled_df = styled_df.map(formatCommentCol, subset=['comment'])
                styled_df = styled_df.set_properties(**{
                    'border': '1px solid black',
                    'border-color': 'black'
                })
                original_df_data = df

            styled_df.to_excel(writer, sheet_name=sheet_name, index=False)

            worksheet = writer.sheets[sheet_name]

            for col_num, value in enumerate(original_df_data.columns.values):
                worksheet.write(0, col_num, value, header_format_excel)

            for i, col in enumerate(original_df_data.columns):
                col_data_max_len = 0
                if not original_df_data[col].empty:
                    lengths = original_df_data[col].astype(str).map(len)
                    col_data_max_len = lengths.max()
                    if pd.isna(col_data_max_len):
                        col_data_max_len = 0
                max_len = max(int(col_data_max_len), len(str(col))) + 2
                worksheet.set_column(i, i, max_len, data_cell_format) # Apply data cell format here

            # Robustly apply data cell borders to the entire data range of the current table
            data_start_row_excel = 1 # Data starts at row 1 after header
            data_end_row_excel = len(original_df_data) # Last row of data
            data_start_col_excel = 0
            data_end_col_excel = len(original_df_data.columns) -1 # Last column index (0-based)
            
            worksheet.conditional_format(
                data_start_row_excel, data_start_col_excel,
                data_end_row_excel, data_end_col_excel,
                {'type': 'no_errors', 'format': data_cell_format}
            )


        # Only close the writer if it was created internally
        if created_writer_internally:
            writer.close()
            output.seek(0)
            return output
        else:
            return None # Indicate that the writer was passed in and not closed here

    except Exception as e:
        st.error(f"An error occurred during Excel export: {e}")
        # If an error occurs and writer was created internally, ensure it's closed
        if created_writer_internally and 'writer' in locals() and writer:
            writer.close()
        return None