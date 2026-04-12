import json
import uuid
import os
import glob
import re
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def limpar_nome_universal(nome_original):
    """
    Limpa o nome do arquivo, removendo extensões, caracteres especiais 
    e resumindo padrões da Anvisa ou nomes muito longos.
    """
    nome_sem_extensao = os.path.splitext(nome_original)[0]
    
    # 1. Regra específica: Se for o padrão da Anvisa (separado por '_-_')
    if '_-_' in nome_sem_extensao:
        partes = nome_sem_extensao.split('_-_')
        # Pega as duas primeiras partes (Ex: CADERNO_1 e TITULO_DO_CADERNO)
        if len(partes) >= 2:
            nome_base = f"{partes[0]}_{partes[1]}"
        else:
            nome_base = nome_sem_extensao
    else:
        # 2. Regra geral: Para PDFs comuns
        nome_base = nome_sem_extensao

    # 3. Limpeza Universal: Substitui tudo que não for letra ou número por underline (_)
    nome_limpo = re.sub(r'[^a-zA-Z0-9_]', '_', nome_base)
    
    # Remove underlines duplicados que possam ter sobrado
    nome_limpo = re.sub(r'_+', '_', nome_limpo).strip('_')
    
    # Limita a 80 caracteres para evitar qualquer problema futuro no Windows
    return nome_limpo[:80]


def converter_pdfs_da_pasta():
    """
    Busca os PDFs na pasta de entrada, fatia o conteúdo e salva na pasta de saída.
    """
    # Definição das pastas
    pasta_entrada = "pdfs"
    pasta_saida = "jsons_chroma" # <-- Nome da nova pasta onde os JSONs vão ficar
    
    # Encontra o caminho absoluto de onde este script está rodando
    caminho_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_pdfs = os.path.join(caminho_atual, pasta_entrada)
    caminho_jsons = os.path.join(caminho_atual, pasta_saida)
    
    # CRIA A PASTA DE SAÍDA AUTOMATICAMENTE SE ELA NÃO EXISTIR
    os.makedirs(caminho_jsons, exist_ok=True)
    
    # Busca todos os arquivos com extensão .pdf na pasta selecionada
    arquivos_pdf = glob.glob(os.path.join(caminho_pdfs, "*.pdf"))

    if not arquivos_pdf:
        print(f"⚠️ Nenhum PDF encontrado em: {caminho_pdfs}")
        return

    print(f"🚀 Localizados {len(arquivos_pdf)} PDFs. Iniciando processamento...")

    # Configuração do fatiador (chunking)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=100
    )

    for caminho_completo in arquivos_pdf:
        nome_arquivo_original = os.path.basename(caminho_completo)
        
        try:
            # Caminho longo (\\\\?\\) para evitar o erro MAX_PATH (260 chars) do Windows
            caminho_longo = "\\\\?\\" + os.path.abspath(caminho_completo)
            
            # Aplica a inteligência de limpeza no nome
            nome_limpo = limpar_nome_universal(nome_arquivo_original)
            
            # Carregamento e fatiamento do PDF
            loader = PyPDFLoader(caminho_longo)
            paginas = loader.load()
            docs = text_splitter.split_documents(paginas)

            # Estrutura esperada pelo ChromaDB
            payload = {"ids": [], "documents": [], "metadatas": []}

            for i, doc in enumerate(docs):
                payload["ids"].append(f"id_{uuid.uuid4().hex[:6]}")
                payload["documents"].append(doc.page_content)
                payload["metadatas"].append({
                    "arquivo": f"{nome_limpo}.pdf",  # Salva o nome limpo no metadado
                    "pagina": doc.metadata.get("page", 0) + 1
                })

            # Define o caminho de saída para a NOVA PASTA
            caminho_saida = os.path.join(caminho_jsons, f"{nome_limpo}.json")
            
            # Salva o resultado
            with open(caminho_saida, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=4)
            
            print(f"✅ Sucesso: {nome_limpo}.json gerado na pasta '{pasta_saida}'.")

        except Exception as e:
            # Mostra apenas os 40 primeiros caracteres do nome original em caso de erro
            print(f"❌ Falha ao processar {nome_arquivo_original[:40]}... \n   Erro: {e}")

if __name__ == "__main__":
    converter_pdfs_da_pasta()