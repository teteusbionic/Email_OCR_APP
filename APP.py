import streamlit as st
import pytesseract
from pdf2image import convert_from_bytes
import re
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Document Processor", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÕES DE VALIDAÇÃO ---
def validar_dados(data):
    erros = []
    
    # Validar CPF (11 dígitos)
    cpf_limpo = re.sub(r'\D', '', data['CPF'])
    if len(cpf_limpo) != 11:
        erros.append(f"CPF inválido: {data['CPF']} (Esperado 11 dígitos)")

    # Validar RG (9 dígitos conforme solicitado)
    rg_limpo = re.sub(r'\D', '', data['RG'])
    if len(rg_limpo) != 9:
        erros.append(f"RG inválido: {data['RG']} (Esperado 9 dígitos)")

    # Validar Tipo Sanguíneo (Máx 3 caracteres: AB+, O-, etc)
    if len(data['Tipo Sanguíneo']) > 3 or data['Tipo Sanguíneo'] == "Não encontrado":
        erros.append(f"Tipo Sanguíneo inválido ou não encontrado: {data['Tipo Sanguíneo']}")

    # Validar Data de Nascimento (Formato DD/MM/AAAA simplificado)
    if not re.match(r'\d{2}/\d{2}/\d{4}', data['Data de Nascimento']):
        erros.append(f"Data de Nascimento fora do padrão: {data['Data de Nascimento']}")

    return erros

def format_document_info(label, value):
    if value == "Não encontrado": return value
    digits = re.sub(r'\D', '', value)
    
    if label == "CPF" and len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    if label == "RG" and len(digits) == 9:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}.{digits[8:]}"
    if label == "Tipo Sanguíneo":
        return value.upper().strip()
    return value

def extract_fields(text):
    patterns = {
        "Nome": r"Nome:\s*(.*)",
        "CPF": r"CPF:\s*([\d\.\-]+)",
        "RG": r"RG\s*SSP:\s*([\d\.\-]+)",
        "Data de Nascimento": r"Data de Nascimento:\s*([\d/]+)",
        "Tipo Sanguíneo": r"Tipo\s*Sangu[íi]neo:\s*([a-zA-Z]{1,2}[\s]*[+-])"
    }
    results = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE | re.UNICODE)
        raw_val = match.group(1).strip() if match else "Não encontrado"
        results[field] = format_document_info(field, raw_val)
    return results

# --- INTERFACE ---
col_left, col_right = st.columns([1, 1])

with col_left:
    st.header("Upload de Documentos")
    uploaded_file = st.file_uploader("Arraste o PDF aqui", type=["pdf"])

    if uploaded_file:
        with st.spinner('Analisando...'):
            images = convert_from_bytes(uploaded_file.read())
            full_text = "".join([pytesseract.image_to_string(img) for img in images])
            data = extract_fields(full_text)
            
            st.subheader("Resultado do Scan")
            st.json(data)
            
            # Validação
            erros = validar_dados(data)
            
            if erros:
                for erro in erros:
                    st.error(erro)
                st.warning("⚠️ Planilha não atualizada devido aos erros acima.")
            else:
                # Se não houver erros, enviar para o Sheets
                try:
                    df_novo = pd.DataFrame([data])
                    # Lê dados existentes
                    existing_data = conn.read()
                    updated_df = pd.concat([existing_data, df_novo], ignore_index=True)
                    # Atualiza a planilha
                    conn.update(data=updated_df)
                    st.success("✅ Dados validados e salvos no Google Sheets!")
                except Exception as e:
                    st.error(f"Erro ao conectar com Google Sheets: {e}")

with col_right:
    st.header("Histórico (Google Sheets)")
    try:
        # Exibe a planilha em tempo real
        current_data = conn.read()
        st.dataframe(current_data, use_container_width=True, hide_index=True)
        
        if st.button("Atualizar Tabela"):
            st.rerun()
    except:
        st.info("Conecte sua planilha para visualizar os dados aqui.")
