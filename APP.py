import streamlit as st
import pytesseract
from pdf2image import convert_from_bytes
import re
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Processador de Documentos", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- VALIDAÇÕES ---
def validar_dados(data):
    erros = []
    # CPF: 11 dígitos
    cpf_limpo = re.sub(r'\D', '', data['CPF'])
    if len(cpf_limpo) != 11:
        erros.append(f"CPF inválido: {data['CPF']} (Esperado 11 dígitos)")

    # RG: 9 dígitos (Formato XX.XXX.XXX.X)
    rg_limpo = re.sub(r'\D', '', data['RG'])
    if len(rg_limpo) != 9:
        erros.append(f"RG inválido: {data['RG']} (Esperado 9 dígitos)")

    # Tipo Sanguíneo: Máx 3 caracteres (A+, AB-, etc)
    if len(data['Tipo Sanguíneo']) > 3 or data['Tipo Sanguíneo'] == "Não encontrado":
        erros.append(f"Tipo Sanguíneo inválido: {data['Tipo Sanguíneo']}")

    # Data de Nascimento: DD/MM/AAAA
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
        "NOME": r"Nome:\s*(.*)",
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
st.markdown("<h1 style='text-align: center;'>Envie documentos para x@y.</h1>", unsafe_allow_html=True)

col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.header("Upload")
    uploaded_file = st.file_uploader("Arraste o PDF aqui", type=["pdf"])

    if uploaded_file:
        with st.spinner('Processando...'):
            images = convert_from_bytes(uploaded_file.read())
            full_text = "".join([pytesseract.image_to_string(img) for img in images])
            data = extract_fields(full_text)
            
            # Garantir a ordem exata das colunas para o DataFrame
            colunas_ordem = ["NOME", "CPF", "RG", "Data de Nascimento", "Tipo Sanguíneo"]
            data_ordenada = {k: data[k] for k in colunas_ordem}
            
            st.subheader("Dados Extraídos")
            st.write(data_ordenada)
            
            erros = validar_dados(data_ordenada)
            
            if erros:
                for erro in erros:
                    st.error(erro)
                st.warning("⚠️ Planilha não atualizada devido aos erros de validação.")
            else:
                try:
                    # Lê dados existentes para não apagar o que já tem
                    existing_data = conn.read()
                    # Cria novo DataFrame com a nova linha
                    df_novo = pd.DataFrame([data_ordenada])
                    updated_df = pd.concat([existing_data, df_novo], ignore_index=True)
                    # Atualiza o Google Sheets
                    conn.update(data=updated_df)
                    st.success("✅ Dados salvos com sucesso!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro na conexão: {e}")

with col_right:
    st.header("Histórico Google Sheets")
    try:
        # Mostra a planilha atualizada na tela
        current_data = conn.read()
        st.dataframe(current_data, use_container_width=True, hide_index=True)
        
        if st.button("🔄 Sincronizar Tabela"):
            st.rerun()
    except Exception as e:
        st.info("Aguardando conexão com a planilha...")
