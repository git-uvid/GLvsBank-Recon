import pandas as pd
import numpy as np
from config import (BANK_COMPARISON_KEY_COL, BANK_TRN_TYPE_COL, GL_TYPE_COL, 
                    GL_TRANSACTION_NUMBER_COL,JOURNAL_COL,DESCRIPTION_COL,BATCHNAME_COL,
                    PARTYNAME_COL,BANK_CATEGORY_LIST,ACH_TRANSNO_SEARCH,JOURNAL_COL,DESCRIPTION_COL,
                    BATCHNAME_COL,PARTYNAME_COL,ZBA_JOURNAL_SEARCH,INTEREST_DESC_SEARCH,
                    PAYROLL_JOURNAL_SEARCH,AUTODEBIT_JOURNAL_SEARCH,EFTPS_JOURNAL_SEARCH,
                    VIBEE_JOURNAL_SEARCH,STRIPE_JOURNAL_SEARCH,SQUARE_DESC_JOURNAL_SEARCH,
                    PARTYNAME_COL,TICKET_PARTY_SEARCH1,TICKET_PARTY_SEARCH2,BATCHNAME_COL,
                    AR_BATCH_SEARCH,WIRE_BATCH_SEARCH,BRINKS_JOURNAL_SEARCH, TRANS_CHECK_SEARCH2, TRANS_CHECK_SEARCH1) 
import logging

logger = logging.getLogger(__name__)


def gl_type(gl:pd.DataFrame, bank:pd.DataFrame) -> pd.DataFrame:
    """
    Classifies GL transactions by type using bank data and transaction patterns.
    Adds a final type column and removes intermediate classification columns.
    Throws an error log if required columns are missing.
    """
    try:
        # List of required columns for classification
        required_gl_cols = [
            GL_TRANSACTION_NUMBER_COL, JOURNAL_COL, DESCRIPTION_COL,
            BATCHNAME_COL,PARTYNAME_COL]
        required_bank_cols = [BANK_COMPARISON_KEY_COL, BANK_TRN_TYPE_COL]

        # Check for missing columns in GL and bank DataFrames
        missing_gl = [col for col in required_gl_cols if col not in gl.columns]
        missing_bank = [col for col in required_bank_cols if col not in bank.columns]
        if missing_gl or missing_bank:
            missing_msg = (
                f"Missing columns in GL: {missing_gl}\n" if missing_gl else "" +
                f"Missing columns in Bank: {missing_bank}\n" if missing_bank else ""
            )
            raise ValueError(f"Column check failed:\n{missing_msg}")

        logger.info("Starting GL type classification.")

        # 1. Map GL transactions to bank types using transaction number
        comparison_map = dict(zip(bank[BANK_COMPARISON_KEY_COL], bank[BANK_TRN_TYPE_COL]))
        gl['BankTransaction_BasedType'] = gl[GL_TRANSACTION_NUMBER_COL].map(comparison_map).fillna('NoCategory')

        
        logger.info("Identified the GL Category based on the bank Transaction")

        # 2. Classify checks by transaction number pattern
        logger.info("Fill Checks based on the SOP")
        gl['IsCheck'] = np.where(
            (gl['BankTransaction_BasedType'] == 'NoCategory') &
            (gl[GL_TRANSACTION_NUMBER_COL].str.len() <= 9) &
            (gl[GL_TRANSACTION_NUMBER_COL].str.startswith(TRANS_CHECK_SEARCH1) | gl[GL_TRANSACTION_NUMBER_COL].str.startswith(TRANS_CHECK_SEARCH2)),
            BANK_CATEGORY_LIST[3], # index 3 has type Checks
            '' #return empty if it is not checks
        )
        logger.info("Checks filled based on SOP")

        # 3. Classify ACH transactions
        logger.info("Fill ACH based on SOP")
        gl['IsACH'] = np.where(
            (gl['BankTransaction_BasedType'] == 'NoCategory') &
            gl[GL_TRANSACTION_NUMBER_COL].str.startswith(ACH_TRANSNO_SEARCH),
            BANK_CATEGORY_LIST[6], #index 6 holds LN ACH
            '' #return empty if it is not ACH checks
        )
        logger.info("ACH filled based on SOP")



        # 4. Classify ZBA and Interest transactions
        logger.info("Fill ZBA/Interest based on SOP")
        gl['IsZBA/Interest'] = np.where(
            (gl['BankTransaction_BasedType'] == 'NoCategory') &
            (gl[JOURNAL_COL].str.contains(ZBA_JOURNAL_SEARCH, case=False, na=False)) &
            (gl[DESCRIPTION_COL].str.contains(INTEREST_DESC_SEARCH, case=False, na=False)),
            BANK_CATEGORY_LIST[5], #index 5 holds interest,
            np.where(
                gl[JOURNAL_COL].str.contains(ZBA_JOURNAL_SEARCH, case=False, na=False)&
                ~gl[DESCRIPTION_COL].str.contains(INTEREST_DESC_SEARCH, case=False, na=False),
                BANK_CATEGORY_LIST[15], #index 5 holds ZBA,
                ''
            )
        )
        logger.info("Filled ZBA/Interest based on SOP")


        logger.info("Fill payroll,autodebit,eftps,vibee,stripe based on SOP")
        # 5. Classify Payroll, Autodebit, EFTPS, Vibee AR by journal name keywords
        def categorize_transaction(text):
            text_lower = str(text).lower()
            if PAYROLL_JOURNAL_SEARCH in text_lower:
                return BANK_CATEGORY_LIST[8] #index 8 holds payroll
            elif AUTODEBIT_JOURNAL_SEARCH in text_lower:
                return BANK_CATEGORY_LIST[1] #index 1 holds autodebit
            elif EFTPS_JOURNAL_SEARCH in text_lower:
                return BANK_CATEGORY_LIST[4] #index 4 holds eftps
            elif VIBEE_JOURNAL_SEARCH  in text_lower:
                return BANK_CATEGORY_LIST[13] #index 13 holds vibee
            elif STRIPE_JOURNAL_SEARCH in text_lower:
                return BANK_CATEGORY_LIST[11] #index 11 holds stripe
            elif BRINKS_JOURNAL_SEARCH in text_lower:
                return BANK_CATEGORY_LIST[2] #index 2 holds brinks
            else:
                return ''
        gl['Is_P_AD_EF_VB_ST'] = gl[JOURNAL_COL].apply(categorize_transaction)

        logger.info("Filled payroll,autodebit,eftps,vibee,stripe based on SOP")

        # 6. Classify Square transactions by journal name and description

        logger.info("Fill square based on SOP")
        gl['IsSquare'] = np.where(
            (gl['BankTransaction_BasedType'] == 'NoCategory') &
            ((gl[JOURNAL_COL].str.contains(SQUARE_DESC_JOURNAL_SEARCH, case=False, na=False)) |
            (gl[DESCRIPTION_COL].str.contains(SQUARE_DESC_JOURNAL_SEARCH, case=False, na=False))),
            BANK_CATEGORY_LIST[10], #index 10 holds square
            ''
        )
        logger.info("Filled square based on SOP")


        # 8. Classify Ticketing transactions by party name
        logger.info("Fill ticketing based on SOP")
        gl['IsTicketing'] = np.where(
            (gl['BankTransaction_BasedType'] == 'NoCategory') &
            (gl[PARTYNAME_COL].str.contains(TICKET_PARTY_SEARCH1, case=False, na=False)) |
            (gl[PARTYNAME_COL].str.contains(TICKET_PARTY_SEARCH2, case=False, na=False)),
            BANK_CATEGORY_LIST[12], #index 12 holds ticketing
            ''
        )
        logger.info("Filled ticketing based on SOP")

        #7. Classify AR transaction based on Batch name
        logger.info("Fill AR based on Batch name")
        AR_Pattern = '|'.join(AR_BATCH_SEARCH)
        gl['Is_AR'] = np.where(
            (gl['BankTransaction_BasedType'] == 'NoCategory') &
            (gl[BATCHNAME_COL].str.contains(AR_Pattern, case=False, na=False)),
            BANK_CATEGORY_LIST[0], #index 10 holds AR
            ''
        )
        logger.info("Filled AR based on Batch name")

        #8.Classify Wire transaction based on batchname with payables
        logger.info("Fill wire based on Batch name")
        wire_pattern = '|'.join(WIRE_BATCH_SEARCH)
        gl['Is_Wire'] = np.where(
            (gl['BankTransaction_BasedType'] == 'NoCategory') &
            (gl[BATCHNAME_COL].str.contains(wire_pattern, case=False, na=False)),
            BANK_CATEGORY_LIST[14], #index 14 holds wire
            ''
        )
        logger.info("Filled wire based on Batch name")
        # 10. Summarize all type columns into the final type column, in priority order
        gl[GL_TYPE_COL] = np.where(
            gl['BankTransaction_BasedType'] != 'NoCategory',
            gl['BankTransaction_BasedType'],
            np.where(
                gl['IsCheck'] != '',
                gl['IsCheck'],
                np.where(
                    gl['IsACH'] != '',
                    gl['IsACH'],
                    np.where(
                        gl['IsZBA/Interest'] != '',
                        gl['IsZBA/Interest'],
                        np.where(
                            gl['Is_P_AD_EF_VB_ST'] != '',
                            gl['Is_P_AD_EF_VB_ST'],
                                np.where(
                                    gl['IsSquare'] != '',
                                    gl['IsSquare'],
                                    np.where(
                                        gl['IsTicketing'] != '',
                                        gl['IsTicketing'],
                                        np.where(
                                            gl['Is_Wire'] != '',
                                            gl['Is_Wire'],
                                            np.where(
                                                gl['Is_AR'] != '',
                                                gl['Is_AR'],
                                                'NoCategory'
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
        # 11. Drop all intermediate type columns except the final type column
        type_columns = [
            'BankTransaction_BasedType', 'IsCheck', 'IsACH', 'IsZBA/Interest',
            'Is_P_AD_EF_VB_ST','IsSquare', 'IsTicketing', 'Is_AR', 'Is_Wire'
        ]
        gl = gl.drop(columns=type_columns)



        logger.info("GL type classification completed successfully.")
        
        # Return the classified DataFrame
        return gl
    
    except Exception as e:
        error_message = str(e)
        logger.error(f"An error occurred during gl categorization:{error_message}")

