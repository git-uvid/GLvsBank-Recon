import pandas as pd
import numpy as np


# Handle Missing Elements.
def Missing_el(data,col, tag):
    counter = 1
    for index, row in data.iterrows():
        if pd.isna(row[col]) or row[col] == '':
            data.at[index, col] = f"Missing {tag} No.{counter}"
            counter += 1

# Create comparison key for bank data
def get_comparison_key(bank_required_cols):
    if bank_required_cols['TRN TYPE'] == "Checks":
        return bank_required_cols['Customer reference']
    elif bank_required_cols['TRN TYPE'] == "Wires": 
        return bank_required_cols['Bank reference']
    elif bank_required_cols['TRN TYPE'] == "AR Module":
        return bank_required_cols['Bank reference']


# Filter Type Function
def filter_type(data, col, filter):
    req_cols_type = data[data[col].isin(filter)]
    return req_cols_type

# Performing Calculation & Comment
def matched_cal(data) :


    # Handle missing values
    data[['Accounted Sum', 'Credit amount', 'Debit amount']] = data[['Accounted Sum', 'Credit amount', 'Debit amount']].fillna(0)
    
    # Add Bank_Accounted Sum
    data['Bnk Accounted Sum'] = data['Credit amount'] + data['Debit amount']
    
    # Select and rename columns
    data = data[[
        'Transaction Number', 'CO', 'AU', 'Acct', 'Sub Acct', 'Project', 'Period Name', 'Source',
        'Type', 'Accounted Sum', 'Bank reference', 'Customer reference','TRN TYPE','TRN status', 
        'Value date', 'Credit amount', 'Debit amount', 'Bnk Accounted Sum','Time', 'Post date', 'comparsion_key'
    ]]


    data['Transaction Number'] = data['Transaction Number'].fillna('No_Transaction_Number')
    data['comparsion_key'] = data['comparsion_key'].fillna('No_Reference_Number')
    
    # Calculate variance and add comments
    data['variance'] = data['Accounted Sum'] - data['Bnk Accounted Sum']
    data['comment'] = np.where(
        data['Transaction Number'] == 'No_Transaction_Number', 
        "Transaction Number not available in GL data",
        np.where(
            data['comparsion_key'] == 'No_Reference_Number', 
            "Transaction Number not available in bank statement",
            np.where(
                data['variance'] == 0,
                "Transaction Matched",
                np.where(
                    data['variance'] != 0, 
                    "Transaction number matched but the transacted amount is different",
                    ""
                )
            )
        )
    )

    return data


    

                