# pages/4_Execucao.py (continuação)

import streamlit as st
from datetime import datetime
import time as time_module

# Importa funções e constantes do arquivo principal e de utilidades
from streamlit_app import check_permission, load_notifications, load_users, update_notification, add_history_entry, add_notification_action, get_notification_actions
from constants import UI_TEXTS, FORM_DATA
from utils import get_deadline_status, display_notification_full_details, save_uploaded_file_to_disk, get_attachment_data, _clear_execution_form_state


def run():
    """Renderiza a página para executores visualizarem notificações atribuídas e registrarem ações."""
    if not check_permission('executor'):
        st.error("❌ Acesso negado! Você não tem permissão para executar notificações.")
        return

    st.markdown("<h1 class='main-header'>⚡ Execução de Notificações</h1>", unsafe_allow_html=True)
    st.info("Nesta página, você pode visualizar as notificações atribuídas a você, registrar as ações executadas e marcar sua parte como concluída.")
    all_notifications = load_notifications()
    user_id_logged_in = st.session_state.user.get('id')
    user_username_logged_in = st.session_state.user.get('username')

    all_users = load_users()
    display_name_to_id_map = {
        f"{user.get('name', UI_TEXTS.text_na)} ({user.get('username', UI_TEXTS.text_na)})": user['id']
        for user in all_users
    }

    user_active_notifications = []
    active_execution_statuses = ['classificada', 'em_execucao']
    for notification in all_notifications:
        is_assigned_to_current_user = False
        assigned_executors_raw = notification.get('executors', [])

        for executor_entry in assigned_executors_raw:
            if isinstance(executor_entry, int) and executor_entry == user_id_logged_in:
                is_assigned_to_current_user = True
                break

        if is_assigned_to_current_user and notification.get('status') in active_execution_statuses:
            user_active_notifications.append(notification)

    closed_statuses = ['aprovada', 'rejeitada', 'reprovada', 'concluida']
    closed_my_exec_notifications = [
        n for n in all_notifications
        if n.get('status') in closed_statuses and user_id_logged_in in n.get('executors', [])
    ]

    if not user_active_notifications and not closed_my_exec_notifications:
        st.info("✅ Não há notificações ativas atribuídas a você no momento. Verifique com seu gestor ou classificador.")
        return

    st.success(f"Você tem {len(user_active_notifications)} notificação(es) atribuída(s) aguardando ou em execução.")
    tab_active_notifications, tab_closed_my_exec_notifs = st.tabs(
        ["🔄 Notificações Atribuídas (Ativas)", f"✅ Minhas Ações Encerradas ({len(closed_my_exec_notifications)})"]
    )

    with tab_active_notifications:
        st.markdown("### Notificações Aguardando ou Em Execução")
        priority_order = {p: i for i, p in enumerate(FORM_DATA.prioridades)}
        user_active_notifications.sort(key=lambda x: (
            priority_order.get(x.get('classification', {}).get('prioridade', 'Baixa'), len(FORM_DATA.prioridades)),
            datetime.fromisoformat(x.get('created_at', '1900-01-01T00:00:00')).timestamp()
        ))

        for notification in user_active_notifications:
            status_class = f"status-{notification.get('status', UI_TEXTS.text_na).replace('_', '-')}"
            classif_info = notification.get('classification') or {}
            prioridade_display = classif_info.get('prioridade', UI_TEXTS.text_na)
            prioridade_display = prioridade_display if prioridade_display != 'Selecionar' else f"{UI_TEXTS.text_na} (Não Classificado)"

            deadline_date_str = classif_info.get('deadline_date')
            concluded_timestamp_str = (notification.get('conclusion') or {}).get('timestamp')

            deadline_status = get_deadline_status(deadline_date_str, concluded_timestamp_str)

            card_class = ""
            if deadline_status['class'] == "deadline-ontrack" or deadline_status['class'] == "deadline-duesoon":
                card_class = "card-prazo-dentro"
            elif deadline_status['class'] == "deadline-overdue":
                card_class = "card-prazo-fora"

            st.markdown(f"""
                    <div class="notification-card {card_class}">
                        <h4>#{notification.get('id', UI_TEXTS.text_na)} - {notification.get('title', UI_TEXTS.text_na)}</h4>
                        <p><strong>Status Atual:</strong> <span class="{status_class}">{notification.get('status', UI_TEXTS.text_na).replace('_', ' ').title()}</span></p>
                        <p><strong>Local do Evento:</strong> {notification.get('location', UI_TEXTS.text_na)} | <strong>Prioridade:</strong> {prioridade_display} <strong class='{deadline_status['class']}'>Prazo: {deadline_status['text']}</strong></p>
                    </div>
                    """, unsafe_allow_html=True)

            with st.expander(
                    f"✨ Ver Detalhes Completos e Classificação - Notificação #{notification.get('id', UI_TEXTS.text_na)}"):
                display_notification_full_details(notification, user_id_logged_in, user_username_logged_in)

            if notification.get('actions'):
                st.markdown("#### ⚡ Histórico de Ações Realizadas")
                with st.expander(
                        f"Ver histórico de ações para Notificação #{notification.get('id', UI_TEXTS.text_na)}"):
                    sorted_actions = sorted(notification['actions'], key=lambda x: x.get('timestamp', ''))
                    for action in sorted_actions:
                        action_type = "🏁 CONCLUSÃO (Executor)" if action.get('final_action_by_executor') else "   AÇÃO Registrada"
                        action_timestamp = action.get('timestamp', UI_TEXTS.text_na)
                        if action_timestamp != UI_TEXTS.text_na:
                            try:
                                action_timestamp = datetime.fromisoformat(action_timestamp).strftime(
                                    '%d/%m/%Y %H:%M:%S')
                            except ValueError:
                                pass

                        if user_id_logged_in and action.get('executor_id') == user_id_logged_in:
                            st.markdown(f"""
                            <div class='my-action-entry-card'>
                                <strong>{action_type}</strong> - por <strong>VOCÊ ({action.get('executor_name', UI_TEXTS.text_na)})</strong> em {action_timestamp}
                                <br>
                                <em>{action.get('description', UI_TEXTS.text_na)}</em>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class='action-entry-card'>
                                <strong>{action_type}</strong> - por <strong>{action.get('executor_name', UI_TEXTS.text_na)}</strong> em {action_timestamp}
                                <br>
                                <em>{action.get('description', UI_TEXTS.text_na)}</em>
                            </div>
                            """, unsafe_allow_html=True)

                        if action.get('final_action_by_executor'):
                            evidence_desc = action.get('evidence_description', '').strip()
                            evidence_atts = action.get('evidence_attachments', [])
                            if evidence_desc or evidence_atts:
                                st.markdown(f"""<div class='evidence-section'>""", unsafe_allow_html=True)
                                st.markdown("<h6>Evidências da Conclusão:</h6>", unsafe_allow_html=True)
                                if evidence_desc:
                                    st.info(evidence_desc)
                                if evidence_atts:
                                    for attach_info in evidence_atts:
                                        unique_name = attach_info.get('unique_name')
                                        original_name = attach_info.get('original_name')
                                        if unique_name and original_name:
                                            file_content = get_attachment_data(unique_name)
                                            if file_content:
                                                st.download_button(
                                                    label=f"Baixar Evidência: {original_name}",
                                                    data=file_content,
                                                    file_name=original_name,
                                                    mime="application/octet-stream",
                                                    key=f"download_action_evidence_exec_{notification['id']}_{unique_name}"
                                                )
                                            else:
                                                st.write(
                                                    f"Anexo: {original_name} (arquivo não encontrado ou corrompido)")
                        st.markdown("---\n")

            executor_has_already_concluded_their_part = False
            if user_id_logged_in:
                notif_actions = get_notification_actions(notification.get('id'))
                for action_entry in notif_actions:
                    if action_entry.get('executor_id') == user_id_logged_in and action_entry.get('final_action_by_executor') == True:
                        executor_has_already_concluded_their_part = True
                        break

            action_choice_key = f"exec_action_choice_{notification.get('id', UI_TEXTS.text_na)}_refactored"

            if action_choice_key not in st.session_state:
                st.session_state[action_choice_key] = UI_TEXTS.selectbox_default_acao_realizar

            if executor_has_already_concluded_their_part:
                st.info(
                    f"✅ Sua parte na execução da Notificação #{notification.get('id')} já foi concluída. Você não pode adicionar mais ações para esta notificação.")
            else:
                st.markdown("### 📝 Registrar Ação Executada ou Concluir Sua Parte")
                action_type_choice_options = [UI_TEXTS.selectbox_default_acao_realizar, "Registrar Ação",
                                              "Concluir Minha Parte"]

                st.selectbox(
                    "Qual ação deseja realizar?*", options=action_type_choice_options,
                    key=action_choice_key,
                    index=action_type_choice_options.index(st.session_state[action_choice_key]),
                    help="Selecione 'Registrar Ação' para adicionar um passo ao histórico ou 'Concluir Minha Parte' para finalizar sua execução."
                )

                with st.form(f"action_form_{notification.get('id', UI_TEXTS.text_na)}_refactored",
                             clear_on_submit=False):
                    st.markdown("<span class='required-field'>* Campo obrigatório</span>", unsafe_allow_html=True)

                    action_description_state = st.text_area(
                        "Descrição detalhada da ação realizada*",
                        value=st.session_state.get(
                            f"exec_action_desc_{notification.get('id', UI_TEXTS.text_na)}_refactored", ""),
                        placeholder="Descreva:\n• O QUÊ foi feito?\n• POR QUÊ foi feito (qual o objetivo)?\n• ONDE foi realizado?\n• QUANDO foi realizado (data/hora)?\n• QUEM executou (se aplicável)?\n• COMO foi executado (passos, métodos)?\n• QUANTO CUSTOU (recursos, tempo)?\n• QUÃO FREQUENTE (se for uma ação contínua)?",
                        height=180,
                        key=f"exec_action_desc_{notification.get('id', UI_TEXTS.text_na)}_refactored",
                        help="Forneça um relato completo e estruturado da ação executada ou da conclusão da sua parte, utilizando os pontos do 5W3H como guia."
                    ).strip()

                    evidence_description_state = ""
                    uploaded_evidence_files = []

                    if st.session_state[action_choice_key] == "Concluir Minha Parte":
                        st.markdown("""
                           <div class="conditional-field">
                               <h4>✅ Evidências da Tratativa</h4>
                               <p>Descreva e anexe as evidências da tratativa realizada para esta notificação.</p>
                           </div>
                           """, unsafe_allow_html=True)
                        evidence_description_state = st.text_area(
                            "Descrição da Evidência (Opcional)",
                            value=st.session_state.get(
                                f"exec_evidence_desc_{notification.get('id', UI_TEXTS.text_na)}_refactored", ""),
                            placeholder="Descreva o resultado da tratativa, evidências de conclusão, etc.",
                            height=100,
                            key=f"exec_evidence_desc_{notification.get('id', UI_TEXTS.text_na)}_refactored"
                        ).strip()

                        uploaded_evidence_files = st.file_uploader(
                            "Anexar arquivos de Evidência (Opcional)", type=None, accept_multiple_files=True,
                            key=f"exec_evidence_attachments_{notification.get('id', UI_TEXTS.text_na)}_refactored"
                        )

                    submit_button = st.form_submit_button("✔️ Confirmar Ação",
                                                          use_container_width=True)
                    st.markdown("---\n")

                    if submit_button:
                        validation_errors = []
                        if st.session_state[action_choice_key] == UI_TEXTS.selectbox_default_acao_realizar:
                            validation_errors.append("É obrigatório selecionar o tipo de ação (Registrar ou Concluir).")
                        if not action_description_state:
                            validation_errors.append("A descrição detalhada da ação é obrigatória.")

                        if validation_errors:
                            st.error("⚠️ **Por favor, corrija os seguintes erros:**")
                            for error in validation_errors: st.warning(error)
                        else:
                            current_notification_in_list = next(
                                (n for n in load_notifications() if n.get('id') == notification.get('id')), None)
                            if not current_notification_in_list:
                                st.error("Erro interno: Notificação não encontrada na lista principal para atualização.")
                            else:
                                recheck_executor_already_concluded = False
                                notif_actions_db = get_notification_actions(notification.get('id'))
                                for existing_action_recheck in notif_actions_db:
                                    if existing_action_recheck.get('executor_id') == user_id_logged_in and existing_action_recheck.get('final_action_by_executor') == True:
                                        recheck_executor_already_concluded = True
                                        break

                                if recheck_executor_already_concluded:
                                    st.error("❌ Sua parte nesta notificação já foi marcada como concluída anteriormente. Operação abortada.")
                                    st.session_state[action_choice_key] = UI_TEXTS.selectbox_default_acao_realizar
                                    _clear_execution_form_state(notification['id'])
                                    st.rerun()
                                else:
                                    saved_evidence_attachments = []
                                    if st.session_state[action_choice_key] == "Concluir Minha Parte" and uploaded_evidence_files:
                                        for file in uploaded_evidence_files:
                                            saved_file_info = save_uploaded_file_to_disk(file, notification.get('id'))
                                            if saved_file_info:
                                                saved_evidence_attachments.append(saved_file_info)

                                    action_data_to_add = {
                                        'executor_id': user_id_logged_in,
                                        'executor_name': user_username_logged_in,
                                        'description': action_description_state,
                                        'timestamp': datetime.now().isoformat(),
                                        'final_action_by_executor': st.session_state[action_choice_key] == "Concluir Minha Parte",
                                        'evidence_description': evidence_description_state if st.session_state[
                                            action_choice_key] == "Concluir Minha Parte" else None,
                                        'evidence_attachments': saved_evidence_attachments if st.session_state[
                                            action_choice_key] == "Concluir Minha Parte" else None
                                    }

                                    add_notification_action(notification['id'], action_data_to_add)

                                    if st.session_state[action_choice_key] == "Registrar Ação":
                                        if current_notification_in_list.get('status') == 'classificada':
                                            update_notification(notification['id'], {'status': 'em_execucao'})
                                        add_history_entry(notification['id'],
                                                          "Ação registrada (Execução)",
                                                          user_username_logged_in,
                                                          f"Registrou ação: {action_description_state[:100]}..." if len(
                                                              action_description_state) > 100 else f"Registrou ação: {action_description_state}")
                                        st.toast("✅ Ação registrada com sucesso!", icon="  ")
                                    elif st.session_state[action_choice_key] == "Concluir Minha Parte":
                                        all_actions_for_notif = get_notification_actions(notification['id'])
                                        all_assigned_executors_ids = set(
                                            current_notification_in_list.get('executors', []))
                                        executors_who_concluded_ids = set(
                                            a.get('executor_id') for a in all_actions_for_notif if
                                            a.get('final_action_by_executor'))

                                        all_executors_concluded = all_assigned_executors_ids.issubset(
                                            executors_who_concluded_ids) and len(all_assigned_executors_ids) > 0

                                        updates_to_status = {}
                                        if all_executors_concluded:
                                            updates_to_status['status'] = 'revisao_classificador_execucao'
                                            st.toast(
                                                "✅ Todos os executores concluíram suas partes. Notificação encaminhada para revisão!",
                                                icon="🏁")
                                        else:
                                            st.toast("✅ Sua execução foi concluída nesta notificação!", icon="✅")
                                        history_details = f"Executor {user_username_logged_in} concluiu sua parte das ações."
                                        add_history_entry(
                                            notification['id'],
                                            "Execução concluída (por executor)",
                                            user_username_logged_in,
                                            history_details
                                        )

                                        if updates_to_status:
                                            update_notification(notification['id'], updates_to_status)

                                        st.success(
                                            f"✅ Sua execução foi concluída nesta notificação! Status atual: '{current_notification_in_list['status'].replace('_', ' ').title()}'.")
                                        if not all_executors_concluded:
                                            users_list_exec = load_users()
                                            remaining_executors_ids = list(
                                                all_assigned_executors_ids - executors_who_concluded_ids)
                                            remaining_executors_names = [u.get('name', UI_TEXTS.text_na) for u in
                                                                         users_list_exec if
                                                                         u.get('id') in remaining_executors_ids]
                                            st.info(
                                                f"Aguardando conclusão dos seguintes executores: {', '.join(remaining_executors_names) or 'Nenhum'}.")
                                        elif all_executors_concluded:
                                            st.info(
                                                f"Todos os executores concluíram suas partes. A notificação foi enviada para revisão final pelo classificador.\n\nEvidência da tratativa:\n{evidence_description_state}\n\nAnexos: {len(saved_evidence_attachments) if saved_evidence_attachments else 0}")
                                    _clear_execution_form_state(notification['id'])
                                    st.rerun()

            with st.expander("👥 Adicionar Executor Adicional"):
                with st.form(f"add_executor_form_{notification.get('id', UI_TEXTS.text_na)}_refactored",
                             clear_on_submit=True):
                    executors = load_users() # Re-carrega usuários para garantir lista mais atualizada
                    # Filtra apenas executores e usuários ativos
                    executors_filtered_by_role = [e for e in executors if 'executor' in e.get('roles', []) and e.get('active', True)]
                    
                    current_executors_ids = notification.get('executors', [])
                    available_executors = [e for e in executors_filtered_by_role if e.get('id') not in current_executors_ids]
                    if available_executors:
                        executor_options = {
                            f"{e.get('name', UI_TEXTS.text_na)} ({e.get('username', UI_TEXTS.text_na)})": e['id']
                            for e in available_executors
                        }

                        add_executor_display_options = [UI_TEXTS.multiselect_instruction_placeholder] + list(executor_options.keys())
                        default_add_executor_selection = [UI_TEXTS.multiselect_instruction_placeholder]

                        new_executor_name_to_add_raw = st.selectbox(
                            "Selecionar executor para adicionar:*",
                            options=add_executor_display_options,
                            index=add_executor_display_options.index(default_add_executor_selection[0]),
                            key=f"add_executor_select_exec_{notification.get('id', UI_TEXTS.text_na)}_form_refactored",
                            help="Selecione o usuário executor que será adicionado a esta notificação."
                        )
                        new_executor_name_to_add = (
                            new_executor_name_to_add_raw
                            if new_executor_name_to_add_raw != UI_TEXTS.multiselect_instruction_placeholder
                            else None
                        )

                        st.markdown("<span class='required-field'>* Campo obrigatório</span>",
                                    unsafe_allow_html=True)

                        submit_button = st.form_submit_button("➕ Adicionar Executor",
                                                              use_container_width=True)
                        if submit_button:
                            if new_executor_name_to_add:
                                new_executor_id = executor_options[new_executor_name_to_add]
                                current_notification_in_list = next(
                                    (n for n in load_notifications() if n.get('id') == notification.get('id')), None)
                                if current_notification_in_list:
                                    updated_executors = current_notification_in_list.get('executors', []) + [
                                        new_executor_id]

                                    update_notification(notification.get('id'), {'executors': updated_executors})

                                    add_history_entry(
                                        notification.get('id'), "Executor adicionado (durante execução)",
                                        user_username_logged_in,
                                        f"Adicionado o executor: {new_executor_name_to_add}"
                                    )

                                    st.success(
                                        f"✅ {new_executor_name_to_add} adicionado como executor para esta notificação.")
                                    st.rerun()
                                else:
                                    st.error("Erro: Notificação não encontrada para adicionar executor.")
                            else:
                                st.error("⚠️ Por favor, selecione um executor para adicionar.")
                    else:
                        st.info("Não há executores adicionais disponíveis para atribuição no momento.")
    with tab_closed_my_exec_notifs:
        st.markdown("### Minhas Ações Encerradas")

        if not closed_my_exec_notifications:
            st.info("✅ Não há notificações encerradas em que você estava envolvido como executor no momento.")
        else:
            st.info(
                f"Total de notificações encerradas em que você estava envolvido: {len(closed_my_exec_notifications)}.")

            search_query_exec_closed = st.text_input(
                "   Buscar em Minhas Ações Encerradas (Título, Descrição, ID):",
                key="closed_exec_notif_search_input",
                placeholder="Ex: 'reparo', '987', 'instalação'"
            ).lower()

            filtered_closed_my_exec_notifications = []
            if search_query_exec_closed:
                for notif in closed_my_exec_notifications:
                    if search_query_exec_closed.isdigit() and int(search_query_exec_closed) == notif.get('id'):
                        filtered_closed_my_exec_notifications.append(notif)
                    elif (search_query_exec_closed in notif.get('title', '').lower() or
                          search_query_exec_closed in notif.get('description', '').lower()):
                        filtered_closed_my_exec_notifications.append(notif)
            else:
                filtered_closed_my_exec_notifications = closed_my_exec_notifications

            if not filtered_closed_my_exec_notifications:
                st.warning(
                    "⚠️ Nenhuma notificação encontrada com os critérios de busca especificados em suas ações encerradas.")
            else:
                filtered_closed_my_exec_notifications.sort(key=lambda x: x.get('created_at', ''), reverse=True)

                st.markdown(f"**Notificações Encontradas ({len(filtered_closed_my_exec_notifications)})**:")
                for notification in filtered_closed_my_exec_notifications:
                    status_class = f"status-{notification.get('status', UI_TEXTS.text_na).replace('_', '-')}"
                    created_at_str = notification.get('created_at', UI_TEXTS.text_na)
                    if created_at_str != UI_TEXTS.text_na:
                        try:
                            created_at_str = datetime.fromisoformat(created_at_str).strftime('%d/%m/%Y %H:%M:%S')
                        except ValueError:
                            pass

                    concluded_by = UI_TEXTS.text_na
                    if notification.get('conclusion') and notification['conclusion'].get('concluded_by'):
                        concluded_by = notification['conclusion']['concluded_by']
                    elif notification.get('approval') and (notification.get('approval') or {}).get('approved_by'):
                        concluded_by = (notification.get('approval') or {}).get('approved_by')
                    elif notification.get('rejection_classification') and (
                            notification.get('rejection_classification') or {}).get('classified_by'):
                        concluded_by = (notification.get('rejection_classification') or {}).get('classified_by')
                    elif notification.get('rejection_approval') and (notification.get('rejection_approval') or {}).get('rejected_by'):
                        concluded_by = (notification.get('rejection_approval') or {}).get('rejected_by')

                    deadline_info = notification.get('classification', {}).get('deadline_date')
                    concluded_timestamp_str = (notification.get('conclusion') or {}).get('timestamp')

                    deadline_status = get_deadline_status(deadline_info, concluded_timestamp_str)
                    card_class = ""
                    if deadline_status['class'] == "deadline-ontrack" or deadline_status['class'] == "deadline-duesoon":
                        card_class = "card-prazo-dentro"
                    elif deadline_status['class'] == "deadline-overdue":
                        card_class = "card-prazo-fora"

                    st.markdown(f"""
                            <div class="notification-card {card_class}">
                                <h4>#{notification.get('id', UI_TEXTS.text_na)} - {notification.get('title', UI_TEXTS.text_na)}</h4>
                                <p><strong>Status Final:</strong> <span class="{status_class}">{notification.get('status', UI_TEXTS.text_na).replace('_', ' ').title()}</span></p>
                                <p><strong>Encerrada por:</strong> {concluded_by} | <strong>Data de Criação:</strong> {created_at_str}</p>
                                <p><strong>Prazo:</strong> {deadline_status['text']}</p>
                            </div>
                            """, unsafe_allow_html=True)

                    with st.expander(
                            f"  ️ Visualizar Detalhes - Notificação #{notification.get('id', UI_TEXTS.text_na)}"):
                        display_notification_full_details(notification, user_id_logged_in, user_username_logged_in)