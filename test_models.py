import hashlib
import os
import time

import tkinter as tk
from tkinter import messagebox

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchWindowException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import openai

load_dotenv()

POLL_SECONDS = 2
MIN_TAMANHO_PERGUNTA = 10
CONFIRMACAO_DELAY = 0.5  # tempo entre duas leituras, para não processar a página no meio de um re-render

# 1. Configuração do Driver (Global)
options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

try:
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


def buscar_alternativas(escopo):
    # No Moodle as alternativas ficam dentro de .answer ou .flex-fill
    elementos_opcoes = escopo.find_elements(By.CSS_SELECTOR, ".answer div.flex-fill.ml-1")
    if not elementos_opcoes:
        # Seletor alternativo caso o de cima mude
        elementos_opcoes = escopo.find_elements(By.CSS_SELECTOR, ".answer label")
    return [opt.text for opt in elementos_opcoes if opt.text.strip() != ""]


def localizar_container(bloco_qtext):
    """Sobe até a div.que (bloco Moodle de uma questão), para restringir a busca de
    alternativas a essa questão especifica quando há várias na mesma página."""
    try:
        return bloco_qtext.find_element(
            By.XPATH,
            "./ancestor::div[contains(concat(' ', normalize-space(@class), ' '), ' que ')][1]",
        )
    except Exception:
        return None


def ler_questao(bloco_qtext, permitir_fallback_global):
    pergunta = bloco_qtext.text
    if len(pergunta.strip()) <= MIN_TAMANHO_PERGUNTA:
        return None

    container = localizar_container(bloco_qtext)
    if container is not None:
        lista_alternativas = buscar_alternativas(container)
    elif permitir_fallback_global:
        # Tema sem div.que reconhecível: só é seguro buscar na página toda
        # quando há uma única questão nela (senão misturaria alternativas de outra).
        lista_alternativas = buscar_alternativas(driver)
    else:
        lista_alternativas = []

    if not lista_alternativas:
        return None

    return pergunta, lista_alternativas


def assinatura(pergunta, alternativas):
    bruto = pergunta + "|" + "|".join(alternativas)
    return hashlib.md5(bruto.encode("utf-8")).hexdigest()


def processar_questao(pergunta, lista_alternativas):
    try:
        # Monta o prompt para a IA
        texto_alternativas = "\n".join(
            f"{chr(65 + i)}) {texto}" for i, texto in enumerate(lista_alternativas)
        )
        prompt = (
            f"Pergunta: {pergunta}\n\nAlternativas:\n{texto_alternativas}\n\n"
            "Responda apenas com a letra correta."
        )

        print("Solicitando resposta para a IA...")
        client = openai.OpenAI()  # Usando a sintaxe da versão mais nova
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        resposta_ia = completion.choices[0].message.content.strip()
        print(f"IA respondeu: {resposta_ia}")
        mostrar_popup(pergunta, resposta_ia)
    except Exception as e:
        print(f"Erro ao consultar a IA: {e}")


# 2. Loop de Monitoramento
print("Monitorando a página... Troque de questão no navegador para disparar.")
print(f"(poll a cada {POLL_SECONDS}s; cobre todas as abas abertas e todas as questões de cada página)")

estado_perguntas = {}  # (janela, indice_na_pagina) -> assinatura da última questão processada nela

while True:
    try:
        handles = driver.window_handles
    except WebDriverException as e:
        print(f"Perdi a conexão com o Chrome (fechou o navegador?): {e}")
        break

    for handle in handles:
        try:
            driver.switch_to.window(handle)
            blocos_qtext = driver.find_elements(By.CLASS_NAME, "qtext")
        except NoSuchWindowException:
            # Aba foi fechada entre o window_handles e o switch_to; ignora e segue.
            continue
        except WebDriverException as e:
            print(f"Erro ao acessar aba: {e}")
            continue

        permitir_fallback_global = len(blocos_qtext) == 1

        for indice, bloco in enumerate(blocos_qtext):
            try:
                resultado = ler_questao(bloco, permitir_fallback_global)
                if resultado is None:
                    continue

                # Segunda leitura para confirmar que o DOM não está no meio de uma
                # transição (evita processar uma questão com texto truncado).
                time.sleep(CONFIRMACAO_DELAY)
                confirmacao = ler_questao(bloco, permitir_fallback_global)
                if confirmacao is None or confirmacao != resultado:
                    continue

                pergunta, lista_alternativas = confirmacao
                chave = (handle, indice)
                nova_assinatura = assinatura(pergunta, lista_alternativas)

                if estado_perguntas.get(chave) != nova_assinatura:
                    estado_perguntas[chave] = nova_assinatura
                    print(f"\n--- Nova questão detectada (posição {indice + 1}) ---")
                    processar_questao(pergunta, lista_alternativas)

            except StaleElementReferenceException:
                # Página re-renderizou entre o find_elements e a leitura; tenta de novo no próximo poll.
                continue
            except Exception as e:
                print(f"Erro ao processar questão: {e}")
                continue

    time.sleep(POLL_SECONDS)
