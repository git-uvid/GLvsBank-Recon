import pandas as pd
import numpy as np


#---------------------------------------------Party dimension table---------------------------------------
def dim_party(data):
    
    #Get dimension table like df for party and partyname
    df_party_pname_trans = data[['Transaction Number','Party Number','Party Name']]
    df_party_pname_trans = df_party_pname_trans.drop_duplicates()
    # Get partyname and party number - filter NA and remove duplicates
    df_party_pname_uniq = df_party_pname_trans[['Party Number','Party Name']]
    df_party_pname_uniq = df_party_pname_uniq.drop_duplicates()
    df_party_pname_uniq = df_party_pname_uniq[df_party_pname_uniq['Party Number'] != 'NA']
    #get uniq partyname
    df_partyname = df_party_pname_trans['Party Name']
    df_partyname = df_partyname.drop_duplicates()
    #merge partyname and partyname_number without NA
    mrg_partynum_pname = pd.merge(df_partyname,df_party_pname_uniq,
                                  on='Party Name',
                                  how='left',suffixes=('_x', '_y'))           
    #merge with df with transnumber
    mrg_party_pname_trans = pd.merge(df_party_pname_trans,mrg_partynum_pname,
                                     on='Party Name',
                                     how='left')
    mrg_part_pname_trans_nonull = mrg_party_pname_trans[mrg_party_pname_trans['Party Number_y'].notna()]
    mrg_part_pname_trans_nonull = mrg_part_pname_trans_nonull.drop_duplicates(
        subset=['Transaction Number','Party Name'])
    #get uniq transaction number
    df_trans_uniq = df_party_pname_trans['Transaction Number']
    df_trans_uniq = df_trans_uniq.drop_duplicates()
    #merge uniq transcations with df processed in previous step
    mrg_final_party_df = pd.merge(df_trans_uniq ,mrg_part_pname_trans_nonull,
                                  how='left',
                                  on = 'Transaction Number',suffixes=('_x', '_y'))

    #rename and drop cols in final party df
    mrg_final_party_df=mrg_final_party_df.drop('Party Number_x', axis=1)
    mrg_final_party_df.columns=['Transaction Number','Party Name','Party Number']
    mrg_final_party_df['Party Number'] = mrg_final_party_df['Party Number'].fillna("NA")

    return mrg_final_party_df


#--------------------------------------------------------Outstanding checks---------------------------------------------

def ost_bank(source1,source2):
    # Process outstanding checks
    ost_bank_chks = pd.merge(
        source1,
        source2,
        left_on='Check number',
        right_on='Customer reference',
        how='left'
    )
    ost_bank_chks[['Amount', 'Credit amount', 'Debit amount']] = ost_bank_chks[
        ['Amount', 'Credit amount', 'Debit amount']
    ].fillna(0)
    ost_bank_chks['variance'] = np.where(
        pd.notnull(ost_bank_chks['Customer reference']),
        ost_bank_chks['Amount'] - ost_bank_chks['Credit amount'] - ost_bank_chks['Debit amount'],
        np.nan
    )
    ost_bank_chks['updated status'] = np.where(
        (ost_bank_chks['variance'] == 0) & (pd.notnull(ost_bank_chks['variance'])),
        "Check cleared",
        np.where(
            (ost_bank_chks['variance'] != 0) & (pd.notnull(ost_bank_chks['variance'])),
            "Check cleared but difference in transaction amount",
            "check not cleared"
        )
    )
    ost_bank_chks['Cleared?'] = np.where(ost_bank_chks['updated status'] == "Check cleared", "yes", 'no')
    return ost_bank_chks


def new_outstanding(comments_data, data):
    # Add new outstanding checks from GL
    trans_not_inbank = comments_data[(comments_data['comment'] == 'Transaction Number not available in bank statement') &
                                       (comments_data['Type'] == 'Checks')]
    trans_not_inbank_reqcols = trans_not_inbank[['Transaction Number','Accounted Sum']]
    trans_not_inbank_reqcols_ost = trans_not_inbank_reqcols.copy()
    trans_not_inbank_reqcols_ost.rename(columns={
        'Transaction Number': 'Check number',
        'Transaction Date': 'Date posted',
        'Party Name': 'Vendor Name',
        'Accounted Sum': 'Amount'
    }, inplace=True)
    trans_not_inbank_reqcols_ost.loc[:, 'Cleared?'] = 'no'
    trans_not_inbank_reqcols_ost.loc[:, 'updated status'] = 'Check not cleared.New entires from gl'
    trans_not_inbank_reqcols_ost['Exists in Bank'] = trans_not_inbank_reqcols_ost['Check number'].isin(data['Check number'])
    trans_not_inbank_reqcols_ost = trans_not_inbank_reqcols_ost[trans_not_inbank_reqcols_ost['Exists in Bank'] == False]
    trans_not_inbank_reqcols_ost = trans_not_inbank_reqcols_ost.drop('Exists in Bank', axis=1)
    
    return trans_not_inbank_reqcols_ost
