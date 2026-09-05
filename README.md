# Resolução Automática de Questões com IA e Selenium

Script em Python que monitora uma página web (por exemplo, um questionário no Moodle) já aberta no Chrome, identifica automaticamente a questão de múltipla escolha exibida, envia o enunciado e as alternativas para um modelo de linguagem e apresenta a resposta sugerida em um popup nativo do sistema operacional.

## Como funciona

O script se conecta a uma instância do Chrome já em execução por meio do Chrome DevTools Protocol, sem abrir uma nova janela controlada pelo Selenium. A cada poll (intervalo configurável), ele:

1. Percorre todas as abas abertas no navegador.
2. Localiza blocos de questão (elementos com a classe `qtext`, padrão do Moodle) em cada aba.
3. Extrai o enunciado e as alternativas associadas a cada questão.
4. Confirma a leitura com uma segunda verificação, evitando processar conteúdo capturado no meio de um re-render da página.
5. Calcula uma assinatura (hash) da questão para não reprocessar a mesma pergunta repetidamente.
6. Envia o enunciado e as alternativas para a API da Groq, compatível com a API da OpenAI.
7. Exibe a resposta sugerida em uma janela de popup construída com Tkinter.

## Tecnologias utilizadas

- Python 3
- Selenium (conexão com o Chrome via CDP)
- Tkinter (exibição do popup de resposta)
- SDK da OpenAI, apontado para a API da Groq
- python-dotenv (carregamento de variáveis de ambiente)

## Pré-requisitos

- Python 3.10 ou superior.
- Google Chrome instalado.
- Uma chave de API válida da Groq (https://console.groq.com).

## Instalação

Clone o repositório e instale as dependências:

```bash
git clone <url-do-repositorio>
cd REPO
pip install -r requirements.txt
```

## Configuração

Crie um arquivo `.env` (ou `key.env`) na raiz do projeto com a sua chave da Groq, seguindo o modelo em `chave.env.example`:

```
GROQ_API_KEY=sua_chave_aqui
```

Esse arquivo é ignorado pelo Git (ver `.gitignore`) e não deve ser versionado.

## Uso

1. Inicie o Chrome com a porta de depuração remota habilitada:

   ```bash
   chrome --remote-debugging-port=9222
   ```

2. Navegue até a página do questionário e deixe a questão visível na tela.

3. Em outro terminal, execute o script:

   ```bash
   python test_models.py
   ```

4. O script passará a monitorar a página. Ao detectar uma nova questão, ele consulta a IA e exibe a resposta sugerida em um popup.

Para encerrar o monitoramento, interrompa o processo com `Ctrl+C` ou feche o Chrome conectado.

## Estrutura do projeto

```
REPO/
├── test_models.py          # Script principal
├── requirements.txt        # Dependências do projeto
├── chave.env.example       # Modelo de arquivo de variáveis de ambiente
├── setup.github/workflows/ # Workflow de verificação no GitHub Actions
└── .gitignore
```

## Integração contínua

O workflow definido em `setup.github/workflows/run-main.yml` valida, a cada push na branch `main`, que `test_models.py` compila sem erros de sintaxe ou dependências ausentes. A execução completa do script não é realizada em CI, pois depende de uma instância local do Chrome (porta 9222) e de um ambiente gráfico para o Tkinter.

## Limitações conhecidas

- A extração de alternativas foi ajustada para a estrutura HTML do Moodle e pode não funcionar em outras plataformas sem adaptação.
- Quando há múltiplas questões sem um contêiner identificável (`div.que`) na mesma página, o fallback de busca global de alternativas só é aplicado se houver exatamente uma questão na página, para evitar misturar alternativas de questões diferentes.
- O script depende de uma sessão do Chrome iniciada manualmente com depuração remota habilitada; ele não inicializa o navegador.

## Aviso

Este projeto tem finalidade educacional, para estudo de automação de navegador e integração com APIs de IA. O uso para obter respostas em avaliações reais pode violar as regras acadêmicas ou institucionais aplicáveis. O uso é de responsabilidade exclusiva de quem executa o script.
