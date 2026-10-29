"""
config.py

Centralized configuration for GL vs Bank Statement Reconciliation.
This module stores constants such as column names, sheet names, and
filter values, promoting readability, maintainability, and testability.
"""


# --- File and Sheet Names ---
GL_FILE_SHEET_NAME = 'LN - GL Account Analysis Report'
BANK_FILE_SHEET_NAME = 'Categorized'
OUTSTANDING_CHECK_REPORT_SHEET_NAME = 'Outstanding Check Report'
EXCEL_OUTPUT_FILENAME = 'financial_reconciliation_report.xlsx'
PIVOT_SHEET_NAME = "pivot"
GL_VS_BANK_SHEET_NAME = "GLvsBank"
OUTSTANDING_CHECK_SHEET_NAME = "OutstandingCheck"

# --- GL Columns ---
#--- Modified as part of GL Categorization---
#--- Added BatchName,Description and Journal Name--
GL_COLUMNS_REQUIRED = [
    'CO', 'AU', 'Acct', 'Sub Acct', 'Project', 'Period Name', 'Source', 'Category', 'Journal Name','Batch Name',
    'Description','Entered DR', 'Entered CR', 'Accounted DR', 'Accounted CR', 'Transaction Number', 'Transaction Date',
    'Transaction Amount', 'Party Number', 'Party Name',  'Accounted Sum'
]

#--- Modified as part of GL Categorization---
#--- Added BatchName,Description and Journal Name--
GL_COLUMN_TYPES = {
    'CO': 'string', 'AU': 'string', 'Acct': 'string', 'Sub Acct': 'string', 'Project': 'string',
    'Period Name': 'string', 'Source': 'string', 'Category': 'string', 'Journal Name': 'string',
    'Batch Name':'string','Description':'string','Entered DR': 'float', 'Entered CR': 'float', 
    'Accounted DR': 'float', 'Accounted CR': 'float','Transaction Number': 'string', 
    'Transaction Date': 'string', 'Transaction Amount': 'float','Party Number': 'string', 
    'Party Name': 'string', 'Accounted Sum': 'float'
}

GL_COLUMNS_TO_FILL_NA = ['Transaction Date', 'Transaction Amount', 'Party Number', 'Party Name']
GL_TRANSACTION_NUMBER_COL = 'Transaction Number'
GL_ACCOUNTED_SUM_COL = 'Accounted Sum'
GL_TYPE_COL = 'Type'
GL_ACCOUNTED_CR_COL = 'Accounted CR'
GL_ACCOUNTED_DR_COL = 'Accounted DR'
#----Added as part of GL categorization----
JOURNAL_COL = 'Journal Name'
DESCRIPTION_COL = 'Description'
BATCHNAME_COL = 'Batch Name'
PARTYNAME_COL = 'Party Name'
BANK_CATEGORY_LIST = ['AR Module','Autodebits','Brinks','Checks','EFTPS','Interest','LN ACH',
                      'Lockbox','Payroll','Return','Square','Stripe','Ticketing','Vibee AR',
                      'Wires','ZBA']


# --- Bank Columns ---
BANK_COLUMNS_REQUIRED = [
    'Bank reference', 'Customer reference', 'TRN TYPE', 'TRN status', 'Value date',
    'Credit amount', 'Debit amount', 'Time', 'Post date'
]

BANK_COLUMN_TYPES = {
    'Bank reference': 'string', 'Customer reference': 'string', 'TRN TYPE': 'string',
    'TRN status': 'string', 'Value date': 'string', 'Credit amount': 'float',
    'Debit amount': 'float', 'Time': 'string', 'Post date': 'string'
}

BANK_CREDIT_AMOUNT_COL = 'Credit amount'
BANK_DEBIT_AMOUNT_COL = 'Debit amount'
BANK_TRN_TYPE_COL = 'TRN TYPE'
BANK_REFERENCE_COL = 'Bank reference'
CUSTOMER_REFERENCE_COL = 'Customer reference'
BANK_COMPARISON_KEY_COL = 'comparsion_key'


# -----GL VS Bank Output Columns ------------

GL_VS_BANK_COL = [
            'Key_Transaction Number', 'GL_CO', 'GL_AU', 'GL_Acct', 'GL_Sub Acct', 'GL_Project',
            'GL_Period Name','Key_Type', 'GL_Accounted Sum', 'Bnk_TRN status',
            'Bnk_Value date', 'Bnk_Credit amount', 'Bnk_Debit amount', 'Bnk_Accounted Sum',
            'Bnk_Time', 'Bnk_Post date', 'Bnk_Comparsion_Key', 'variance', 'comment'
        ]

# --- Outstanding Checks Columns ---
OUTSTANDING_CHECK_COLUMNS_REQUIRED = [
    'Check number', 'Date posted', 'Vendor Name', 'Amount', 'Cleared?'
]

OUTSTANDING_CHECK_COLUMN_TYPES = {
    'Check number': 'string', 'Date posted': 'string', 'Vendor Name': 'string',
    'Amount': 'float', 'Cleared?': 'string'
}

OUTSTANDING_CHECK_NUMBER_COL = 'Check number'
OUTSTANDING_DATE_POSTED_COL = 'Date posted'
#OUTSTANDING_VENDOR_NAME_COL = 'Vendor Name'
OUTSTANDING_VENDOR_NAME_COL = 'Party Name'
OUTSTANDING_AMOUNT_COL = 'Amount'
OUTSTANDING_CLEARED_COL = 'Cleared?'


# --- Reconciliation Specifics ---
COMMENT_FULL_MATCH = "Full Match"
COMMENT_PARTIAL_MATCH = "Partial Match"
COMMENT_GL_NO_BANK_YES = "GL No,Bank yes"
COMMENT_GL_YES_BANK_NO = "GL Yes,Bank No"

COMMENT_TRANS_NOT_IN_BANK = 'Transaction Number not available in bank statement'
COMMENT_TRANS_MATCH_DIFF_AMT = 'Transaction number matched but the transacted amount is different'
COMMENT_TRANS_MATCHED = "Transaction Matched"

GL_NO_TRANS_NUMBER = 'No_Transaction_Number'
NO_REFERENCE_NUMBER = 'No_Reference_Number'


#-----------Added as part of gl categorization--------------
DESC_CHECK_SEARCH1 = 'manual checks'
DESC_CHECK_SEARCH2 = 'ck#'
DESC_TRANSNO_SEARCH1 = 'ref#'
ACH_TRANSNO_SEARCH = '640'
ZBA_JOURNAL_SEARCH = 'ZBA'
INTEREST_DESC_SEARCH = 'interest'
PAYROLL_JOURNAL_SEARCH = 'payroll'
AUTODEBIT_JOURNAL_SEARCH = 'autodebit'
EFTPS_JOURNAL_SEARCH = 'eftps'
VIBEE_JOURNAL_SEARCH = 'vibee'
STRIPE_JOURNAL_SEARCH = 'stripe'
BRINKS_JOURNAL_SEARCH = 'table sales'
SQUARE_DESC_JOURNAL_SEARCH = 'square'
TICKET_PARTY_SEARCH1 = 'front gate'
TICKET_PARTY_SEARCH2 = 'vivendi'
AR_BATCH_SEARCH = ['receivable','ar','ON ACCOUNT','receipt','cash']
WIRE_BATCH_SEARCH = ['payables','wire']
TRANS_CHECK_SEARCH1 = '1112'
TRANS_CHECK_SEARCH2 = '340'

#---------------------------------Added as part of highlighting manual checks in outstanding checks---------------------------
PARTY_NAME_SEARCH1 = 'manual checks'
PARTY_NAME_SEARCH2 = 'ck#'
 
# --- Styling Colors ---
HEADER_BG_COLOR_PIVOT = '#4472C4' # Blue
HEADER_TEXT_COLOR_PIVOT = "#FBEFEF"
DATA_CELL_BORDER_COLOR_PIVOT = 'gray'

HEADER_BG_COLOR_RECON = '#2F5496' # Darker Blue
HEADER_TEXT_COLOR_RECON = 'white'
DATA_CELL_BORDER_COLOR_RECON = 'black'

# --- Logging Configuration ---
LOGGING_LEVEL = 'INFO' # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE_NAME = 'reconciliation.log'

# -------Streamlit Pages ------

TAB1 = "📁 File Upload"
TAB2 = "🔄 Categorization"
TAB3 = "⚖️ Reconciliation"

#---------------Excel formatting currency columns---------------
CURRENCY_COLUMNS = [
    'GL_Accounted Sum', 'Bnk_Credit amount', 'Bnk_Debit amount', 'Bnk_Accounted Sum', 'variance', # From GL vs Bank sheet
    'Amount', # From Outstanding Check sheet (original outstanding amount)
    'Banking Credit amount', 'Banking Debit amount', 'Banking sum Cr Dr', # From Bank Pivot
    'GL Accounted CR', 'GL Accounted DR', 'GL sum Accounted Cr Dr', # From GL Pivot
    'Bank Sum', 'GL Sum', 'Difference' # From Difference Grid

]
