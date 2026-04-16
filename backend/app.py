import streamlit as st
import requests
from bs4 import BeautifulSoup
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import time
import urllib.parse
import base64
import subprocess

# =========================
# CONFIGURAÇÃO DA PÁGINA E CORES
# =========================
st.set_page_config(page_title="Gerenciador de PDFs", layout="wide")

# Aplicando a sua paleta de cores via CSS
st.markdown("""
    <style>
    /* Cor principal nos títulos */
    h1, h2, h3 { color: #4DB9C9 !important; }
    
    /* Estilo dos botões primários */
    .stButton>button {
        background-color: #4DB9C9;
        color: white;
        border-radius: 8px;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #FBE6BD;
        color: #333;
    }
    
    /* Caixas de sucesso/alerta */
    .st-emotion-cache-1cvow4s {
        background-color: #D7F1D0;
        color: #1b4332;
    }
    </style>
""", unsafe_allow_html=True)

# =========================
# MAPEAMENTO DE PASTAS
# =========================
BASE_URL = "https://www.gov.br"
headers = {"User-Agent": "Mozilla/5.0"}

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
DIRETORIO_LOADER = os.path.abspath(os.path.join(DIRETORIO_ATUAL, "..", "loaderpdf"))
PASTA_PDFS = os.path.join(DIRETORIO_LOADER, "pdfs")

os.makedirs(PASTA_PDFS, exist_ok=True)

# =========================
# FUNÇÕES DE BUSCA
# =========================
def get_links_requests(url):
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        if "caderno-" in a["href"]:
            link = a["href"]
            if link.startswith("/"):
                link = BASE_URL + link
            if link not in links:
                links.append(link)
    return links

def get_links_selenium(url):
    service = Service("chromedriver.exe")
    driver = webdriver.Chrome(service=service)
    driver.get(url)
    time.sleep(5)
    elements = driver.find_elements(By.TAG_NAME, "a")
    links = []
    for el in elements:
        href = el.get_attribute("href")
        if href and "caderno-" in href:
            if href not in links:
                links.append(href)
    driver.quit()
    return links

def mostrar_pdf(caminho_arquivo):
    with open(caminho_arquivo, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)


# =========================
# INTERFACE DO SITE EM ABAS
# =========================
st.title("🗄️ Sistema Central de Manuais")

aba_download, aba_visualizar, aba_processar = st.tabs([
    "📥 1. Baixar PDFs", 
    "👀 2. Meus Arquivos", 
    "⚙️ 3. Processar (JSON)"
])

# ---------------------------------
# ABA 1: DOWNLOAD
# ---------------------------------
with aba_download:
    st.subheader("Captura de Dados")
    url_input = st.text_input(
        "Link Gov.br:", 
        value="https://www.gov.br/anvisa/pt-br/centraisdeconteudo/publicacoes/servicosdesaude/manuais/cadernos-de-seguranca-do-paciente-e-qualidade-em-servicos-de-saude-2024-versoes-preliminares-nao-finalizadas-aguardando-o-envio-de-sugestoes"
    )

    col1, col2 = st.columns([1, 4])
    
    with col1:
        btn_iniciar = st.button("🚀 Iniciar Download")
    with col2:
        st.caption("Para interromper um download em andamento, clique no botão 'Stop' no canto superior direito da tela.")

    if btn_iniciar:
        with st.spinner("Buscando links..."):
            links = get_links_requests(url_input)
            if not links:
                st.warning("Tentando com Selenium...")
                links = get_links_selenium(url_input)

        if not links:
            st.error("❌ Nenhum caderno encontrado.")
        else:
            st.success(f"📚 {len(links)} cadernos encontrados!")
            barra_progresso = st.progress(0)
            
            for i, url_pdf in enumerate(links):
                res = requests.get(url_pdf, headers=headers)
                soup = BeautifulSoup(res.text, "html.parser")
                download_link = None
                
                for a in soup.find_all("a", href=True):
                    if "@@download" in a["href"]:
                        download_link = a["href"]
                        break

                if download_link:
                    if download_link.startswith("/"):
                        download_link = BASE_URL + download_link
                    
                    pdf = requests.get(download_link, headers=headers)
                    filename = None
                    
                    if "content-disposition" in pdf.headers:
                        match = re.findall(r'filename\*?=(?:UTF-8\'\')?["\']?([^;"\']+)', pdf.headers["content-disposition"], re.IGNORECASE)
                        if match:
                            filename = urllib.parse.unquote(match[0])
                    
                    if not filename or filename == "@@download":
                        nome_da_url = url_pdf.rstrip('/').split('/')[-1]
                        filename = f"{nome_da_url}.pdf"

                    if not filename.lower().endswith(".pdf"):
                        filename += ".pdf"
                    
                    filename = filename.replace("%20", " ")
                    filepath = os.path.join(PASTA_PDFS, filename)
                    
                    with open(filepath, "wb") as f:
                        f.write(pdf.content)
                    
                    st.write(f"✅ Baixado: `{filename}`")
                
                progresso_atual = int(((i + 1) / len(links)) * 100)
                barra_progresso.progress(progresso_atual)

            st.balloons()
            st.success("Download finalizado! Vá para a aba 'Meus Arquivos'.")

# ---------------------------------
# ABA 2: VISUALIZAR
# ---------------------------------
with aba_visualizar:
    st.subheader("Pasta de PDFs (`loaderpdf/pdfs`)")
    
    arquivos = [f for f in os.listdir(PASTA_PDFS) if f.endswith('.pdf')]
    
    if not arquivos:
        st.info("Sua pasta de PDFs está vazia no momento.")
    else:
        st.write(f"**Total de arquivos:** {len(arquivos)}")
        
        arquivo_selecionado = st.selectbox("Selecione um PDF para visualizar:", arquivos)
        
        if arquivo_selecionado:
            caminho_completo = os.path.join(PASTA_PDFS, arquivo_selecionado)
            tamanho_mb = os.path.getsize(caminho_completo) / (1024 * 1024)
            st.caption(f"Tamanho: {tamanho_mb:.2f} MB")
            mostrar_pdf(caminho_completo)

# ---------------------------------
# ABA 3: PROCESSAR JSON
# ---------------------------------
with aba_processar:
    st.subheader("Integração com o Banco de Dados")
    st.write("Esta ação irá acionar o seu script `index.py` para ler os PDFs baixados e convertê-los.")
    
    if st.button("⚙️ Converter para JSON / Subir para o Banco"):
        caminho_script_index = os.path.join(DIRETORIO_LOADER, "index.py")
        
        if not os.path.exists(caminho_script_index):
            st.error(f"Não encontrei o arquivo `index.py` na pasta: {DIRETORIO_LOADER}")
        else:
            with st.spinner("Processando os dados... Isso pode demorar um pouco."):
                try:
                    # Prepara o ambiente forçando o Python a entender UTF-8 e emojis
                    ambiente = os.environ.copy()
                    ambiente["PYTHONIOENCODING"] = "utf-8"

                    # Roda o script com suporte total a caracteres especiais
                    resultado = subprocess.run(
                        ["python", caminho_script_index], 
                        capture_output=True, 
                        text=True,
                        encoding="utf-8",
                        env=ambiente
                    )
                    
                    if resultado.returncode == 0:
                        st.success("Conversão finalizada com sucesso!")
                        st.code(resultado.stdout, language="bash")
                    else:
                        st.error("Ocorreu um erro ao rodar o script.")
                        st.code(resultado.stderr, language="bash")
                except Exception as e:
                    st.error(f"Erro na execução: {e}")