# pages/2_Dashboard.py

import streamlit as st
import pandas as pd
from datetime import datetime, date as dt_date_class, timedelta

# Importa funções e constantes do arquivo principal e de utilidades
from streamlit_app import check_permission, load_notifications, load_users
from constants import UI_TEXTS, FORM_DATA
from utils import get_deadline_status, display_notification_full_details


def run():
    if not check_permission('admin') and not check_permission('classificador'):
        st.error("❌ Acesso negado! Você não tem permissão para visualizar o dashboard.")
        return

    st.markdown("<h1 class='main-header'>Dashboard de Notificações</h1>", unsafe_allow_html=True)

    all_notifications = load_notifications()
    if not all_notifications:
        st.warning("⚠️ Nenhuma notificação encontrada para exibir no dashboard. Comece registrando uma nova notificação.")
        return

    df_notifications = pd.DataFrame(all_notifications)
    df_notifications['created_at_dt'] = pd.to_datetime(df_notifications['created_at'])
    df_notifications['occurrence_date_dt'] = pd.to_datetime(df_notifications['occurrence_date'])

    completed_statuses = ['aprovada', 'concluida']
    rejected_statuses = ['rejeitada', 'reprovada']

    tab_overview_list, tab_indicators = st.tabs(
        ["📊 Visão Geral e Lista", "📈 Indicadores e Gráficos"])

    with tab_overview_list:
        st.info("Visão geral e detalhada de todas as notificações registradas no sistema.")

        st.markdown("### Visão Geral e Métricas Chave")
        total = len(all_notifications)
        pending_classif = len(
            [n for n in all_notifications if n.get('status') == "pendente_classificacao"])
        in_progress_statuses = ['classificada', 'em_execucao', 'aguardando_classificador',
                                'aguardando_aprovacao', 'revisao_classificador_execucao']
        in_progress = len(
            [n for n in all_notifications if n.get('status') in in_progress_statuses])
        completed = len([n for n in all_notifications if n.get('status') in completed_statuses])
        rejected = len([n for n in all_notifications if n.get('status') in rejected_statuses])

        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        with col_m1:
            st.markdown(f"<div class='metric-card'><h4>Total</h4><p>{total}</p></div>",
                        unsafe_allow_html=True)
        with col_m2:
            st.markdown(
                f"<div class='metric-card'><h4>Pendente Classif.</h4><p>{pending_classif}</p></div>",
                unsafe_allow_html=True)
        with col_m3:
            st.markdown(
                f"<div class='metric-card'><h4>Em Andamento</h4><p>{in_progress}</p></div>",
                unsafe_allow_html=True)
        with col_m4:
            st.markdown(f"<div class='metric-card'><h4>Concluídas</h4><p>{completed}</p></div>",
                        unsafe_allow_html=True)
        with col_m5:
            st.markdown(f"<div class='metric-card'><h4>Rejeitadas</h4><p>{rejected}</p></div>",
                        unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("### Gráficos de Tendência e Distribuição")
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.markdown("#### Distribuição de Notificações por Status")
            status_mapping = {
                'pendente_classificacao': 'Pendente Classif. Inicial',
                'classificada': 'Classificada (Aguardando Exec.)',
                'em_execucao': 'Em Execução',
                'revisao_classificador_execucao': 'Aguardando Revisão Exec.',
                'aguardando_classificador': 'Aguardando Classif. (Revisão)',
                'aguardando_aprovacao': 'Aguardando Aprovação',
                'aprovada': 'Concluída (Aprovada)',
                'rejeitada': 'Rejeitada (Classif. Inicial)',
                'reprovada': 'Reprovada (Aprovação)'
            }
            status_count = {}
            for notification in all_notifications:
                status = notification.get('status', UI_TEXTS.text_na)
                mapped_status = status_mapping.get(status, status)
                status_count[mapped_status] = status_count.get(mapped_status, 0) + 1

            if status_count:
                status_df = pd.DataFrame(list(status_count.items()),
                                         columns=['Status', 'Quantidade'])
                status_order = [status_mapping.get(s) for s in
                                ['pendente_classificacao', 'classificada', 'em_execucao',
                                 'revisao_classificador_execucao',
                                 'aguardando_classificador',
                                 'aguardando_aprovacao', 'aprovada', 'rejeitada',
                                 'reprovada']]
                status_order = [s for s in status_order if
                                s and s in status_df['Status'].tolist()]
                if status_order:
                    status_df['Status'] = pd.Categorical(status_df['Status'],
                                                         categories=status_order, ordered=True)
                    status_df = status_df.sort_values('Status')
                st.bar_chart(status_df.set_index('Status'))
            else:
                st.info("Nenhum dado de status para gerar o gráfico.")

        with col_chart2:
            st.markdown("#### Notificações Criadas ao Longo do Tempo")
            if not df_notifications.empty:
                df_notifications_copy = df_notifications.copy()
                df_notifications_copy['month_year'] = df_notifications_copy['created_at_dt'].dt.to_period('M').astype(str)
                monthly_counts = df_notifications_copy.groupby('month_year').size().reset_index(
                    name='count')
                monthly_counts['month_year'] = pd.to_datetime(monthly_counts['month_year'])
                monthly_counts = monthly_counts.sort_values('month_year')
                monthly_counts['month_year'] = monthly_counts['month_year'].dt.strftime(
                    '%Y-%m')

                st.line_chart(monthly_counts.set_index('month_year'))
            else:
                st.info("Nenhum dado para gerar o gráfico de tendência.")

        st.markdown("---")

        st.markdown("### Lista Detalhada de Notificações")

        col_filters1, col_filters2, col_filters3 = st.columns(3)

        all_option_text = UI_TEXTS.multiselect_all_option

        if 'dashboard_filter_status' not in st.session_state: st.session_state.dashboard_filter_status = [
            all_option_text]
        if 'dashboard_filter_nnc' not in st.session_state: st.session_state.dashboard_filter_nnc = [
            all_option_text]
        if 'dashboard_filter_priority' not in st.session_state: st.session_state.dashboard_filter_priority = [
            all_option_text]
        if 'dashboard_filter_date_start' not in st.session_state: st.session_state.dashboard_filter_date_start = None
        if 'dashboard_filter_date_end' not in st.session_state: st.session_state.dashboard_filter_date_end = None
        if 'dashboard_search_query' not in st.session_state: st.session_state.dashboard_search_query = ""
        if 'dashboard_sort_column' not in st.session_state: st.session_state.dashboard_sort_column = 'created_at'
        if 'dashboard_sort_ascending' not in st.session_state: st.session_state.dashboard_sort_ascending = False

        with col_filters1:
            all_status_options_keys = list(status_mapping.keys())
            display_status_options_with_all = [all_option_text] + all_status_options_keys

            current_status_selection_raw = st.session_state.get(
                "dashboard_filter_status_select", [all_option_text])
            if all_option_text in current_status_selection_raw and len(
                    current_status_selection_raw) > 1:
                default_status_selection_for_display = [all_option_text]
            elif not current_status_selection_raw:
                default_status_selection_for_display = [all_option_text]
            else:
                default_status_selection_for_display = current_status_selection_raw

            st.session_state.dashboard_filter_status = st.multiselect(
                UI_TEXTS.multiselect_filter_status_label,
                options=display_status_options_with_all,
                format_func=lambda x: status_mapping.get(x, x.replace('_', ' ').title()),
                default=default_status_selection_for_display,
                key="dashboard_filter_status_select"
            )
            if all_option_text in st.session_state.dashboard_filter_status and len(
                    st.session_state.dashboard_filter_status) > 1:
                st.session_state.dashboard_filter_status = [all_option_text]
            elif not st.session_state.dashboard_filter_status:
                st.session_state.dashboard_filter_status = [all_option_text]

            applied_status_filters = [s for s in st.session_state.dashboard_filter_status if
                                      s != all_option_text]
            all_nnc_options = FORM_DATA.classificacao_nnc
            display_nnc_options_with_all = [all_option_text] + all_nnc_options
            current_nnc_selection_raw = st.session_state.get("dashboard_filter_nnc_select",
                                                                             [all_option_text])
            if all_option_text in current_nnc_selection_raw and len(
                    current_nnc_selection_raw) > 1:
                default_nnc_selection_for_display = [all_option_text]
            elif not current_nnc_selection_raw:
                default_nnc_selection_for_display = [all_option_text]
            else:
                default_nnc_selection_for_display = current_nnc_selection_raw

            st.session_state.dashboard_filter_nnc = st.multiselect(
                UI_TEXTS.multiselect_filter_nnc_label,
                options=display_nnc_options_with_all,
                default=default_nnc_selection_for_display,
                key="dashboard_filter_nnc_select"
            )
            if all_option_text in st.session_state.dashboard_filter_nnc and len(
                    st.session_state.dashboard_filter_nnc) > 1:
                st.session_state.dashboard_filter_nnc = [all_option_text]
            elif not st.session_state.dashboard_filter_nnc:
                st.session_state.dashboard_filter_nnc = [all_option_text]
            applied_nnc_filters = [n for n in st.session_state.dashboard_filter_nnc if
                                   n != all_option_text]

        with col_filters2:
            all_priority_options = FORM_DATA.prioridades
            display_priority_options_with_all = [all_option_text] + all_priority_options
            current_priority_selection_raw = st.session_state.get(
                "dashboard_filter_priority_select", [all_option_text])
            if all_option_text in current_priority_selection_raw and len(
                    current_priority_selection_raw) > 1:
                default_priority_selection_for_display = [all_option_text]
            elif not current_priority_selection_raw:
                default_priority_selection_for_display = [all_option_text]
            else:
                default_priority_selection_for_display = current_priority_selection_raw

            st.session_state.dashboard_filter_priority = st.multiselect(
                UI_TEXTS.multiselect_filter_priority_label,
                options=display_priority_options_with_all,
                default=default_priority_selection_for_display,
                key="dashboard_filter_priority_select"
            )
            if all_option_text in st.session_state.dashboard_filter_priority and len(
                    st.session_state.dashboard_filter_priority) > 1:
                st.session_state.dashboard_filter_priority = [all_option_text]
            elif not st.session_state.dashboard_filter_priority:
                st.session_state.dashboard_filter_priority = [all_option_text]
            applied_priority_filters = [p for p in st.session_state.dashboard_filter_priority if
                                        p != all_option_text]
            date_start_default = st.session_state.dashboard_filter_date_start or (
                df_notifications['created_at_dt'].min().date() if not df_notifications.empty else dt_date_class.today() - timedelta(
                    days=365)
            )
            date_end_default = st.session_state.dashboard_filter_date_end or (
                df_notifications['created_at_dt'].max().date() if not df_notifications.empty else dt_date_class.today()
            )

            st.session_state.dashboard_filter_date_start = st.date_input(
                "Data Inicial (Criação):", value=date_start_default,
                key="dashboard_filter_date_start_input"
            )
            st.session_state.dashboard_filter_date_end = st.date_input(
                "Data Final (Criação):", value=date_end_default,
                key="dashboard_filter_date_date_end_input"
            )

        with col_filters3:
            st.session_state.dashboard_search_query = st.text_input(
                "Buscar (Título, Descrição, ID):",
                value=st.session_state.dashboard_search_query,
                key="dashboard_search_query_input"
            ).lower()

            sort_options_map = {
                'ID': 'id',
                'Data de Criação': 'created_at',
                'Título': 'title',
                'Local': 'location',
                'Prioridade': 'classification.prioridade',
            }
            sort_options_display = [UI_TEXTS.selectbox_sort_by_placeholder] + list(
                sort_options_map.keys())
            selected_sort_option_display = st.selectbox(
                UI_TEXTS.selectbox_sort_by_label,
                options=sort_options_display,
                index=0,
                key="dashboard_sort_column_select"
            )
            if selected_sort_option_display != UI_TEXTS.selectbox_sort_by_placeholder:
                st.session_state.dashboard_sort_column = sort_options_map[selected_sort_option_display]
            else:
                st.session_state.dashboard_sort_column = 'created_at'

            st.session_state.dashboard_sort_ascending = st.checkbox(
                "Ordem Crescente", value=st.session_state.dashboard_sort_ascending,
                key="dashboard_sort_ascending_checkbox"
            )

        filtered_notifications = []
        for notification in all_notifications:
            match = True

            if applied_status_filters:
                if notification.get('status') not in applied_status_filters:
                    match = False
            if match and applied_nnc_filters:
                classif_nnc = notification.get('classification', {}).get('nnc')
                if classif_nnc not in applied_nnc_filters:
                    match = False
            if match and applied_priority_filters:
                priority = notification.get('classification', {}).get('prioridade')
                if priority not in applied_priority_filters:
                    match = False

            if match and st.session_state.dashboard_filter_date_start and st.session_state.dashboard_filter_date_end:
                created_at_date = datetime.fromisoformat(notification['created_at']).date()
                if not (
                        st.session_state.dashboard_filter_date_start <= created_at_date <= st.session_state.dashboard_filter_date_end):
                    match = False

            if match and st.session_state.dashboard_search_query:
                query = st.session_state.dashboard_search_query
                search_fields = [
                    str(notification.get('id', '')).lower(),
                    notification.get('title', '').lower(),
                    notification.get('description', '').lower(),
                    notification.get('location', '').lower()
                ]
                if not any(query in field for field in search_fields):
                    match = False

            if match:
                filtered_notifications.append(notification)

        def get_sort_value(notif, sort_key):
            if sort_key == 'id':
                return notif.get('id', 0)
            elif sort_key == 'created_at':
                return datetime.fromisoformat(notif.get('created_at', '1900-01-01T00:00:00'))
            elif sort_key == 'title':
                return notif.get('title', '')
            elif sort_key == 'location':
                return notif.get('location', '')
            elif sort_key == 'classification.prioridade':
                priority_value = notif.get('classification', {}).get('prioridade', 'Baixa')
                priority_order_val = {'Crítica': 4, 'Alta': 3, 'Média': 2, 'Baixa': 1,
                                      UI_TEXTS.text_na: 0,
                                      UI_TEXTS.selectbox_default_prioridade_resolucao: 0}
                return priority_order_val.get(priority_value, 0)
            return None

        actual_sort_column = st.session_state.dashboard_sort_column
        if actual_sort_column in sort_options_map.values():
            filtered_notifications.sort(
                key=lambda n: get_sort_value(n, actual_sort_column),
                reverse=not st.session_state.dashboard_sort_ascending
            )

        st.write(f"**Notificações Encontradas: {len(filtered_notifications)}**")

        items_per_page_options = [5, 10, 20, 50]
        items_per_page_display_options = [UI_TEXTS.selectbox_items_per_page_placeholder] + [
            str(x) for x in items_per_page_options]

        if 'dashboard_items_per_page' not in st.session_state: st.session_state.dashboard_items_per_page = 10

        selected_items_per_page_display = st.selectbox(
            UI_TEXTS.selectbox_items_per_page_label,
            options=items_per_page_display_options,
            index=items_per_page_display_options.index(
                str(st.session_state.dashboard_items_per_page)) if str(
                st.session_state.dashboard_items_per_page) in items_per_page_display_options else 0,
            key="dashboard_items_per_page_select"
        )
        if selected_items_per_page_display != UI_TEXTS.selectbox_items_per_page_placeholder:
            st.session_state.dashboard_items_per_page = int(selected_items_per_page_display)
        else:
            st.session_state.dashboard_items_per_page = 10

        total_pages = (
                              len(filtered_notifications) + st.session_state.dashboard_items_per_page - 1) // st.session_state.dashboard_items_per_page
        if total_pages == 0: total_pages = 1

        if 'dashboard_current_page' not in st.session_state: st.session_state.dashboard_current_page = 1
        st.session_state.dashboard_current_page = st.number_input(
            "Página:", min_value=1, max_value=total_pages,
            value=st.session_state.dashboard_current_page,
            key="dashboard_current_page_input"
        )

        start_idx = (
                            st.session_state.dashboard_current_page - 1) * st.session_state.dashboard_items_per_page
        end_idx = start_idx + st.session_state.dashboard_items_per_page
        paginated_notifications = filtered_notifications[start_idx:end_idx]

        if not paginated_notifications:
            st.info("Nenhuma notificação encontrada com os filtros e busca aplicados.")
        else:
            for notification in paginated_notifications:
                status_class = f"status-{notification.get('status', UI_TEXTS.text_na).replace('_', '-')}"
                created_at_str = datetime.fromisoformat(notification['created_at']).strftime(
                    '%d/%m/%Y %H:%M:%S')
                current_status_display = status_mapping.get(
                    notification.get('status', UI_TEXTS.text_na),
                    notification.get('status', UI_TEXTS.text_na).replace('_', ' ').title())

                classif_info = notification.get('classification') or {}
                deadline_date_str = classif_info.get('deadline_date')
                deadline_html = ""
                if deadline_date_str:
                    deadline_date_formatted = datetime.fromisoformat(
                        deadline_date_str).strftime('%d/%m/%Y')
                    deadline_status = get_deadline_status(deadline_date_str)
                    deadline_html = f" | <strong class='{deadline_status['class']}'>Prazo: {deadline_date_formatted} ({deadline_status['text']})</strong>"

                st.markdown(f"""
                                    <div class="notification-card">
                                        <h4>#{notification.get('id', UI_TEXTS.text_na)} - {notification.get('title', UI_TEXTS.text_na)}</h4>
                                        <p><strong>Status:</strong> <span class="{status_class}">{current_status_display}</span> {deadline_html}</p>
                                        <p><strong>Local:</strong> {notification.get('location', UI_TEXTS.text_na)} | <strong>Criada em:</strong> {created_at_str}</p>
                                    </div>
                                    """, unsafe_allow_html=True)

                with st.expander(
                        f"👁️ Visualizar Detalhes - Notificação #{notification.get('id', UI_TEXTS.text_na)}"):
                    display_notification_full_details(notification,
                                                      st.session_state.user.get('id') if st.session_state.authenticated else None,
                                                      st.session_state.user.get('username') if st.session_state.authenticated else None)

    with tab_indicators:
        st.info("Explore os indicadores e tendências das notificações, com filtros de período.")
        st.markdown("### Seleção de Período para Indicadores")

        min_date = df_notifications['created_at_dt'].min().date() if not df_notifications.empty else dt_date_class.today() - timedelta(days=365)
        max_date = df_notifications['created_at_dt'].max().date() if not df_notifications.empty else dt_date_class.today()
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date_indicators = st.date_input("Data de Início", value=min_date,
                                                  key="start_date_indicators")
        with col_date2:
            end_date_indicators = st.date_input("Data de Fim", value=max_date,
                                                key="end_date_indicators")

        df_filtered_by_period = df_notifications[
            (df_notifications['created_at_dt'].dt.date >= start_date_indicators) &
            (df_notifications['created_at_dt'].dt.date <= end_date_indicators)].copy()

        if df_filtered_by_period.empty:
            st.warning("⚠️ Não há dados para o período selecionado para gerar os indicadores.")
            return

        st.markdown("---")

        st.markdown("#### Quantidade de Notificações por Mês (Abertas, Concluídas, Rejeitadas)")

        df_monthly = df_filtered_by_period.copy()
        df_monthly['month_year'] = df_monthly['created_at_dt'].dt.to_period('M').astype(str)

        df_monthly['status_category'] = 'Aberta'
        df_monthly.loc[df_monthly['status'].isin(completed_statuses), 'status_category'] = 'Concluída'
        df_monthly.loc[df_monthly['status'].isin(rejected_statuses), 'status_category'] = 'Rejeitada'

        monthly_counts = df_monthly.groupby(['month_year', 'status_category']).size().unstack(
            fill_value=0)

        all_months_in_range = pd.period_range(start=start_date_indicators,
                                              end=end_date_indicators, freq='M').astype(
            str)
        monthly_counts = monthly_counts.reindex(all_months_in_range, fill_value=0)
        if not monthly_counts.empty:
            st.line_chart(monthly_counts)
        else:
            st.info("Nenhuma notificação encontrada no período para este gráfico.")

        st.markdown("---")

        st.markdown("#### Pendência de Análises por Mês")
        pending_analysis_statuses = ['pendente_classificacao', 'aguardando_classificador',
                                     'revisao_classificador_execucao']
        df_pending_analysis = df_filtered_by_period[
            df_filtered_by_period['status'].isin(pending_analysis_statuses)].copy()

        all_notified_departments_unique = sorted(
            df_notifications['notified_department'].unique().tolist())
        notified_departments_filter_options = ['Todos'] + all_notified_departments_unique
        selected_notified_dept = st.selectbox("Filtrar por Setor Notificado:",
                                              notified_departments_filter_options,
                                              key="pending_dept_filter")

        if selected_notified_dept != 'Todos':
            df_pending_analysis = df_pending_analysis[
                df_pending_analysis['notified_department'] == selected_notified_dept]

        if not df_pending_analysis.empty:
            df_pending_analysis['month_year'] = df_pending_analysis['created_at_dt'].dt.to_period('M').astype(str)
            monthly_pending_counts = df_pending_analysis.groupby('month_year').size().reset_index(name='Quantidade')

            all_months_in_range_pending = pd.period_range(start=start_date_indicators,
                                                          end=end_date_indicators,
                                                          freq='M').astype(str)
            monthly_pending_counts = monthly_pending_counts.set_index('month_year').reindex(
                all_months_in_range_pending,
                fill_value=0).reset_index()
            monthly_pending_counts.columns = ['month_year', 'Quantidade']

            st.bar_chart(monthly_pending_counts.set_index('month_year'))
        else:
            st.info("Nenhuma pendência de análise encontrada no período e filtro selecionados.")

        st.markdown("---")

        st.markdown("#### Top 10 Setores Notificados e Notificantes")
        col_top1, col_top2 = st.columns(2)

        with col_top1:
            st.markdown("##### Top 10 Setores Notificados")
            if not df_filtered_by_period.empty:
                top_notified = df_filtered_by_period['notified_department'].value_counts().nlargest(10)
                if not top_notified.empty:
                    st.bar_chart(top_notified)
                else:
                    st.info("Nenhum dado de setor notificado para o período.")
            else:
                st.info("Nenhum dado de setor notificado para o período.")

        with col_top2:
            st.markdown("##### Top 10 Setores Notificantes")
            if not df_filtered_by_period.empty:
                top_reporting = df_filtered_by_period['reporting_department'].value_counts().nlargest(10)
                if not top_reporting.empty:
                    st.bar_chart(top_reporting)
                else:
                    st.info("Nenhum dado de setor notificante para o período.")
            else:
                st.info("Nenhum dado de setor notificante para o período.")

        st.markdown("---")

        st.markdown("#### Classificação das Notificações (NNC e Tipo Principal)")

        df_completed_period = df_filtered_by_period[
            df_filtered_by_period['status'].isin(completed_statuses)].copy()
        df_open_period = df_filtered_by_period[
            ~df_filtered_by_period['status'].isin(
                completed_statuses + rejected_statuses)].copy()

        col_classif1, col_classif2 = st.columns(2)

        with col_classif1:
            st.markdown("##### NNC - Concluídas")
            if not df_completed_period.empty:
                completed_nnc = df_completed_period['classification'].apply(
                    lambda x: x.get('nnc') if x else None).value_counts().dropna()
                if not completed_nnc.empty:
                    st.bar_chart(completed_nnc)
                else:
                    st.info("Nenhuma classificação NNC para notificações concluídas no período.")
            else:
                st.info("Nenhuma notificação concluída no período.")

        with col_classif2:
            st.markdown("##### NNC - Abertas")
            if not df_open_period.empty:
                open_nnc = df_open_period['classification'].apply(
                    lambda x: x.get('nnc') if x else None).value_counts().dropna()
                if not open_nnc.empty:
                    st.bar_chart(open_nnc)
                else:
                    st.info("Nenhuma classificação NNC para notificações abertas no período.")
            else:
                st.info("Nenhuma notificação aberta no período.")

        col_classif3, col_classif4 = st.columns(2)
        with col_classif3:
            st.markdown("##### Tipo Principal - Concluídas")
            if not df_completed_period.empty:
                completed_main_type = df_completed_period['classification'].apply(
                    lambda x: x.get('event_type_main') if x else None).value_counts().dropna()
                if not completed_main_type.empty:
                    st.bar_chart(completed_main_type)
                else:
                    st.info("Nenhum tipo principal para notificações concluídas no período.")
            else:
                st.info("Nenhuma notificação concluída no período.")

        with col_classif4:
            st.markdown("##### Tipo Principal - Abertas")
            if not df_open_period.empty:
                open_main_type = df_open_period['classification'].apply(
                    lambda x: x.get('event_type_main') if x else None).value_counts().dropna()
                if not open_main_type.empty:
                    st.bar_chart(open_main_type)
                else:
                    st.info("Nenhuma tipo principal para notificações abertas no período.")
            else:
                st.info("Nenhuma notificação aberta no período.")