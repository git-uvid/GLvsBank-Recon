import pandas as pd
import numpy as np
import io

def createBankPivot(bank_req_cols):
    bank_req_cols[['Credit amount', 'Debit amount']] = bank_req_cols[['Credit amount', 'Debit amount']].fillna(0)
    bank_req_cols['cr-dr'] = bank_req_cols['Credit amount'] - bank_req_cols['Debit amount']

    # TRN TYPE Autodebits to Autodebit
    bank_req_cols['TRN TYPE'] = np.where(bank_req_cols['TRN TYPE'] == 'Autodebits', 'Autodebit',bank_req_cols['TRN TYPE'])


    bank_pivot = pd.pivot_table(
                            bank_req_cols,
                            values =['Credit amount','Debit amount'],
                            index = 'TRN TYPE',
                            aggfunc ='sum',
                            fill_value = 0)
    bank_pivot['sum Cr Dr'] = bank_pivot['Credit amount'] - bank_pivot['Debit amount']
    bank_pivot.columns = ['Banking ' + col for col in bank_pivot.columns.values] # Flatten columns
    #print(bank_pivot)
    return bank_pivot
    
def createGLPivot(gl_required_cols):
    gl_pivot = pd.pivot_table(
                            gl_required_cols,
                            values = ['Accounted CR','Accounted DR'],
                            index = 'Type',
                            aggfunc = 'sum',
                            fill_value=0)

    gl_pivot['sum Accounted Cr Dr'] = gl_pivot['Accounted DR'] - gl_pivot['Accounted CR']


    gl_pivot.columns = ['GL ' + col for col in gl_pivot.columns.values ]
    #print(gl_pivot)
    return gl_pivot
    
def createDifferenceGrid(bank_pivot,gl_pivot):
    bank_temp = bank_pivot[['Banking Credit amount', 'Banking Debit amount', 'Banking sum Cr Dr']].copy()
    bank_temp.columns = ['Credit', 'Debit', 'Net_Sum']

    gl_temp = gl_pivot[['GL Accounted CR', 'GL Accounted DR', 'GL sum Accounted Cr Dr']].copy()
    gl_temp.columns = ['Credit', 'Debit', 'Net_Sum']

    # Align indices (categories/types) for subtraction
    # We'll take the union of indices and fill missing values with 0
    common_indices = bank_temp.index.union(gl_temp.index)

    bank_aligned = bank_temp.reindex(common_indices, fill_value=0)
    gl_aligned = gl_temp.reindex(common_indices, fill_value=0)

    difference_table = pd.DataFrame()
    # --- 2. Calculate the Difference Table by Category (Index) ---
    # Difference = GL - Bank for each corresponding column and index
    difference_table['GL Sum'] = gl_aligned['Net_Sum']
    difference_table['Bank Sum'] = bank_aligned['Net_Sum']
    difference_table['Difference'] = difference_table['GL Sum'] - difference_table['Bank Sum']
    difference_table.index.name = "Type" # Consolidated name for difference table index
    #print(difference_table)
    return difference_table