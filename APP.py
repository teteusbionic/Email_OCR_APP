import streamlit as st
import pytesseract
from pdf2image import convert_from_bytes
import re

# --- Configuração da Interface ---
st.set_page_config(page_title="Extrator de Documentos", layout="centered")
st.markdown("<h1 style='text-align: center;'>Envie documentos para x@y.</h1>", unsafe_allow_html=True)

# Função para formatar os dados e deixá-los padronizados
def format_document_info(label, value):
    if value == "Não encontrado":
        return value
    
    # Remove qualquer caractere que não seja número
    digits_only = re.sub(r'\D', '', value)
    
    if label == "CPF" and len(digits_only) == 11:
        return f"{digits_only[:3]}.{digits_only[3:6]}.{digits_only[6:9]}-{digits_only[9:]}"
    
    if label == "RG":
        # Se o RG tiver 9 dígitos (padrão comum), formata como 22.327.258.9
        if len(digits_only) == 9:
            return f"{digits_only[:2]}.{digits_only[2:5]}.{digits_only[5:8]}.{digits_only[8:]}"
        # Se tiver um número diferente de dígitos, apenas limpa e retorna
        return digits_only 
    
    if label == "Tipo Sanguíneo":
        return value.upper().strip()
    
    return value

def extract_fields(text):
    patterns = {
        "Nome": r"Nome:\s*(.*)",
        "CPF": r"CPF:\s*([\d\.\-]+)",
        "RG": r"RG\s*SSP:\s*([\d\.\-]+)",
        "Data de Nascimento": r"Data de Nascimento:\s*([\d/]+)",
        # Este novo padrão aceita "Sanguineo", "Sanguíneo", "Sanguinio" etc.
        "Tipo Sanguíneo": r"Tipo\s*Sangu[íi]neo:\s*([a-zA-Z]{1,2}[\s]*[+-])" 
    }
    
    results = {}
    for field, pattern in patterns.items():
        # O flag re.IGNORECASE é vital aqui
        match = re.search(pattern, text, re.IGNORECASE | re.UNICODE)
        raw_value = match.group(1).strip() if match else "Não encontrado"
        results[field] = format_document_info(field, raw_value)
    return results

# --- Lógica Principal do App ---
uploaded_file = st.file_uploader("Upload do PDF", type=["pdf"])

if uploaded_file is not None:
    with st.spinner('Processando e Formatando Documento...'):
        # 1. OCR
        images = convert_from_bytes(uploaded_file.read())
        full_text = ""
        for img in images:
            full_text += pytesseract.image_to_string(img)
        
        # 2. Extração
        data = extract_fields(full_text)
        
        st.write("### Dados Estruturados do Documento")
        
        # 3. Exibição na Tela
        container = st.container(border=True)
        with container:
            st.write(f"**Nome:** {data['Nome']}")
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**CPF**\n\n{data['CPF']}")
                st.info(f"**RG**\n\n{data['RG']}")
            with col2:
                st.info(f"**Nascimento**\n\n{data['Data de Nascimento']}")
                st.info(f"**Tipo Sanguíneo**\n\n{data['Tipo Sanguíneo']}")

        if st.checkbox("Mostrar texto bruto (OCR)"):
            st.text(full_text)
