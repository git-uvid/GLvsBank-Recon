import streamlit as st
import logging

# # Import UI functions
from app_ui import display_app_header,display_footer,tab_categorization,tab_file_upload,tab_reconciliation, initialize_session_state, sidebar_instructions
# Import core reconciliation logic
from reconciliation_core import run_full_reconciliation

# Import constants from config.py for logging setup
from config import LOGGING_LEVEL, LOG_FILE_NAME

# --- Logging Configuration ---
# Ensure logging is configured only once
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=getattr(logging, LOGGING_LEVEL.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(), # Output to console
            logging.FileHandler(LOG_FILE_NAME) # Output to file
        ]
    )
logger = logging.getLogger(__name__)

def main():
    """Main function to run the Streamlit application."""
    #display_app_header()
    display_app_header()
    initialize_session_state()
    sidebar_instructions()
    tab1, tab2, tab3 = st.tabs(["📁 File Upload", "🔄 Categorization", "⚖️ Reconciliation"])
    with tab1:
        tab_file_upload()
    with tab2:
        tab_categorization()
    with tab3:
        tab_reconciliation()
    display_footer()

if __name__ == "__main__":
    main()
