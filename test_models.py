import os
import time
import tkinter as tk
from tkinter import messagebox
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import openai

load_dotenv()
openai.api_key = os.environ.get("OPENAI_API_KEY")

# 1. Configuração do Driver (Global)
options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

try:
    # Inicializamos o driver aqui para que ele esteja disponível para todo o script
    driver = webdriver.Chrome(options=options)
    print("Conectado ao Chrome com sucesso!")
except Exception as e:
    print(f"Erro ao conectar: {e}. Verifique se o Chrome está aberto na porta 9222.")
    exit()

def mostrar_popup(pergunta, resposta):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    # Mostra apenas os primeiros 150 caracteres da pergunta para não travar o popup
    messagebox.showinfo("Resposta da IA", f"Questão: {pergunta[:150]}...\n\nSugerida: {resposta}")
    root.destroy()

def processar_questao():
    try:
        # Busca o texto da pergunta
        pergunta = driver.find_element(By.CLASS_NAME, "qtext").text
        
        # Busca as alternativas (No Moodle ficam dentro de .answer ou .flex-fill)
        # O seletor abaixo busca os textos das opções (a, b, c, d, e)
        elementos_opcoes = driver.find_elements(By.CSS_SELECTOR, ".answer div.flex-fill.ml-1")
        
        if not elementos_opcoes:
            # Seletor alternativo caso o de cima mude
            elementos_opcoes = driver.find_elements(By.CSS_SELECTOR, ".answer label")

        lista_alternativas = [opt.text for opt in elementos_opcoes if opt.text.strip() != ""]
        
        if not lista_alternativas:
            print("Não encontrei as alternativas.")
            return

        # Monta o prompt para a IA
        texto_alternativas = "\n".join([f"{chr(65+i)}) {texto}" for i, texto in enumerate(lista_alternativas)])
        
        prompt = f"Pergunta: {pergunta}\n\nAlternativas:\n{texto_alternativas}\n\nResponda apenas com a letra correta."

        print("Solicitando resposta para a IA...")
        client = openai.OpenAI() # Usando a sintaxe da versão mais nova
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        resposta_ia = completion.choices[0].message.content.strip()
        print(f"IA respondeu: {resposta_ia}")
        mostrar_popup(pergunta, resposta_ia)

    except Exception as e:
        print(f"Erro ao processar: {e}")

# 2. Loop de Monitoramento
print("Monitorando a página... Troque de questão no navegador para disparar.")
ultima_pergunta = ""

while True:
    try:
        # Busca o elemento da pergunta na tela
        elementos_q = driver.find_elements(By.CLASS_NAME, "qtext")
        
        if elementos_q:
            texto_atual = elementos_q[0].text
            
            # Se a pergunta mudou e não está vazia
            if texto_atual != ultima_pergunta and len(texto_atual.strip()) > 10:
                ultima_pergunta = texto_atual
                print("\n--- Nova pergunta detectada! ---")
                processar_questao()
                
    except Exception as e:
        # Se o driver perder a conexão (ex: fechou o chrome)
        print(f"Erro no loop: {e}")
        break
        
    time.sleep(3)