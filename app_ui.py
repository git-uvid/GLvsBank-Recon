import streamlit as st
import pandas as pd
import logging
import io
from datetime import datetime
from config import (
    GL_FILE_SHEET_NAME, BANK_FILE_SHEET_NAME, OUTSTANDING_CHECK_REPORT_SHEET_NAME,
    GL_COLUMNS_REQUIRED, GL_COLUMN_TYPES, BANK_COLUMNS_REQUIRED, BANK_COLUMN_TYPES,
    OUTSTANDING_CHECK_COLUMN_TYPES, EXCEL_OUTPUT_FILENAME, BANK_COMPARISON_KEY_COL
)
from reconciliation_core import run_full_reconciliation
from category_gl import gl_type  # Ensures reload if updated
from stBankGL import clean_and_prepare_gl_bank_data, rename_bank_trn_type, create_bank_comparison_key


logger = logging.getLogger(__name__)

def initialize_session_state():
    if 'gl_data' not in st.session_state:
        st.session_state.gl_data = None
    if 'bank_data' not in st.session_state:
        st.session_state.bank_data = None
    if 'outstanding_check_data' not in st.session_state:
        st.session_state.outstanding_check_data = None
    if 'categorized_gl' not in st.session_state:
        st.session_state.categorized_gl = None
    if 'reconciliation_excel_buffer' not in st.session_state:
        st.session_state.reconciliation_excel_buffer = None
    if 'reconciliation_results' not in st.session_state:
        st.session_state.reconciliation_results = None
    logger.info("Session state initialized.")

def display_app_header():
    st.set_page_config(
        page_title="GL Categorization & Reconciliation",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown("""
    <style>
        .main-header {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            padding: 2rem 0;
            border-radius: 10px;
            text-align: center;
            color: white;
            margin-bottom: 2rem;
        }
        .section-header {
            background: #f8f9fa;
            color: black;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            margin: 1rem 0;
        }
        .success-box {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
        }
        .info-box {
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
        }
        .metric-card {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
    </style>
    <div class="main-header">
        <h1>📊 GL Categorization & Reconciliation System</h1>
        <p>Streamline your financial data processing and reconciliation workflow</p>
    </div>
    """, unsafe_allow_html=True)
    logger.info("Header displayed.")

def sidebar_instructions():
    st.sidebar.markdown("### Instructions")
    st.sidebar.markdown("""
    1. **Upload Files** (GL & Bank)
    2. **Categorize GL** (choose method and options)
    3. **Run Reconciliation** (after uploading Categorized GL)
    4. **Download Reports**
    """)
    st.sidebar.markdown("---")
    st.sidebar.markdown("You can re-upload files at any time to restart the process.")

def tab_file_upload():
    st.markdown('<div class="section-header"><h2>📁 File Upload</h2></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📄 GL File (.xlsx only)")
        gl_file = st.file_uploader(
            "Upload your GL file (Excel only)",
            type=['xlsx'],
            key="gl_upload",
            help="Upload your General Ledger file"
        )
    with col2:
        st.markdown("#### 🏦 Bank File (.xlsx only)")
        bank_file = st.file_uploader(
            "Upload your Bank file (Excel only)",
            type=['xlsx'],
            key="bank_upload",
            help="Upload your bank file"
        )
    if st.button("Process Files"):
        if gl_file and bank_file:
            with st.spinner("Processing uploaded files..."):
                try:
                    gl_raw_df = pd.read_excel(gl_file, sheet_name=GL_FILE_SHEET_NAME, dtype=str)
                    bank_raw_df = pd.read_excel(bank_file, sheet_name=BANK_FILE_SHEET_NAME, dtype=str)
                    outstanding_raw_df = pd.read_excel(gl_file, sheet_name=OUTSTANDING_CHECK_REPORT_SHEET_NAME, dtype=str)
                    gl_processed_df = gl_raw_df[GL_COLUMNS_REQUIRED].astype(GL_COLUMN_TYPES)
                    bank_processed_df = bank_raw_df[BANK_COLUMNS_REQUIRED].astype(BANK_COLUMN_TYPES)
                    outstanding_processed_df = outstanding_raw_df.astype(OUTSTANDING_CHECK_COLUMN_TYPES)
                    st.session_state.gl_data = gl_processed_df
                    st.session_state.bank_data = bank_processed_df
                    st.session_state.outstanding_check_data = outstanding_processed_df
                    st.success("✅ Files uploaded and processed successfully!")
                    logger.info("Files uploaded and processed.")
                except KeyError as ke:
                    error_msg = f"Missing expected column or sheet: {ke}"
                    st.error(error_msg)
                    logger.error(error_msg, exc_info=True)
                except Exception as e:
                    error_msg = f"Error processing files: {str(e)}"
                    st.error(error_msg)
                    logger.error(error_msg, exc_info=True)
        else:
            st.warning("Please upload both GL and Bank files to proceed.")
            logger.warning("Upload attempt without both files.")

def tab_categorization():
    st.markdown('<div class="section-header"><h2>🔄 GL Categorization</h2></div>', unsafe_allow_html=True)

    if st.session_state.gl_data is not None and st.session_state.bank_data is not None:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("#### Categorization Method")
            st.markdown("This will use pre-defined rules to assign a Type column using GL and Bank data.")
        with col2:
            st.markdown("#### Actions")
            if st.button("🔍 Run GL Categorization"):
                with st.spinner("Categorizing GL using SOP logic..."):
                    try:
                        
                        gl_cleaned, bank_cleaned = clean_and_prepare_gl_bank_data(st.session_state.gl_data.copy(), st.session_state.bank_data.copy())
                        bank_cleaned = rename_bank_trn_type(bank_cleaned)
                        bank_cleaned[BANK_COMPARISON_KEY_COL] = bank_cleaned.apply(create_bank_comparison_key, axis=1)
                        
                        categorized_gl = gl_type(gl_cleaned, bank_cleaned)

                        # Save result in session
                        st.session_state.categorized_gl = categorized_gl

                        # Convert to Excel for download
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            categorized_gl.to_excel(writer, sheet_name="Categorized_GL", index=False)
                        output.seek(0)

                        st.success("✅ GL categorization completed successfully!")
                        st.download_button(
                            label="📥 Download Categorized GL (Excel)",
                            data=output,
                            file_name=f"gl_categorized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    except ValueError as ve:
                        st.error(f"❌ Required columns missing:\n{ve}")
                        logger.error(f"Column validation failed: {ve}", exc_info=True)
                    except Exception as e:
                        st.error(f"❌ An error occurred during categorization:\n{e}")
                        logger.error("Unexpected error in categorization", exc_info=True)
    else:
        st.info("Please upload and process both GL and Bank files first.")


def tab_reconciliation():
    st.markdown('<div class="section-header"><h2>⚖️ Reconciliation</h2></div>', unsafe_allow_html=True)

    st.markdown("#### 📂 Upload Categorized GL File")
    categorized_gl_file = st.file_uploader(
        "Upload your categorized GL file (Excel format with 'Type' column)",
        type=['xlsx'],
        key="categorized_gl_upload",
        help="Ensure the GL file is already categorized before uploading."
    )

    if categorized_gl_file:
        try:
            df = pd.read_excel(categorized_gl_file, dtype=str)
            if "Type" not in df.columns:
                st.error("❌ 'Type' column not found in uploaded GL file. Reconciliation requires it.")
                return
            st.session_state.categorized_gl = df
            st.success("✅ Categorized GL uploaded successfully!")
        except Exception as e:
            st.error(f"❌ Failed to read uploaded file: {str(e)}")
            return

    if st.session_state.categorized_gl is not None and st.session_state.bank_data is not None:
        if st.button("⚙️ Run Reconciliation"):
            with st.spinner("Running reconciliation..."):
                try:
                    excel_buffer = run_full_reconciliation(
                        st.session_state.categorized_gl,
                        st.session_state.bank_data,
                        st.session_state.outstanding_check_data
                    )
                    st.session_state.reconciliation_excel_buffer = excel_buffer
                    st.success("✅ Reconciliation completed!")
                except Exception as e:
                    st.error(f"❌ Reconciliation failed: {str(e)}")
                    logger.error("Reconciliation failed", exc_info=True)

        if st.session_state.reconciliation_excel_buffer:
            st.download_button(
                label="📥 Download Reconciliation Report (Excel)",
                data=st.session_state.reconciliation_excel_buffer,
                file_name=EXCEL_OUTPUT_FILENAME,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("Please upload the categorized GL file and process Bank file before running reconciliation.")

def display_footer():
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 2rem;">
        <p>GL Categorization & Reconciliation System | Built with Streamlit</p>
    </div>
    """, unsafe_allow_html=True)
