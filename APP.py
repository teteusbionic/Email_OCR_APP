import streamlit as st
import pytesseract
from pdf2image import convert_from_bytes
import re

# --- UI Setup ---
st.set_page_config(page_title="Extrato de Documento", layout="centered")
st.markdown("<h1 style='text-align: center;'>UPLOAD de PDF.</h1>", unsafe_allow_html=True)

# Helper function to clean and format strings
def format_document_info(label, value):
    if value == "Not found":
        return value
    
    # Remove all non-numeric characters for digits-only fields
    digits_only = re.sub(r'\D', '', value)
    
    if label == "CPF" and len(digits_only) == 11:
        return f"{digits_only[:3]}.{digits_only[3:6]}.{digits_only[6:9]}-{digits_only[9:]}"
    
    if label == "RG" and len(digits_only) >= 8:
        # Assuming standard format: XX.XXX.XXX-X
        return f"{digits_only[:-1].replace(digits_only[:-4], digits_only[:-4] + '.')}-{digits_only[-1]}"
    
    if label == "CNS" and len(digits_only) == 15:
        return f"{digits_only[:3]} {digits_only[3:7]} {digits_only[7:11]} {digits_only[11:]}"
    
    return value

def extract_fields(text):
    patterns = {
        "Nome": r"Nome:\s*(.*)",
        "CPF": r"CPF:\s*([\d\.\-]+)",
        "RG": r"RG\s*SSP:\s*([\d\.\-]+)",
        "Data de Nascimento": r"Data de Nascimento:\s*([\d/]+)",
        "Data de Expedição": r"Data de Expedição:\s*([\d/]+)"
    }
    
    results = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        raw_value = match.group(1).strip() if match else "Not found"
        # Apply formatting immediately
        results[field] = format_document_info(field, raw_value)
    return results

# --- Main App Logic ---
uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file is not None:
    with st.spinner('Processando e Formatando documento...'):
        images = convert_from_bytes(uploaded_file.read())
        full_text = ""
        for img in images:
            full_text += pytesseract.image_to_string(img)
        
        data = extract_fields(full_text)
        
        st.write("### Data estruturada do Documento")
        
        # Display in a clean, organized layout
        container = st.container(border=True)
        with container:
            st.write(f"**Nome:** {data['Nome']}")
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**CPF**\n\n{data['CPF']}")
                st.info(f"**RG**\n\n{data['RG']}")
            with col2:
                st.info(f"**Nascimento**\n\n{data['Data de Nascimento']}")
                st.info(f"**Expedição**\n\n{data['Data de Expedição']}")

        if st.checkbox("Informação RAW extraida"):
            st.text(full_text)
