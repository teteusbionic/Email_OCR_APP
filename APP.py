import streamlit as st
import pytesseract
from pdf2image import convert_from_bytes
import re
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Processador de Documentos", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# Inicializa o estado para evitar duplicatas
if 'processado' not in st.session_state:
    st.session_state.processado = False

def format_document_info(label, value):
    if value == "Não encontrado": return value
    digits = re.sub(r'\D', '', value)
    
    if label == "CPF" and len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    
    if label == "RG" and len(digits) == 9:
        # Formato solicitado: XX.XXX.XXX.X
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}.{digits[8:]}"
        
    if label == "Tipo Sanguíneo":
        return value.upper().strip()
        
    return value

def validar_dados(data):
    erros = []
    cpf_limpo = re.sub(r'\D', '', data['CPF'])
    if len(cpf_limpo) != 11:
        erros.append(f"CPF inválido: {data['CPF']} (Esperado 11 dígitos)")

    rg_limpo = re.sub(r'\D', '', data['RG'])
    if len(rg_limpo) != 9:
        erros.append(f"RG inválido: {data['RG']} (Esperado 9 dígitos)")

    if len(data['Tipo Sanguíneo']) > 3 or data['Tipo Sanguíneo'] == "Não encontrado":
        erros.append(f"Tipo Sanguíneo inválido: {data['Tipo Sanguíneo']}")

    if not re.match(r'\d{2}/\d{2}/\d{4}', data['Data de Nascimento']):
        erros.append(f"Data de Nascimento inválida: {data['Data de Nascimento']}")

    return erros

def extract_fields(text):
    # Regex flexível para capturar "RG:" ou "RG SSP:" conforme o arquivo CPF3.pdf
    patterns = {
        "NOME": r"Nome:\s*(.*)",
        "CPF": r"CPF:\s*([\d\.\-]+)",
        "RG": r"RG(?:\s*SSP)?:\s*([\d\.\-]+)",
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
st.markdown("<h1 style='text-align: center;'>Send documents to be processed.</h1>", unsafe_allow_html=True)

col_left, col_right = st.columns([1, 1.2])

# --- ESTADO DO APP ---
# Criamos uma 'memória' para saber qual foi o último arquivo salvo
if 'ultimo_arquivo' not in st.session_state:
    st.session_state.ultimo_arquivo = None

# --- LÓGICA DE UPLOAD NO COL_LEFT ---
with col_left:
    st.header("Upload")
    uploaded_file = st.file_uploader("Arraste o PDF aqui", type=["pdf"])

    if uploaded_file:
        # Só processa se o nome do arquivo for diferente do último salvo
        if st.session_state.ultimo_arquivo != uploaded_file.name:
            with st.spinner('Processando e salvando automaticamente...'):
                # 1. OCR e Extração
                images = convert_from_bytes(uploaded_file.read())
                full_text = "".join([pytesseract.image_to_string(img) for img in images])
                data = extract_fields(full_text)
                
                colunas_ordem = ["NOME", "CPF", "RG", "Data de Nascimento", "Tipo Sanguíneo"]
                data_final = {k: data.get(k, "Não encontrado") for k in colunas_ordem}
                
                # 2. Validação
                erros = validar_dados(data_final)
                
                if erros:
                    for erro in erros:
                        st.error(erro)
                else:
                    try:
                        # 3. Salva na Planilha (ttl=0 para ler a verdade atual)
                        existing_df = conn.read(ttl=0)
                        new_row = pd.DataFrame([data_final])
                        
                        if existing_df is not None and not existing_df.empty:
                            updated_df = pd.concat([existing_df, new_row], ignore_index=True)
                        else:
                            updated_df = new_row
                            
                        conn.update(data=updated_df)
                        
                        # 4. TRAVA: Registra que este arquivo já foi salvo
                        st.session_state.ultimo_arquivo = uploaded_file.name
                        
                        st.success(f"✅ {data_final['NOME']} adicionado com sucesso!")
                        st.balloons()
                        st.rerun() # Atualiza a tabela na direita imediatamente
                    except Exception as e:
                        st.error(f"Erro no salvamento automático: {e}")
        else:
            # Se o arquivo já foi processado, apenas mostra os dados na tela
            st.info("ℹ️ Este arquivo já foi enviado para a planilha.")
            # Opcional: mostrar o que foi extraído apenas para conferência

with col_right:
    st.header("Histórico (Google Sheets)")
    
    # Criamos um fragmento que se auto-atualiza a cada 30 segundos
    @st.fragment(run_every="15s")
    def mostrar_tabela_viva():
        try:
            # ttl=0 garante que ele ignore o cache e busque o dado real da planilha
            current_data = conn.read(ttl=0)
            
            if current_data is not None:
                st.dataframe(current_data, use_container_width=True, hide_index=True)
                st.caption("🔄 Atualizado automaticamente a cada 30s")
        except Exception:
            st.info("Sincronizando com o Google Sheets...")

    # Chamamos a função para exibir a tabela
    mostrar_tabela_viva()
    
    if st.button("Forçar Atualização Agora"):
        st.rerun()
