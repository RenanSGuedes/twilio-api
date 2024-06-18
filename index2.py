import streamlit as st
import pandas as pd
import plotly.express as px
from twilio.rest import Client
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

# Função para obter mensagens filtradas por data
def get_messages(start_date, end_date):
    messages = client.messages.list(
        date_sent_after=start_date,
        date_sent_before=end_date
    )
    
    data = []
    for message in messages:
        data.append({
            "SID": message.sid,
            "De": message.from_,
            "Para": message.to,
            "Mensagem": message.body,
            "Data": message.date_sent,
            "Status": message.status,
            "Segmentos": message.num_segments,
            "Erro Cod.": message.error_code,
            "Erro Msg.": message.error_message,
            "URI": message.uri,
            "Data de Criação": message.date_created,
            "Data de Atualização": message.date_updated,
            "Direção": message.direction,
            "Preço": message.price,
            "Moeda": message.price_unit,
            "API Version": message.api_version
        })
    return pd.DataFrame(data)

# Interface do Streamlit para entrada de credenciais e número de telefone
st.title("Mensagens do WhatsApp - Twilio")

# Configurações da Twilio
col1, col2 = st.columns(2)
with col1:
    account_sid = st.text_input("Account SID")
with col2:
    auth_token = st.text_input("Auth Token", type="password")

# Verifica se as credenciais foram fornecidas
if account_sid and auth_token:
    client = Client(account_sid, auth_token)

    # Filtros
    st.header("Filtros")
    col1, col2 = st.columns(2)
    with col2:
        end_date = st.date_input("Data de Fim", datetime.now())
    with col1:
        # Define o valor padrão de start_date como 7 dias antes de end_date
        start_date_default = end_date - timedelta(days=7)
        start_date = st.date_input("Data de Início", start_date_default)

    # Convertendo start_date e end_date para datetime.datetime
    start_date = datetime.combine(start_date, datetime.min.time())
    end_date = datetime.combine(end_date, datetime.min.time())

    # Verificação do intervalo de 400 dias
    max_date_range = datetime.now() - timedelta(days=400)
    if start_date < max_date_range:
        st.warning(f"A data de início foi ajustada para estar dentro do intervalo de 400 dias.")
        start_date = max_date_range

    if start_date > end_date:
        st.error("Data de início não pode ser maior que a data de fim.")

    # Marcador de estado para controlar se os dados devem ser recarregados
    reload_data = st.button("Recarregar Dados")

    # Obtém mensagens apenas se o botão for clicado
    try:
        if reload_data:
            with st.spinner("Obtendo mensagens..."):
                messages_df = get_messages(start_date, end_date)

            st.session_state.messages_df = messages_df

        elif 'messages_df' not in st.session_state:
            st.warning("Por favor, clique em 'Recarregar Dados' para obter as mensagens.")

        # Exibição das mensagens se os dados estiverem disponíveis
        if 'messages_df' in st.session_state:
            messages_df = st.session_state.messages_df
            
            # Filtro por número de telefone (coluna "Para")
            st.subheader("Filtrar por Número de Telefone")
            unique_recipients = messages_df['Para'].unique()
            select_all = st.checkbox("Selecionar todos os usuários")

            if select_all:
                selected_recipients = unique_recipients.tolist()  # Converte para lista para garantir compatibilidade
            else:
                selected_recipients = st.multiselect('Escolha até 10 usuários', unique_recipients, max_selections=10)

            if len(selected_recipients) > 0:  # Verificação correta
                messages_df = messages_df[messages_df['Para'].isin(selected_recipients)]
            
            # Filtro por direção
            st.subheader("Filtrar por Direção")
            unique_directions = messages_df['Direção'].unique()
            selected_directions = st.multiselect('Escolha as direções das mensagens', unique_directions, default=unique_directions)
            
            if selected_directions:
                messages_df = messages_df[messages_df['Direção'].isin(selected_directions)]

            # Métrica de número de usuários diferentes
            num_unique_users = messages_df['Para'].nunique()
            st.metric(label="Número de Usuários Diferentes", value=num_unique_users)

            # Exibição da tabela de dados
            st.subheader("Tabela de Mensagens")
            st.dataframe(messages_df[[
                "Para",
                "Mensagem",
                "Data",
                "Status",
                "Direção"
            ]], 
                use_container_width=True,
                hide_index=True
            )
        
            # Gerando CSV
            csv = messages_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Baixar CSV",
                data=csv,
                file_name='mensagens_whatsapp.csv',
                mime='text/csv'
            )
            
            # Dividindo a visualização em 3 colunas
            col1, col2 = st.columns(2)
                
            with col1:
                # Gráfico de status das mensagens
                st.subheader("Status das Mensagens")
                status_counts = messages_df['Status'].value_counts().reset_index()
                status_counts.columns = ['Status', 'Count']
                fig_status_bar = px.bar(status_counts, x='Status', y='Count', title='Status das Mensagens')
                st.plotly_chart(fig_status_bar, use_container_width=True)

            with col2:
                # Gráfico de pizza dos status das mensagens
                st.subheader("Distribuição dos Status")
                fig_status_pie = px.pie(status_counts, values='Count', names='Status', title='Distribuição dos Status das Mensagens')
                st.plotly_chart(fig_status_pie, use_container_width=True)
            
            # Tabela com status por usuários
            st.subheader("Status por Usuário")
            user_status_counts = messages_df.groupby(['Para', 'Status']).size().unstack(fill_value=0).reset_index()
            
            st.dataframe(user_status_counts, use_container_width=True, hide_index=True)
    except:
        st.error(":x: Credenciais incorretas")

else:
    st.warning("Por favor, forneça as credenciais do Twilio e o número de telefone.")
