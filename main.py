import streamlit as st
import pandas as pd
from io import BytesIO
from io import StringIO
import google.generativeai as genai
import fitz  # PyMuPDF

# Configuração da API do Generative AI
API_KEY = 'AIzaSyAsHT-MDvucg2G6qm8apVrNPWpuUsuyND8'
genai.configure(api_key=API_KEY)

# Configuração do modelo
model = genai.GenerativeModel('gemini-1.5-flash-002')

def upload_file_to_genai(file_object, display_name):
    """Faz o upload do arquivo para a Generative AI."""
    return genai.upload_file(file_object, display_name=display_name, mime_type="application/pdf")

def extract_info_from_pdf(uploaded_file, display_name, user_request=None):
    """Envia o arquivo para o modelo Generative AI e retorna o texto extraído."""
    uploaded_file_genai = upload_file_to_genai(uploaded_file, display_name)
    if user_request:
        prompt = f"Por favor, extraia as informações do documento e me forneça em formato de tabela Markdown. A tabela deve incluir as seguintes informações: {user_request}. Retorne apenas a tabela, sem nunhum texto acima ou abaixo. Retorne sempre em formato colunar."
    else:
        prompt = "Por favor, extraia as informações do documento e me forneça em formato de tabela Markdown. Extraia as principais informações desta invoice. Retorne apenas a tabela, sem nunhum texto acima ou abaixo. Retorne apenas a tabela, sem nunhum texto acima ou abaixo. Retorne sempre em formato colunar."
    response = model.generate_content(
        [uploaded_file_genai, prompt]
    )
    return response.text

def parse_extracted_info_to_table(extracted_text):
    """Converte o texto extraído em formato tabular para salvar em Excel."""
    df = pd.read_csv(StringIO(extracted_text), sep="|", engine="python", skipinitialspace=True)
    df = df.iloc[:, 1:-1] # Remove colunas extras vazias

    return df

def create_excel_download(dataframe):
    """Cria um arquivo Excel a partir de um DataFrame."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Dados Extraídos")
    processed_data = output.getvalue()
    return processed_data

def render_pdf_pages(uploaded_file):
    """Lê o PDF e converte as páginas em imagens para exibição."""
    pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    images = []
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        # Renderiza a página como imagem
        pix = page.get_pixmap()
        image = BytesIO(pix.tobytes(output="png"))
        images.append(image)
    return images

def ask_question_to_genai(uploaded_file, question):
    """Faz uma pergunta ao Generative AI sobre o PDF."""
    uploaded_file_genai = upload_file_to_genai(uploaded_file, "Pergunta PDF")
    questionF = 'Sempre responda em português, mesmo que a pergunta ou o documento estejam em outro idioma.\n' +  question
    response = model.generate_content(
        [uploaded_file_genai,questionF]
    )
    return response.text

# Streamlit App
def main():
    st.title("Protótipo - Extração de Dados de PDFs com Generative AI")
    st.write("Envie um arquivo PDF e extraia informações importantes com a ajuda de Generative AI.")

    uploaded_file = st.file_uploader("Faça upload do arquivo PDF", type="pdf")

    if uploaded_file:
        st.success("Arquivo enviado com sucesso!")
        
        # Mostrar o PDF carregado na tela
        st.write("### Visualização do PDF Carregado")
        with st.expander("Visualizar PDF"):
            try:
                pdf_pages = render_pdf_pages(uploaded_file)
                for page_num, page_image in enumerate(pdf_pages):
                    st.image(page_image, caption=f"Página {page_num + 1}", use_column_width=True)
            except Exception as e:
                st.error(f"Erro ao renderizar o PDF: {e}")

        # Solicitar lista de informações ao usuário
        st.write("### Escolha as Informações que Deseja Extrair")
        user_info_list = st.text_area(
            "Digite as informações que você gostaria de ver no Excel, separadas por vírgulas.",
            placeholder="Exemplo: Nome, Endereço, Data, Valor Total",
        )

        # Processar o arquivo com Generative AI
        if st.button("Extrair Informações com AI"):
            user_request = user_info_list.strip('|') if user_info_list else None
            with st.spinner("Consultando a Generative AI..."):
                extracted_text = extract_info_from_pdf(uploaded_file, uploaded_file.name, user_request)
            st.success("Informações extraídas com sucesso!")

            # Mostrar as informações extraídas
            st.text_area("Informações Extraídas:", extracted_text, height=300)

            # Converter para tabela
            extracted_table = parse_extracted_info_to_table(extracted_text)

            # Exibir a tabela extraída
            st.write("### Dados Extraídos")
            st.dataframe(extracted_table)

            # Gerar botão para download em Excel
            excel_data = create_excel_download(extracted_table)
            st.download_button(
                label="📥 Baixar Informações em Excel",
                data=excel_data,
                file_name="dados_extraidos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        # Chat interativo com histórico
        st.write("### Perguntas sobre o PDF")
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Exibir histórico de mensagens
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Entrada para nova pergunta
        if prompt := st.chat_input("Digite sua pergunta sobre o PDF:"):
            # Adicionar pergunta do usuário ao histórico
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            # Consultar Generative AI
            with st.spinner("Consultando a Generative AI..."):
                try:
                    response = ask_question_to_genai(uploaded_file, prompt)
                except Exception as e:
                    response = f"Erro ao consultar o modelo: {e}"

            # Adicionar resposta ao histórico e exibir
            st.chat_message("assistant").markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
