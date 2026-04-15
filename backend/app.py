import streamlit as st
import requests
from bs4 import BeautifulSoup
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import time

BASE_URL = "https://www.gov.br"
headers = {"User-Agent": "Mozilla/5.0"}
output_dir = "cadernos"
os.makedirs(output_dir, exist_ok=True)

# =========================
# FUNÇÕES DE BUSCA
# =========================
def get_links_requests(url):
    st.write("🔎 Tentando método rápido (requests)...")
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
    st.write("🤖 Site bloqueou. Usando método avançado (Selenium)...")
    service = Service("chromedriver.exe") # Lembre-se de ter o chromedriver na mesma pasta
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

# =========================
# INTERFACE DO SITE
# =========================
# Isso cria o título e o textozinho na tela
st.title("📥 Baixador de PDFs Massivo")
st.markdown("Insira o link da página do Gov.br abaixo para baixar todos os cadernos disponíveis.")

# Cria uma caixa de texto para você digitar a URL
url_input = st.text_input(
    "URL da página:", 
    value="https://www.gov.br/anvisa/pt-br/centraisdeconteudo/publicacoes/servicosdesaude/manuais/cadernos-de-seguranca-do-paciente-e-qualidade-em-servicos-de-saude-2024-versoes-preliminares-nao-finalizadas-aguardando-o-envio-de-sugestoes"
)

# Cria o botão. O código abaixo só roda se o botão for clicado.
if st.button("🚀 Iniciar Download"):
    
    # st.spinner cria uma animação de "carregando"
    with st.spinner("Procurando os links na página..."):
        links = get_links_requests(url_input)
        
        if not links:
            links = get_links_selenium(url_input)

    if not links:
        st.error("❌ Nenhum caderno encontrado nessa página.")
    else:
        st.success(f"📚 {len(links)} cadernos encontrados! Começando o download...")

        # Barra de progresso visual
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
                    match = re.findall('filename="(.+)"', pdf.headers["content-disposition"])
                    if match:
                        filename = match[0]
                if not filename:
                    filename = os.path.basename(download_link)
                if not filename.endswith(".pdf"):
                    filename = "arquivo.pdf"
                
                filename = filename.replace("%20", " ")
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, "wb") as f:
                    f.write(pdf.content)
                
                # Mostra o arquivo que acabou de ser baixado
                st.write(f"✅ Salvo: `{filename}`")
            
            # Atualiza a barra de progresso
            progresso_atual = int(((i + 1) / len(links)) * 100)
            barra_progresso.progress(progresso_atual)

        st.balloons() # Solta balões na tela quando termina!
        st.success("🎉 TODOS OS DOWNLOADS FORAM FINALIZADOS!")