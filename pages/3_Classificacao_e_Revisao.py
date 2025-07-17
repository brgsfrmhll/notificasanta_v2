# pages/3_Classificacao_e_Revisao.py

import streamlit as st
from datetime import datetime, date as dt_date_class, time as dt_time_class
import time as time_module

# Importa funções e constantes do arquivo principal e de utilidades
from streamlit_app import check_permission, load_notifications, load_users, update_notification, add_history_entry, get_notification_actions
from constants import UI_TEXTS, FORM_DATA, DEADLINE_DAYS_MAPPING
from utils import get_deadline_status, format_date_time_summary, get_attachment_data


def run():
    """
    Renders the page for classifiers to perform initial classification of new notifications
    and review the execution of completed actions by responsible parties.
    """
    if not check_permission('classificador'):
        st.error("❌ Acesso negado! Você não tem permissão para classificar notificações.")
        return

    st.markdown("<h1 class='main-header'>🔍 Classificação e Revisão de Notificações</h1>", unsafe_allow_html=True)
    st.info("📋 Nesta área, você pode realizar a classificação inicial de novas notificações e revisar a execução das ações concluídas pelos responsáveis.")

    all_notifications = load_notifications()
    pending_initial_classification = [n for n in all_notifications if n.get('status') == "pendente_classificacao"]
    pending_execution_review = [n for n in all_notifications if n.get('status') == "revisao_classificador_execucao"]
    closed_statuses = ['aprovada', 'rejeitada', 'reprovada', 'concluida']
    closed_notifications = [n for n in all_notifications if n.get('status') in closed_statuses]

    if not pending_initial_classification and not pending_execution_review and not closed_notifications:
        st.info("✅ Não há notificações pendentes de classificação inicial, revisão de execução ou encerradas no momento.")
        return

    tab_initial_classif, tab_review_exec, tab_closed_notifs = st.tabs(
        [f"⏳ Pendentes Classificação Inicial ({len(pending_initial_classification)})",
         f"🛠️ Revisão de Execução Concluída ({len(pending_execution_review)})",
         f"✅ Notificações Encerradas ({len(closed_notifications)})"]
    )

    with tab_initial_classif:
        st.markdown("### Notificações Aguardando Classificação Inicial")

        if not pending_initial_classification:
            st.info("✅ Não há notificações aguardando classificação inicial no momento.")
        else:
            st.markdown("#### 📋 Selecionar Notificação para Classificação Inicial")
            notification_options_initial = [UI_TEXTS.selectbox_default_notification_select] + [
                f"#{n['id']} | Criada em: {n.get('created_at', UI_TEXTS.text_na)[:10]} | {n.get('title', 'Sem título')[:60]}..."
                for n in pending_initial_classification
            ]

            pending_initial_ids_str = ",".join(str(n['id']) for n in pending_initial_classification)
            selectbox_key_initial = f"classify_selectbox_initial_{pending_initial_ids_str}"

            if selectbox_key_initial not in st.session_state or st.session_state[
                selectbox_key_initial] not in notification_options_initial:
                previous_selection = st.session_state.get(selectbox_key_initial, notification_options_initial[0])
                if previous_selection in notification_options_initial:
                    st.session_state[selectbox_key_initial] = previous_selection
                else:
                    st.session_state[selectbox_key_initial] = notification_options_initial[0]

            selected_option_initial = st.selectbox(
                "Escolha uma notificação para analisar e classificar inicial:",
                options=notification_options_initial,
                index=notification_options_initial.index(st.session_state[selectbox_key_initial]),
                key=selectbox_key_initial,
                help="Selecione na lista a notificação pendente que você deseja classificar.")

            notification_id_initial = None
            notification_initial = None

            if selected_option_initial != UI_TEXTS.selectbox_default_notification_select:
                try:
                    parts = selected_option_initial.split('#')
                    if len(parts) > 1:
                        id_part = parts[1].split(' |')[0]
                        notification_id_initial = int(id_part)
                        notification_initial = next(
                            (n for n in all_notifications if n.get('id') == notification_id_initial), None)
                except (IndexError, ValueError):
                    st.error("Erro ao processar a seleção da notificação para classificação inicial.")
                    notification_initial = None

            if notification_id_initial and (
                    st.session_state.get('current_initial_classification_id') != notification_id_initial):
                st.session_state.initial_classification_state = st.session_state.get('initial_classification_state', {})
                st.session_state.initial_classification_state[notification_id_initial] = {
                    'step': 1,
                    'data': {
                        'procede': UI_TEXTS.selectbox_default_procede_classification,
                        'motivo_rejeicao': '',
                        'classificacao_nnc': UI_TEXTS.selectbox_default_classificacao_nnc,
                        'nivel_dano': UI_TEXTS.selectbox_default_nivel_dano,
                        'prioridade_selecionada': UI_TEXTS.selectbox_default_prioridade_resolucao,
                        'never_event_selecionado': UI_TEXTS.text_na,
                        'evento_sentinela_sim_nao': UI_TEXTS.selectbox_default_evento_sentinela,
                        'tipo_evento_principal_selecionado': UI_TEXTS.selectbox_default_tipo_principal,
                        'tipo_evento_sub_selecionado': [],
                        'tipo_evento_sub_texto_livre': '',
                        'classificacao_oms_selecionada': [],
                        'observacoes_classificacao': '',
                        'requires_approval': UI_TEXTS.selectbox_default_requires_approval,
                        'approver_selecionado': UI_TEXTS.selectbox_default_approver,
                        'executores_selecionados': [],
                        'temp_notified_department': notification_initial.get(
                            'notified_department') if notification_initial else None,
                        'temp_notified_department_complement': notification_initial.get(
                            'notified_department_complement') if notification_initial else None,
                    }
                }
                st.session_state.current_initial_classification_id = notification_id_initial
                if 'current_review_classification_id' in st.session_state: st.session_state.pop(
                    'current_review_classification_id')

                st.rerun()

            current_classification_state = st.session_state.initial_classification_state.get(notification_id_initial,
                                                                                             {})
            current_step = current_classification_state.get('step', 1)
            current_data = current_classification_state.get('data', {})

            if notification_initial:
                st.markdown(
                    f"### Notificação Selecionada para Classificação Inicial: #{notification_initial.get('id', UI_TEXTS.text_na)}")

                with st.expander(
                        f"📄 Detalhes Reportados Originalmente (Notificação #{notification_initial.get('id', UI_TEXTS.text_na)})",
                        expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**📝 Informações Básicas**")
                        st.write(f"**Título:** {notification_initial.get('title', UI_TEXTS.text_na)}")
                        st.write(f"**Local:** {notification_initial.get('location', UI_TEXTS.text_na)}")
                        occurrence_datetime_summary = format_date_time_summary(
                            notification_initial.get('occurrence_date'), notification_initial.get('occurrence_time'))
                        st.write(f"**Data/Hora:** {occurrence_datetime_summary}")
                        st.write(f"**Turno:** {notification_initial.get('event_shift', UI_TEXTS.text_na)}")
                        reporting_department = notification_initial.get('reporting_department', UI_TEXTS.text_na)
                        reporting_complement = notification_initial.get('reporting_department_complement')
                        reporting_dept_display = f"{reporting_department}{f' ({reporting_complement})' if reporting_complement else ''}"
                        st.write(f"**Setor Notificante:** {reporting_dept_display}")

                        notified_department = notification_initial.get('notified_department', UI_TEXTS.text_na)
                        notified_complement = notification_initial.get('notified_department_complement')
                        notified_dept_display = f"{notified_department}{f' ({notified_complement})' if notified_complement else ''}"
                        st.write(f"**Setor Notificado:** {notified_dept_display}")

                        if notification_initial.get('immediate_actions_taken') and notification_initial.get('immediate_action_description'):
                            st.write(
                                f"**Ações Imediatas Reportadas:** {notification_initial.get('immediate_action_description', UI_TEXTS.text_na)[:100]}...")
                    with col2:
                        st.markdown("**📊 Detalhes de Paciente e Observações Iniciais**")
                        st.write(
                            f"**Paciente Envolvido:** {'Sim' if notification_initial.get('patient_involved') else 'Não'}")
                        if notification_initial.get('patient_involved'):
                            st.write(f"**Prontuário:** {notification_initial.get('patient_id', UI_TEXTS.text_na)}")
                            outcome = notification_initial.get('patient_outcome_obito')
                            if outcome is True:
                                st.write("**Evoluiu para Óbito:** Sim")
                            elif outcome is False:
                                st.write("**Evoluiu para Óbito:** Não")
                            else:
                                st.write("**Evoluiu para Óbito:** Não informado")
                    st.markdown("**📝 Descrição Detalhada do Evento**")
                    st.info(notification_initial.get('description', UI_TEXTS.text_na))
                    if notification_initial.get('additional_notes'):
                        st.markdown("**ℹ️ Observações Adicionais do Notificante**")
                        st.info(notification_initial.get('additional_notes', UI_TEXTS.text_na))
                    if notification_initial.get('attachments'):
                        st.markdown("**📎 Anexos**")
                        for attach_info in notification_initial['attachments']:
                            unique_name_to_use = None
                            original_name_to_use = None
                            if isinstance(attach_info,
                                          dict) and 'unique_name' in attach_info and 'original_name' in attach_info:
                                unique_name_to_use = attach_info['unique_name']
                                original_name_to_use = attach_info['original_name']
                            elif isinstance(attach_info, str):
                                unique_name_to_use = attach_info
                                original_name_to_use = attach_info

                            if unique_name_to_use:
                                file_content = get_attachment_data(unique_name_to_use)
                                if file_content:
                                    st.download_button(
                                        label=f"Baixar {original_name_to_use}",
                                        data=file_content,
                                        file_name=original_name_to_use,
                                        mime="application/octet-stream",
                                        key=f"download_init_{notification_initial['id']}_{unique_name_to_use}"
                                    )
                                else:
                                    st.write(f"Anexo: {original_name_to_use} (arquivo não encontrado ou corrompido)")
                st.markdown("---")

                if current_step == 1:
                    with st.container():
                        st.markdown("""
                             <div class="form-section">
                                 <h3>📋 Etapa 1: Aceite da Notificação</h3>
                                 <p>Analise os detalhes da notificação e decida se ela procede para classificação.</p>
                             </div>
                             """, unsafe_allow_html=True)
                        procede_options = [UI_TEXTS.selectbox_default_procede_classification, "Sim", "Não"]
                        current_data['procede'] = st.selectbox(
                            "Após análise, a notificação procede e deve ser classificada?*",
                            options=procede_options,
                            index=procede_options.index(
                                current_data.get('procede', UI_TEXTS.selectbox_default_procede_classification)),
                            key=f"procede_select_{notification_id_initial}_step1_initial_refactored",
                            help="Selecione 'Sim' para classificar a notificação ou 'Não' para rejeitá-la.")
                        st.markdown("<span class='required-field'>* Campo obrigatório</span>", unsafe_allow_html=True)
                        if current_data['procede'] == "Não":
                            current_data['motivo_rejeicao'] = st.text_area(
                                "Justificativa para Rejeição*", value=current_data.get('motivo_rejeicao', ''),
                                key=f"motivo_rejeicao_{notification_id_initial}_step1_initial_refactored",
                                help="Explique detalhadamente por que esta notificação será rejeitada.").strip()
                        else:
                            current_data['motivo_rejeicao'] = ""

                elif current_step == 2:
                    with st.container():
                        st.markdown("""
                             <div class="form-section">
                                 <h3>📘 Etapa 2: Classificação NNC, Dano e Prioridade</h3>
                                 <p>Forneça a classificação de Não Conformidade, o nível de dano (se aplicável) e defina a prioridade.</p>
                             </div>
                             """, unsafe_allow_html=True)
                        classificacao_nnc_options = [
                                                        UI_TEXTS.selectbox_default_classificacao_nnc] + FORM_DATA.classificacao_nnc
                        current_data['classificacao_nnc'] = st.selectbox(
                            "Classificação:*", options=classificacao_nnc_options,
                            index=classificacao_nnc_options.index(
                                current_data.get('classificacao_nnc', UI_TEXTS.selectbox_default_classificacao_nnc)),
                            key=f"class_nnc_{notification_id_initial}_step2_initial_refactored",
                            help="Selecione o tipo de classificação principal do evento.")
                        st.markdown("<span class='required-field'>* Campo obrigatório</span>", unsafe_allow_html=True)
                        if current_data['classificacao_nnc'] == "Evento com dano":
                            nivel_dano_options = [UI_TEXTS.selectbox_default_nivel_dano] + FORM_DATA.niveis_dano
                            current_data['nivel_dano'] = st.selectbox(
                                "Nível de Dano ao Paciente:*", options=nivel_dano_options,
                                index=nivel_dano_options.index(
                                    current_data.get('nivel_dano', UI_TEXTS.selectbox_default_nivel_dano)),
                                key=f"dano_nivel_{notification_id_initial}_step2_initial_refactored",
                                help="Selecione o nível de dano ao paciente.")
                            st.markdown(
                                "<span class='required-field'>* Campo obrigatório quando Evento com Dano</span>",
                                unsafe_allow_html=True)
                        else:
                            current_data['nivel_dano'] = UI_TEXTS.selectbox_default_nivel_dano

                        prioridades_options = [UI_TEXTS.selectbox_default_prioridade_resolucao] + FORM_DATA.prioridades
                        current_data['prioridade_selecionada'] = st.selectbox(
                            "Prioridade de Resolução:*", options=prioridades_options,
                            index=prioridades_options.index(
                                current_data.get('prioridade_selecionada',
                                                 UI_TEXTS.selectbox_default_prioridade_resolucao)),
                            key=f"prioridade_select_{notification_id_initial}_step2_initial_refactored",
                            help="Defina a prioridade para investigação e resolução do evento.")
                        st.markdown("<span class='required-field'>* Campo obrigatório</span>", unsafe_allow_html=True)
                elif current_step == 3:
                    with st.container():
                        st.markdown("""
                             <div class="form-section">
                                 <h3>⚠️ Etapa 3: Eventos Especiais (Never Event / Sentinela)</h3>
                                 <p>Identifique se o evento se enquadra em categorias de alta relevância para a segurança do paciente.</p>
                             </div>
                             """, unsafe_allow_html=True)

                        never_event_options = [UI_TEXTS.selectbox_default_never_event] + FORM_DATA.never_events + [UI_TEXTS.text_na]

                        selected_never_event_for_index = current_data.get('never_event_selecionado', UI_TEXTS.text_na)

                        try:
                            default_index = never_event_options.index(selected_never_event_for_index)
                        except ValueError:
                            default_index = 0

                        current_data['never_event_selecionado'] = st.selectbox(
                            "Never Event:*",
                            options=never_event_options,
                            index=default_index,
                            format_func=lambda x: UI_TEXTS.selectbox_never_event_na_text if x == UI_TEXTS.text_na else x,
                            key=f"never_event_select_{notification_id_initial}_step3_initial_refactored",
                            help="Selecione se o evento se enquadra como um Never Event. Utilize 'Selecione uma opção...' caso não se aplique ou não haja um Never Event identificado."
                        )
                        st.markdown("<span class='required-field'>* Campo obrigatório</span>", unsafe_allow_html=True)
                        evento_sentinela_options = [UI_TEXTS.selectbox_default_evento_sentinela, "Sim", "Não"]
                        current_data['evento_sentinela_sim_nao'] = st.selectbox(
                            "Evento Sentinela?*", options=evento_sentinela_options,
                            index=evento_sentinela_options.index(
                                current_data.get('evento_sentinela_sim_nao',
                                                 UI_TEXTS.selectbox_default_evento_sentinela)),
                            key=f"is_sentinel_event_select_{notification_id_initial}_step3_initial_refactored",
                            help="Indique se o evento é considerado um Evento Sentinela.")
                        st.markdown("<span class='required-field'>* Campo obrigatório</span>", unsafe_allow_html=True)
                elif current_step == 4:
                    with st.container():
                        st.markdown("""
                             <div class="form-section">
                                 <h3> categorização do evento (Tipo Principal e Especificação)</h3>
                                 <p>Classifique o evento pelo tipo principal e especifique, se necessário.</p>
                             </div>
                             """, unsafe_allow_html=True)
                        tipo_evento_principal_options = [UI_TEXTS.selectbox_default_tipo_principal] + list(
                            FORM_DATA.tipos_evento_principal.keys())
                        current_data['tipo_evento_principal_selecionado'] = st.selectbox(
                            "Tipo Principal:*", options=tipo_evento_principal_options,
                            index=tipo_evento_principal_options.index(
                                current_data.get('tipo_evento_principal_selecionado',
                                                 UI_TEXTS.selectbox_default_tipo_principal)),
                            key="event_type_main_refactored", help="Classificação do tipo principal de evento.")
                        st.markdown("<span class='required-field'>* Campo obrigatório</span>", unsafe_allow_html=True)
                        sub_options = FORM_DATA.tipos_evento_principal.get(
                            current_data.get('tipo_evento_principal_selecionado'), [])

                        if current_data.get('tipo_evento_principal_selecionado') in ["Clínico", "Não-clínico", "Ocupacional"] and sub_options:
                            multiselect_display_options = [UI_TEXTS.multiselect_instruction_placeholder] + sub_options
                            default_sub_selection = current_data.get('tipo_evento_sub_selecionado', [])

                            if not default_sub_selection or not any(
                                    item in sub_options for item in default_sub_selection):
                                default_sub_selection = [UI_TEXTS.multiselect_instruction_placeholder]

                            selected_sub_raw = st.multiselect(
                                f"{UI_TEXTS.multiselect_event_spec_label_prefix}{current_data['tipo_evento_principal_selecionado']}{UI_TEXTS.multiselect_event_spec_label_suffix}",
                                options=multiselect_display_options,
                                default=default_sub_selection,
                                key=f"event_type_sub_select_{notification_id_initial}_step4_initial_refactored",
                                help="Selecione as sub-categorias aplicáveis.")

                            current_data['tipo_evento_sub_selecionado'] = [
                                opt for opt in selected_sub_raw if
                                opt != UI_TEXTS.multiselect_instruction_placeholder
                            ]
                            current_data['tipo_evento_sub_texto_livre'] = ""
                        elif current_data.get('tipo_evento_principal_selecionado') in ["Queixa técnica", "Outros"]:
                            label_text = f"Especifique o tipo '{current_data['tipo_evento_principal_selecionado']}'*" if \
                                current_data['tipo_evento_principal_selecionado'] == "Outros" else f"Especifique o tipo '{current_data['tipo_evento_principal_selecionado']}':"
                            current_data['tipo_evento_sub_texto_livre'] = st.text_input(
                                label_text, value=current_data.get('tipo_evento_sub_texto_livre', ''),
                                key=f"event_type_sub_text_{notification_id_initial}_step4_initial_refactored",
                                help="Descreva o tipo de evento 'Queixa Técnica' ou 'Outro'.")
                            current_data['tipo_evento_sub_selecionado'] = []
                            if current_data.get('tipo_evento_principal_selecionado') == "Outros":
                                st.markdown(
                                    "<span class='required-field'>* Campo obrigatório quando Tipo Principal é 'Outros'</span>",
                                    unsafe_allow_html=True)
                        else:
                            current_data['tipo_evento_sub_selecionado'] = []
                            current_data['tipo_evento_sub_texto_livre'] = ""

                elif current_step == 5:
                    with st.container():
                        st.markdown("""
                            <div class="form-section">
                                <h3>🌐 Etapa 5: Classificação OMS</h3>
                                <p>Classifique o evento de acordo com a Classificação Internacional de Segurança do Paciente da OMS.</p>
                            </div>
                            """, unsafe_allow_html=True)
                        oms_options = FORM_DATA.classificacao_oms
                        multiselect_display_options = [UI_TEXTS.multiselect_instruction_placeholder] + oms_options
                        default_oms_selection = current_data.get('classificacao_oms_selecionada', [])
                        if not default_oms_selection or not any(item in oms_options for item in default_oms_selection):
                            default_oms_selection = [UI_TEXTS.multiselect_instruction_placeholder]

                        selected_oms_raw = st.multiselect(
                            UI_TEXTS.multiselect_classification_oms_label,
                            options=multiselect_display_options,
                            default=default_oms_selection,
                            key=f"oms_classif_{notification_id_initial}_step5_initial_refactored",
                            help="Selecione um ou mais tipos de incidente da Classificação da OMS.")

                        current_data['classificacao_oms_selecionada'] = [
                            opt for opt in selected_oms_raw if opt != UI_TEXTS.multiselect_instruction_placeholder
                        ]
                        st.markdown("<span class='required-field'>* Campo obrigatório (selecionar ao menos um)</span>",
                                    unsafe_allow_html=True)

                elif current_step == 6:
                    with st.container():
                        st.markdown("""
                             <div class="form-section">
                                 <h3>📄 Etapa 6: Observações da Classificação</h3>
                                 <p>Adicione quaisquer observações relevantes sobre a classificação do evento.</p>
                             </div>
                             """, unsafe_allow_html=True)
                        current_data['observacoes_classificacao'] = st.text_area(
                            "Observações da Classificação (opcional)",
                            value=current_data.get('observacoes_classificacao', ''),
                            key=f"obs_classif_{notification_id_initial}_step6_initial_refactored",
                            help="Adicione observações relevantes sobre a classificação do evento.").strip()

                elif current_step == 7:
                    with st.container():
                        st.markdown("""
                             <div class="form-section">
                                 <h3>👥 Etapa 7: Atribuição e Fluxo Pós-Classificação</h3>
                                 <p>Defina quem será responsável pela execução das ações e se aprovação superior é necessária.</p>
                             </div>
                             """, unsafe_allow_html=True)

                        st.markdown("#### 📝 Resumo da Notificação Original")
                        st.write(f"**Título Original:** {notification_initial.get('title', UI_TEXTS.text_na)}")
                        st.write(f"**Local Original:** {notification_initial.get('location', UI_TEXTS.text_na)}")
                        original_occurrence_datetime_summary = format_date_time_summary(
                            notification_initial.get('occurrence_date'), notification_initial.get('occurrence_time'))
                        st.write(f"**Data/Hora Original:** {original_occurrence_datetime_summary}")
                        reporting_department = notification_initial.get('reporting_department', UI_TEXTS.text_na)
                        reporting_complement = notification_initial.get('reporting_department_complement')
                        reporting_dept_display = f"{reporting_department}{f' ({reporting_complement})' if reporting_complement else ''}"
                        st.write(f"**Setor Notificante Original:** {reporting_dept_display}")

                        original_notified_department = notification_initial.get('notified_department', UI_TEXTS.text_na)
                        original_notified_complement = notification_initial.get('notified_department_complement')
                        original_notified_dept_display = f"{original_notified_department}{f' ({original_notified_complement})' if original_notified_complement else ''}"
                        st.write(f"**Setor Notificado Original:** {original_notified_dept_display}")

                        patient_involved_display = 'Sim' if notification_initial.get('patient_involved') else 'Não'
                        if notification_initial.get('patient_involved'):
                            patient_id_display = notification_initial.get('patient_id', UI_TEXTS.text_na)
                            patient_outcome_obito_display = "Sim" if notification_initial.get('patient_outcome_obito') is True else "Não" if notification_initial.get('patient_outcome_obito') is False else UI_TEXTS.text_na
                            st.write(
                                f"**Paciente Envolvido Original:** {patient_involved_display} (ID: {patient_id_display}, Óbito: {patient_outcome_obito_display})")
                        else:
                            st.write(f"**Paciente Envolvido Original:** {patient_involved_display}")
                        st.write(
                            f"**Descrição Original:** {notification_initial.get('description', UI_TEXTS.text_na)[:200]}...")
                        st.markdown("---")

                        st.markdown("#### 🏢 Ajustar Setor Notificado")
                        st.info(
                            "Você pode ajustar o setor que receberá esta notificação e seu complemento, se necessário.")

                        initial_notified_department = current_data.get('temp_notified_department')
                        if initial_notified_department is None and notification_initial:
                            initial_notified_department = notification_initial.get('notified_department')

                        initial_notified_department_complement = current_data.get('temp_notified_department_complement')
                        if initial_notified_department_complement is None and notification_initial:
                            initial_notified_department_complement = notification_initial.get('notified_department_complement')

                        notified_dept_options_classif = [UI_TEXTS.selectbox_default_department_select] + FORM_DATA.SETORES
                        current_data['temp_notified_department'] = st.selectbox(
                            "Setor Notificado:*",
                            options=notified_dept_options_classif,
                            index=notified_dept_options_classif.index(
                                initial_notified_department) if initial_notified_department in notified_dept_options_classif else 0,
                            key=f"classifier_notified_dept_{notification_id_initial}_refactored",
                            help="Selecione o setor que será o responsável principal por receber e gerenciar esta notificação."
                        )
                        current_data['temp_notified_department_complement'] = st.text_input(
                            "Complemento do Setor Notificado",
                            value=initial_notified_department_complement,
                            placeholder="Informações adicionais (opcional)",
                            key=f"classifier_notified_dept_comp_{notification_id_initial}_refactored",
                            help="Detalhes adicionais sobre o setor notificado (Ex: Equipe A, Sala 101).")

                        st.markdown("<span class='required-field'>* Campo obrigatório</span>", unsafe_allow_html=True)
                        st.markdown("---")

                        executors = load_users() # Usar load_users() para ter a lista atualizada
                        executor_options = {
                            f"{e.get('name', UI_TEXTS.text_na)} ({e.get('username', UI_TEXTS.text_na)})": e['id']
                            for e in executors if 'executor' in e.get('roles', []) and e.get('active', True)
                        }

                        executor_display_options = [UI_TEXTS.multiselect_instruction_placeholder] + list(executor_options.keys())
                        default_executor_selection = [
                            name for name, uid in executor_options.items() if
                            uid in current_data.get('executores_selecionados', [])
                        ]

                        if not default_executor_selection or not any(
                                item in list(executor_options.keys()) for item in default_executor_selection):
                            default_executor_selection = [UI_TEXTS.multiselect_instruction_placeholder]
                        selected_executor_names_raw = st.multiselect(
                            UI_TEXTS.multiselect_assign_executors_label,
                            options=executor_display_options,
                            default=default_executor_selection,
                            key=f"executors_multiselect_{notification_id_initial}_step7_initial_refactored",
                            help="Selecione os usuários que serão responsáveis pela execução das ações corretivas/preventivas.")

                        current_data['executores_selecionados'] = [
                            opt for opt in selected_executor_names_raw if
                            opt != UI_TEXTS.multiselect_instruction_placeholder
                        ]

                        st.markdown(
                            "<span class='required-field'>* Campo obrigatório (selecionar ao menos um executor)</span>",
                            unsafe_allow_html=True)
                        st.markdown("---")

                        requires_approval_options = [UI_TEXTS.selectbox_default_requires_approval, "Sim", "Não"]
                        current_data['requires_approval'] = st.selectbox(
                            "Requer Aprovação Superior após Execução?*",
                            options=requires_approval_options,
                            index=requires_approval_options.index(
                                current_data.get('requires_approval', UI_TEXTS.selectbox_default_requires_approval)),
                            key=f"requires_approval_select_{notification_id_initial}_step7_initial_refactored",
                            help="Indique se esta notificação, após o execução das ações, precisa ser aprovada por um usuário com a função 'aprovador'.")
                        st.markdown("<span class='required-field'>* Campo obrigatório</span>", unsafe_allow_html=True)

                        approvers = load_users() # Usar load_users() para ter a lista atualizada
                        approver_options = {
                            f"{a.get('name', UI_TEXTS.text_na)} ({a.get('username', UI_TEXTS.text_na)})": a['id']
                            for a in approvers if 'aprovador' in a.get('roles', []) and a.get('active', True)
                        }
                        approver_select_options = [UI_TEXTS.selectbox_default_approver] + list(approver_options.keys())
                        if current_data['requires_approval'] == 'Sim':
                            selected_approver_name = st.selectbox(
                                "Selecionar Aprovador Responsável:*",
                                options=approver_select_options,
                                index=approver_select_options.index(next(
                                    (name for name, uid in approver_options.items() if
                                     uid == current_data.get('approver_selecionado')),
                                    UI_TEXTS.selectbox_default_approver)),
                                key=f"approver_select_{notification_id_initial}_step7_initial_refactored",
                                help="Selecione o usuário 'aprovador' que será responsável pela aprovação final.")
                            current_data['approver_selecionado'] = approver_options.get(selected_approver_name)
                            st.markdown(
                                "<span class='required-field'>* Campo obrigatório quando requer aprovação</span>",
                                unsafe_allow_html=True)
                        else:
                            current_data['approver_selecionado'] = UI_TEXTS.selectbox_default_approver

                        st.markdown("---")
                        st.markdown("#### ✅ Resumo da Classificação Final")
                        st.write(f"**Classificação NNC:** {current_data.get('classificacao_nnc', UI_TEXTS.text_na)}")
                        if current_data.get('classificacao_nnc') == "Evento com dano" and current_data.get('nivel_dano') != UI_TEXTS.selectbox_default_nivel_dano:
                            st.write(f"**Nível de Dano:** {current_data.get('nivel_dano', UI_TEXTS.text_na)}")
                        st.write(f"**Prioridade:** {current_data.get('prioridade_selecionada', UI_TEXTS.text_na)}")
                        st.write(f"**Never Event:** {current_data.get('never_event_selecionado', UI_TEXTS.text_na)}")
                        st.write(f"**Evento Sentinela:** {'Sim' if current_data.get('evento_sentinela_sim_nao') == 'Sim' else 'Não'}")
                        st.write(f"**Tipo Principal:** {current_data.get('tipo_evento_principal_selecionado', UI_TEXTS.text_na)}")
                        sub_type_display = ''
                        if current_data.get('tipo_evento_sub_selecionado'):
                            sub_type_display = ', '.join(current_data.get('tipo_evento_sub_selecionado'))
                        elif current_data.get('tipo_evento_sub_texto_livre'):
                            sub_type_display = current_data.get('tipo_evento_sub_texto_livre')
                        if sub_type_display:
                            st.write(f"**Especificação:** {sub_type_display}")
                        st.write(
                            f"**Classificação OMS:** {', '.join(current_data.get('classificacao_oms_selecionada', [UI_TEXTS.text_na]))}")
                        st.write(
                            f"**Observações:** {current_data.get('observacoes_classificacao') or UI_TEXTS.text_na}")

                        st.write(
                            f"**Setor Notificado (Ajustado):** {current_data.get('temp_notified_department', UI_TEXTS.text_na)}")
                        if current_data.get('temp_notified_department_complement'):
                            st.write(
                                f"**Complemento Setor Notificado (Ajustado):** {current_data.get('temp_notified_department_complement')}")

                        displayed_executors = [name for name, uid in executor_options.items() if
                                               uid in current_data.get('executores_selecionados', [])]
                        st.write(f"**Executores Atribuídos:** {', '.join(displayed_executors) or 'Nenhum'}")
                        requires_approval_display = current_data.get('requires_approval', UI_TEXTS.text_na)
                        st.write(f"**Requer Aprovação:** {requires_approval_display}")
                        if requires_approval_display == 'Sim':
                            approver_name_display = next((name for name, uid in approver_options.items() if
                                                          uid == current_data.get('approver_selecionado')),
                                                         UI_TEXTS.selectbox_default_approver)
                            st.write(f"**Aprovador Atribuído:** {approver_name_display}")

                col_prev_initial, col_cancel_initial, col_next_submit_initial = st.columns(3)

                with col_prev_initial:
                    if current_step > 1 and current_step <= 7 and current_data.get('procede') != 'Não':
                        if st.button("◀️ Voltar", use_container_width=True,
                                     key=f"back_btn_{notification_id_initial}_step{current_step}_initial_refactored"):
                            current_classification_state['step'] -= 1
                            st.session_state.initial_classification_state[notification_id_initial] = current_classification_state
                            st.rerun()

                with col_cancel_initial:
                    if current_step <= 7:
                        if st.button("🚫 Cancelar Classificação", use_container_width=True,
                                     key=f"cancel_btn_{notification_id_initial}_step{current_step}_initial_refactored"):
                            st.session_state.initial_classification_state.pop(notification_id_initial, None)
                            st.session_state.pop('current_initial_classification_id', None)
                            st.info(f"A classificação inicial da notificação #{notification_id_initial} foi cancelada.")
                            st.rerun()

                with col_next_submit_initial:
                    if current_step < 7 and current_data.get('procede') != 'Não':
                        if st.button(f"➡️ Próximo",
                                     key=f"next_btn_{notification_id_initial}_step{current_step}_initial_refactored",
                                     use_container_width=True):
                            validation_errors = []
                            if current_step == 1:
                                if current_data.get('procede') != 'Sim': validation_errors.append(
                                    'Etapa 1: Para avançar, a notificação deve proceder (selecione \'Sim\').')
                            elif current_step == 2:
                                if current_data.get('classificacao_nnc') == UI_TEXTS.selectbox_default_classificacao_nnc: validation_errors.append(
                                    "Etapa 2: Classificação NNC é obrigatória.")
                                if current_data.get('classificacao_nnc') == "Evento com dano" and current_data.get('nivel_dano') == UI_TEXTS.selectbox_default_nivel_dano: validation_errors.append(
                                    "Etapa 2: Nível de dano é obrigatório para evento com dano.")
                                if current_data.get('prioridade_selecionada') == UI_TEXTS.selectbox_default_prioridade_resolucao: validation_errors.append(
                                    "Etapa 2: Prioridade de Resolução é obrigatória.")
                            elif current_step == 3:
                                if current_data.get('never_event_selecionado') == UI_TEXTS.selectbox_default_never_event: validation_errors.append(
                                    "Etapa 3: Never Event é obrigatório (selecione 'N/A' se não se aplica).")
                                if current_data.get('evento_sentinela_sim_nao') == UI_TEXTS.selectbox_default_evento_sentinela: validation_errors.append(
                                    "Etapa 3: Evento Sentinela é obrigatório (Sim/Não).")
                            elif current_step == 4:
                                if current_data.get('tipo_evento_principal_selecionado') == UI_TEXTS.selectbox_default_tipo_principal:
                                    validation_errors.append("Etapa 4: Tipo Principal de Evento é obrigatório.")
                                elif current_data.get('tipo_evento_principal_selecionado') in ["Clínico", "Não-clínico", "Ocupacional"] and not current_data.get('tipo_evento_sub_selecionado'):
                                    validation_errors.append("Etapa 4: É obrigatório selecionar ao menos uma Especificação do Evento.")
                                elif current_data.get('tipo_evento_principal_selecionado') == 'Outros' and not current_data.get('tipo_evento_sub_texto_livre'):
                                    validation_errors.append("Etapa 4: A especificação do tipo 'Outros' é obrigatória.")
                                elif current_data.get('tipo_evento_principal_selecionado') == 'Queixa técnica' and not current_data.get('tipo_evento_sub_texto_livre'):
                                    validation_errors.append("Etapa 4: A especificação do tipo 'Queixa técnica' é obrigatória.")
                            elif current_step == 5:
                                if not current_data.get('classificacao_oms_selecionada'): validation_errors.append(
                                    "Etapa 5: Classificação OMS é obrigatória (selecione ao menos um item).")

                            if validation_errors:
                                st.error("⚠️ **Por favor, corrija os seguintes erros para avançar:**")
                                for error in validation_errors: st.warning(error)
                            else:
                                current_classification_state['step'] += 1
                                st.session_state.initial_classification_state[notification_id_initial] = current_classification_state
                                st.rerun()

                    is_final_classification_submit_step_initial = current_step == 7 and current_data.get('procede') == 'Sim'
                    is_rejection_submit_step_initial = current_step == 1 and current_data.get('procede') == 'Não'
                    if is_final_classification_submit_step_initial or is_rejection_submit_step_initial:
                        with st.form(
                                key=f"final_classification_submit_form_{notification_id_initial}_step{current_step}_initial_refactored",
                                clear_on_submit=False):
                            submit_button_label = "❌ Rejeitar Notificação" if is_rejection_submit_step_initial else "📤 Enviar Classificação Final"
                            submit_final_action = st.form_submit_button(submit_button_label, use_container_width=True)

                            if submit_final_action:
                                st.subheader("Processando sua decisão final...")
                                validation_errors = []

                                if is_rejection_submit_step_initial:
                                    if not current_data.get('motivo_rejeicao'): validation_errors.append("Justificativa de rejeição é obrigatória.")
                                elif is_final_classification_submit_step_initial:
                                    if current_data.get('procede') != 'Sim': validation_errors.append('Erro interno: Status "procede" inválido para finalização.')
                                    if current_data.get('classificacao_nnc') == UI_TEXTS.selectbox_default_classificacao_nnc: validation_errors.append("Etapa 2: Classificação NNC é obrigatória.")
                                    if current_data.get('classificacao_nnc') == "Evento com dano" and current_data.get('nivel_dano') == UI_TEXTS.selectbox_default_nivel_dano: validation_errors.append("Etapa 2: Nível de dano é obrigatório para evento com dano.")
                                    if current_data.get('prioridade_selecionada') == UI_TEXTS.selectbox_default_prioridade_resolucao: validation_errors.append("Etapa 2: Prioridade de Resolução é obrigatória.")
                                    if current_data.get('never_event_selecionado') == UI_TEXTS.selectbox_default_never_event: validation_errors.append("Etapa 3: Never Event é obrigatório (selecione 'N/A' se não se aplica).")
                                    if current_data.get('evento_sentinela_sim_nao') == UI_TEXTS.selectbox_default_evento_sentinela: validation_errors.append("Etapa 3: Evento Sentinela é obrigatório (Sim/Não).")
                                    if current_data.get('tipo_evento_principal_selecionado') == UI_TEXTS.selectbox_default_tipo_principal: validation_errors.append("Etapa 4: Tipo Principal de Evento é obrigatório.")
                                    if current_data.get('tipo_evento_principal_selecionado') in ["Clínico", "Não-clínico", "Ocupacional"] and not current_data.get('tipo_evento_sub_selecionado'):
                                        validation_errors.append("Etapa 4: É obrigatório selecionar ao menos uma Especificação do Evento.")
                                    elif current_data.get('tipo_evento_principal_selecionado') == 'Outros' and not current_data.get('tipo_evento_sub_texto_livre'):
                                        validation_errors.append("Etapa 4: A especificação do tipo 'Outros' é obrigatória.")
                                    elif current_data.get('tipo_evento_principal_selecionado') == 'Queixa técnica' and not current_data.get('tipo_evento_sub_texto_livre'):
                                        validation_errors.append("Etapa 4: A especificação do tipo 'Queixa técnica' é obrigatória.")

                                    if not current_data.get('classificacao_oms_selecionada'): validation_errors.append("Etapa 5: Classificação OMS é obrigatória (selecione ao menos um item).")
                                    if not current_data.get('temp_notified_department') or \
                                       current_data['temp_notified_department'] == UI_TEXTS.selectbox_default_department_select:
                                        validation_errors.append("Etapa 7: É obrigatório definir o Setor Notificado.")

                                    if not current_data.get('executores_selecionados'): validation_errors.append("Etapa 7: É obrigatório atribuir ao menos um Executor Responsável.")
                                    if current_data.get('requires_approval') == UI_TEXTS.selectbox_default_requires_approval: validation_errors.append("Etapa 7: É obrigatório indicar se requer Aprovação Superior (Sim/Não).")
                                    if current_data.get('requires_approval') == "Sim" and (
                                            current_data.get('approver_selecionado') is None or current_data.get('approver_selecionado') == UI_TEXTS.selectbox_default_approver): validation_errors.append("Etapa 7: É obrigatório selecionar o Aprovador Responsável quando requer aprovação.")

                                if validation_errors:
                                    st.error("⚠️ **Por favor, corrija os seguintes erros antes de enviar:**")
                                    for error in validation_errors: st.warning(error)
                                    st.stop()
                                else:
                                    user_name = st.session_state.user.get('name', 'Usuário')
                                    user_username = st.session_state.user.get('username', UI_TEXTS.text_na)

                                    if is_rejection_submit_step_initial:
                                        updates = {
                                            "status": "rejeitada",
                                            "classification": None,
                                            "executors": [],
                                            "approver": None,
                                            "rejection_classification": {
                                                "reason": current_data.get('motivo_rejeicao'),
                                                "classified_by": user_username,
                                                "timestamp": datetime.now().isoformat()
                                            }
                                        }
                                        update_notification(notification_id_initial, updates)
                                        add_history_entry(
                                            notification_id_initial, "Notificação rejeitada na Classificação Inicial",
                                            user_name,
                                            f"Motivo da rejeição: {current_data.get('motivo_rejeicao', '')[:200]}..." if len(
                                                current_data.get('motivo_rejeicao', '')) > 200 else f"Motivo da rejeição: {current_data.get('motivo_rejeicao', '')}"
                                        )
                                        st.success(f"✅ Notificação #{notification_id_initial} rejeitada com sucesso!")
                                        st.info("Você será redirecionado para a lista atualizada de notificações pendentes.")
                                    elif is_final_classification_submit_step_initial:
                                        all_executors_list_for_map = load_users()
                                        executor_name_to_id_map = {
                                            f"{e.get('name', UI_TEXTS.text_na)} ({e.get('username', UI_TEXTS.text_na)})":
                                                e['id']
                                            for e in all_executors_list_for_map if 'executor' in e.get('roles', []) and e.get('active', True)
                                        }

                                        selected_executor_ids_for_db = [
                                            executor_name_to_id_map[name]
                                            for name in current_data.get('executores_selecionados', [])
                                            if name in executor_name_to_id_map
                                        ]

                                        deadline_days = 0
                                        nnc_type = current_data.get('classificacao_nnc')
                                        if nnc_type == "Evento com dano":
                                            dano_level = current_data.get('nivel_dano')
                                            deadline_days = DEADLINE_DAYS_MAPPING[nnc_type].get(dano_level, 0)
                                        else:
                                            deadline_days = DEADLINE_DAYS_MAPPING.get(nnc_type, 0)

                                        if not isinstance(deadline_days, int):
                                            deadline_days = 0
                                        deadline_date_calculated = (dt_date_class.today() + timedelta(days=deadline_days)).isoformat()

                                        classification_data_to_save = {
                                            "nnc": nnc_type,
                                            "nivel_dano": current_data.get('nivel_dano') if nnc_type == "Evento com dano" else None,
                                            "prioridade": current_data.get('prioridade_selecionada'),
                                            "never_event": current_data.get('never_event_selecionado'),
                                            "is_sentinel_event": True if current_data.get('evento_sentinela_sim_nao') == "Sim" else False if current_data.get('evento_sentinela_sim_nao') == "Não" else None,
                                            "oms": current_data.get('classificacao_oms_selecionada'),
                                            "event_type_main": current_data.get('tipo_evento_principal_selecionado'),
                                            "event_type_sub": current_data.get('tipo_evento_sub_selecionado') if current_data.get('tipo_evento_principal_selecionado') in ["Clínico", "Não-clínico", "Ocupacional"] else (
                                                [current_data.get('tipo_evento_sub_texto_livre')] if current_data.get('tipo_evento_sub_texto_livre') else []),
                                            "notes": current_data.get('observacoes_classificacao'),
                                            "classificador": user_username,
                                            "classification_timestamp": datetime.now().isoformat(),
                                            "requires_approval": True if current_data.get('requires_approval') == "Sim" else False if current_data.get('requires_approval') == "Não" else None,
                                            "deadline_date": deadline_date_calculated
                                        }

                                        updates = {
                                            "status": "classificada",
                                            "classification": classification_data_to_save,
                                            "rejection_classification": None,
                                            "executors": selected_executor_ids_for_db,
                                            "approver": current_data.get('approver_selecionado') if current_data.get('requires_approval') == 'Sim' else None,
                                            "notified_department": current_data.get('temp_notified_department'),
                                            "notified_department_complement": current_data.get('temp_notified_department_complement')
                                        }
                                        update_notification(notification_id_initial, updates)

                                        details_hist = f"Classificação NNC: {classification_data_to_save['nnc']}, Prioridade: {classification_data_to_save.get('prioridade', UI_TEXTS.text_na)}"
                                        if classification_data_to_save["nnc"] == "Evento com dano" and \
                                                classification_data_to_save["nivel_dano"]:
                                            details_hist += f", Nível Dano: {classification_data_to_save['nivel_dano']}"
                                        details_hist += f", Never Event: {classification_data_to_save.get('never_event', UI_TEXTS.text_na)}"
                                        details_hist += f", Evento Sentinela: {'Sim' if classification_data_to_save.get('is_sentinel_event') else 'Não'}"
                                        details_hist += f", Tipo Principal: {classification_data_to_save.get('event_type_main', UI_TEXTS.text_na)}"
                                        sub_detail = classification_data_to_save.get('event_type_sub')
                                        if sub_detail:
                                            if isinstance(sub_detail, list):
                                                details_hist += f" ({', '.join(sub_detail)[:100]}...)" if len(
                                                    ', '.join(sub_detail)) > 100 else f" ({', '.join(sub_detail)})"
                                            else:
                                                details_hist += f" ({str(sub_detail)[:100]}...)" if len(
                                                    str(sub_detail)) > 100 else f" ({str(sub_detail)})"
                                        details_hist += f", Requer Aprovação: {'Sim' if classification_data_to_save.get('requires_approval') else 'Não'}"

                                        all_users = load_users()
                                        exec_ids_in_updates = updates.get('executors', [])
                                        exec_names_for_history = [
                                            u.get('name', UI_TEXTS.text_na) for u in all_users
                                            if u.get('id') in exec_ids_in_updates
                                        ]
                                        details_hist += f", Executores: {', '.join(exec_names_for_history) or 'Nenhum'}"

                                        if updates.get('approver'):
                                            approvers_list_hist = all_users
                                            approver_name_hist = next(
                                                (a.get('name', UI_TEXTS.text_na) for a in approvers_list_hist if
                                                 a.get('id') == updates.get('approver')), UI_TEXTS.text_na)
                                            details_hist += f", Aprovador: {approver_name_hist}"

                                        notified_dept_hist = updates.get('notified_department', UI_TEXTS.text_na)
                                        notified_comp_hist = updates.get('notified_department_complement', '')
                                        details_hist += f", Setor Notificado: {notified_dept_hist}"
                                        if notified_comp_hist:
                                            details_hist += f" ({notified_comp_hist})"

                                        add_history_entry(
                                            notification_id_initial, "Notificação classificada e atribuída",
                                            user_name, details_hist
                                        )
                                        st.success(
                                            f"✅ Notificação #{notification_id_initial} classificada e atribuída com sucesso!")
                                        st.info("A notificação foi movida para a fase de execução e atribuída aos responsáveis.")

                                    st.session_state.initial_classification_state.pop(notification_id_initial, None)
                                    st.session_state.pop('current_initial_classification_id', None)
                                    st.rerun()

            else:
                if pending_initial_classification:
                    st.info(f"👆 Selecione uma notificação da lista acima para visualizar e iniciar a classificação.")

    with tab_review_exec:
        st.markdown("### Notificações Aguardando Revisão da Execução")

        if not pending_execution_review:
            st.info("✅ Não há notificações aguardando revisão da execução no momento.")
        else:
            st.markdown("#### 📋 Selecionar Notificação para Revisão")
            notification_options_review = [UI_TEXTS.selectbox_default_notification_select] + [
                f"#{n['id']} | Classificada em: {n.get('classification', {}).get('classification_timestamp', UI_TEXTS.text_na)[:10]} | {n.get('title', 'Sem título')[:60]}..."
                for n in pending_execution_review
            ]

            pending_review_ids_str = ",".join(str(n['id']) for n in pending_execution_review)
            selectbox_key_review = f"classify_selectbox_review_{pending_review_ids_str}"

            if selectbox_key_review not in st.session_state or st.session_state[
                selectbox_key_review] not in notification_options_review:
                previous_selection = st.session_state.get(selectbox_key_review, notification_options_review[0])
                if previous_selection in notification_options_review:
                    st.session_state[selectbox_key_review] = previous_selection
                else:
                    st.session_state[selectbox_key_review] = notification_options_review[0]

            selected_option_review = st.selectbox(
                "Escolha uma notificação para revisar a execução:",
                options=notification_options_review,
                index=notification_options_review.index(st.session_state[selectbox_key_review]),
                key=selectbox_key_review,
                help="Selecione na lista a notificação cuja execução você deseja revisar.")

            notification_id_review = None
            notification_review = None

            if selected_option_review != UI_TEXTS.selectbox_default_notification_select:
                try:
                    parts = selected_option_review.split('#')
                    if len(parts) > 1:
                        id_part = parts[1].split(' |')[0]
                        notification_id_review = int(id_part)
                        notification_review = next(
                            (n for n in all_notifications if n.get('id') == notification_id_review), None)
                except (IndexError, ValueError):
                    st.error("Erro ao processar a seleção da notificação para revisão.")
                    notification_review = None

            if notification_id_review and (
                    st.session_state.get('current_review_classification_id') != notification_id_review):
                st.session_state.review_classification_state = st.session_state.get('review_classification_state', {})
                st.session_state.review_classification_state[notification_id_review] = {
                    'decision': UI_TEXTS.selectbox_default_decisao_revisao,
                    'rejection_reason_review': '',
                    'notes': '',
                }
                st.session_state.current_review_classification_id = notification_id_review
                if 'current_initial_classification_id' in st.session_state: st.session_state.pop(
                    'current_initial_classification_id')

                st.rerun()

            current_review_data = st.session_state.review_classification_state.get(notification_id_review or 0, {})

            if notification_review is not None:
                st.markdown(
                    f"### Notificação Selecionada para Revisão de Execução: #{notification_review.get('id', UI_TEXTS.text_na)}")

                raw_classification_data = notification_review.get('classification')
                if isinstance(raw_classification_data, dict):
                    classif_info = raw_classification_data
                else:
                    classif_info = {}

                deadline_date_str = classif_info.get('deadline_date')

                concluded_timestamp_str = (notification_review.get('conclusion') or {}).get('timestamp')

                deadline_status = get_deadline_status(deadline_date_str, concluded_timestamp_str)
                card_class = ""
                if deadline_status['class'] == "deadline-ontrack" or deadline_status['class'] == "deadline-duesoon":
                    card_class = "card-prazo-dentro"
                elif deadline_status['class'] == "deadline-overdue":
                    card_class = "card-prazo-fora"

                st.markdown(f"""
                    <div class="notification-card {card_class}">
                        <h4>#{notification_review.get('id', UI_TEXTS.text_na)} - {notification_review.get('title', UI_TEXTS.text_na)}</h4>
                        <p><strong>Status:</strong> <span class="status-{notification_review.get('status', UI_TEXTS.text_na).replace('_', '-')}">{notification_review.get('status', UI_TEXTS.text_na).replace('_', ' ').title()}</span></p>
                        <p><strong>Prazo:</strong> {deadline_status['text']}</p>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("#### 📋 Detalhes para Revisão")
                col_rev1, col_rev2 = st.columns(2)

                with col_rev1:
                    st.markdown("**📝 Evento Reportado Original**")
                    st.write(f"**Título:** {notification_review.get('title', UI_TEXTS.text_na)}")
                    st.write(f"**Local:** {notification_review.get('location', UI_TEXTS.text_na)}")
                    occurrence_datetime_summary = format_date_time_summary(notification_review.get('occurrence_date'),
                                                                           notification_review.get('occurrence_time'))
                    st.write(f"**Data/Hora Ocorrência:** {occurrence_datetime_summary}")
                    st.write(
                        f"**Setor Notificante:** {notification_review.get('reporting_department', UI_TEXTS.text_na)}")
                    if notification_review.get('immediate_actions_taken') and notification_review.get(
                            'immediate_action_description'):
                        st.write(
                            f"**Ações Imediatas Reportadas:** {notification_review.get('immediate_action_description', UI_TEXTS.text_na)[:100]}...")

                with col_rev2:
                    st.markdown("**⏱️ Informações de Gestão e Classificação**")
                    classif_review = classif_info
                    st.write(f"**Classificação NNC:** {classif_review.get('nnc', UI_TEXTS.text_na)}")
                    if classif_review.get('nivel_dano'): st.write(
                        f"**Nível de Dano:** {classif_review.get('nivel_dano', UI_TEXTS.text_na)}")
                    st.write(f"**Prioridade:** {classif_review.get('prioridade', UI_TEXTS.text_na)}")
                    st.write(f"**Never Event:** {classif_review.get('never_event', UI_TEXTS.text_na)}")
                    st.write(f"**Evento Sentinela:** {'Sim' if classif_review.get('is_sentinel_event') else 'Não'}")
                    st.write(f"**Tipo Principal:** {classif_review.get('event_type_main', UI_TEXTS.text_na)}")
                    sub_type_display_review = ''
                    if classif_review.get('event_type_sub'):
                        if isinstance(classif_review['event_type_sub'], list):
                            sub_type_display_review = ', '.join(classif_review['event_type_sub'])
                        else:
                            sub_type_display_review = str(classif_review['event_type_sub'])
                    if sub_type_display_review: st.write(f"**Especificação:** {sub_type_display_review}")
                    st.write(f"**Classificação OMS:** {', '.join(classif_review.get('oms', [UI_TEXTS.text_na]))}")
                    st.write(
                        f"**Requer Aprovação Superior (Classif. Inicial):** {'Sim' if classif_review.get('requires_approval') else 'Não'}")
                    st.write(f"**Classificado por:** {classif_review.get('classificador', UI_TEXTS.text_na)}")

                    if deadline_date_str:
                        deadline_date_formatted = datetime.fromisoformat(deadline_date_str).strftime('%d/%m/%Y')
                        st.markdown(
                            f"**Prazo de Conclusão:** {deadline_date_formatted} (<span class='{deadline_status['class']}'>{deadline_status['text']}</span>)",
                            unsafe_allow_html=True)
                    else:
                        st.write(f"**Prazo de Conclusão:** {UI_TEXTS.deadline_days_nan}")

                st.markdown("---")
                st.markdown("#### ⚡ Ações Executadas pelos Responsáveis")
                if notification_review.get('actions'):
                    for action in sorted(notification_review['actions'], key=lambda x: x.get('timestamp', '')):
                        action_type = "🏁 CONCLUSÃO (Executor)" if action.get(
                            'final_action_by_executor') else "📝 AÇÃO Registrada"
                        action_timestamp = action.get('timestamp', UI_TEXTS.text_na)
                        if action_timestamp != UI_TEXTS.text_na:
                            try:
                                action_timestamp = datetime.fromisoformat(action_timestamp).strftime(
                                    '%d/%m/%Y %H:%M:%S')
                            except ValueError:
                                pass
                        st.markdown(f"""
                                   <strong>{action_type}</strong> - por <strong>{action.get('executor_name', UI_TEXTS.text_na)}</strong> em {action_timestamp}
                                   <br>
                                   <em>{action.get('description', UI_TEXTS.text_na)}</em>
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
                                                    key=f"download_action_evidence_review_{notification_review['id']}_{unique_name}"
                                                )
                                            else:
                                                st.write(
                                                    f"Anexo: {original_name} (arquivo não encontrado ou corrompido)")
                        st.markdown("---")
                else:
                    st.warning("⚠️ Nenhuma ação foi registrada pelos executores para esta notificação ainda.")

                users_review = load_users()
                executor_name_to_id_map_review = {
                    f"{u.get('name', UI_TEXTS.text_na)} ({u.get('username', UI_TEXTS.text_na)})": u['id']
                    for u in users_review if 'executor' in u.get('roles', []) and u.get('active', True)
                }
                executor_names_review = [
                    name for name, uid in executor_name_to_id_map_review.items()
                    if uid in notification_review.get('executors', [])
                ]
                st.markdown(
                    f"**👥 Executores Atribuídos Originalmente:** {', '.join(executor_names_review) or 'Nenhum'}")
                if notification_review.get('attachments'):
                    st.markdown("#### 📎 Anexos")
                    for attach_info in notification_review['attachments']:
                        unique_name_to_use = None
                        original_name_to_use = None
                        if isinstance(attach_info,
                                      dict) and 'unique_name' in attach_info and 'original_name' in attach_info:
                            unique_name_to_use = attach_info['unique_name']
                            original_name_to_use = attach_info['original_name']
                        elif isinstance(attach_info, str):
                            unique_name_to_use = attach_info
                            original_name_to_use = attach_info

                        if unique_name_to_use:
                            file_content = get_attachment_data(unique_name_to_use)
                            if file_content:
                                st.download_button(
                                    label=f"Baixar {original_name_to_use}",
                                    data=file_content,
                                    file_name=original_name_to_use,
                                    mime="application/octet-stream",
                                    key=f"download_review_{notification_review['id']}_{unique_name_to_use}"
                                )
                            else:
                                st.write(f"Anexo: {original_name_to_use} (arquivo não encontrado ou corrompido)")
                st.markdown("---")

                with st.form(key=f"review_decision_form_{notification_id_review}_refactored", clear_on_submit=False):
                    st.markdown("### 🎯 Decisão de Revisão da Execução")

                    decision_options = [UI_TEXTS.selectbox_default_decisao_revisao, "Aceitar Conclusão",
                                        "Rejeitar Conclusão"]
                    current_review_data['decision'] = st.selectbox(
                        "Decisão:*", options=decision_options,
                        key=f"review_decision_{notification_id_review}_refactored",
                        index=decision_options.index(
                            current_review_data.get('decision', UI_TEXTS.selectbox_default_decisao_revisao)),
                        help="Selecione 'Aceitar Conclusão' se a execução foi satisfatória ou 'Rejeitar Conclusão' para devolvê-la para correção/revisão.")
                    st.markdown("<span class='required-field'>* Campo obrigatório</span>", unsafe_allow_html=True)
                    if current_review_data['decision'] == "Rejeitar Conclusão":
                        st.markdown("""
                           <div class="conditional-field">
                               <h4>📝 Detalhes da Rejeição</h4>
                               <p>Explique por que a execução foi rejeitada e o que precisa ser feito.</p>
                           </div>
                           """, unsafe_allow_html=True)
                        current_review_data['rejection_reason_review'] = st.text_area(
                            "Justificativa para Rejeição da Conclusão*",
                            value=current_review_data.get('rejection_reason_review', ''),
                            key=f"rejection_reason_review_{notification_id_review}_refactored",
                            help="Descreva os motivos da rejeição e as ações corretivas necessárias.").strip()
                        st.markdown("<span class='required-field'>* Campo obrigatório ao rejeitar</span>",
                                    unsafe_allow_html=True)
                    else:
                        current_review_data['rejection_reason_review'] = ""

                    current_review_data['notes'] = st.text_area(
                        "Observações da Revisão (opcional)",
                        value=current_review_data.get('notes', ''),
                        key=f"review_notes_{notification_id_review}_refactored",
                        help="Adicione quaisquer observações relevantes sobre a revisão da execução.").strip()
                    submit_button_review = st.form_submit_button("✔️ Confirmar Decisão", use_container_width=True)

                    if submit_button_review:
                        review_decision_state = current_review_data.get('decision', UI_TEXTS.selectbox_default_decisao_revisao)
                        validation_errors = []

                        if review_decision_state == UI_TEXTS.selectbox_default_decisao_revisao: validation_errors.append(
                            "É obrigatório selecionar a decisão da revisão (Aceitar/Rejeitar).")
                        if review_decision_state == "Rejeitar Conclusão" and not current_review_data.get('rejection_reason_review'): validation_errors.append(
                            "Justificativa para Rejeição da Conclusão é obrigatória.")
                        if validation_errors:
                            st.error("⚠️ **Por favor, corrija os seguintes erros:**")
                            for error in validation_errors: st.warning(error)
                            st.stop()
                        else:
                            user_name = st.session_state.user.get('name', 'Usuário')
                            user_username = st.session_state.user.get('username', UI_TEXTS.text_na)
                            review_notes = current_review_data.get('notes')

                            review_details_to_save = {
                                'decision': review_decision_state.replace(' Conclusão', ''),
                                'reviewed_by': user_username,
                                'timestamp': datetime.now().isoformat(),
                                'notes': review_notes or None
                            }
                            if review_decision_state == "Rejeitar Conclusão":
                                review_details_to_save['rejection_reason'] = current_review_data.get('rejection_reason_review')

                            if review_decision_state == "Aceitar Conclusão":
                                original_classification = notification_review.get('classification', {})
                                requires_approval_after_execution = original_classification.get('requires_approval')
                                if requires_approval_after_execution is True:
                                    new_status = 'aguardando_aprovacao'
                                    updates = {
                                        'status': new_status,
                                        'review_execution': review_details_to_save
                                    }

                                    add_history_entry(
                                        notification_id_review, "Revisão de Execução: Conclusão Aceita",
                                        user_name,
                                        f"Execução aceita pelo classificador. Encaminhada para aprovação superior." + (
                                            f" Obs: {review_notes}" if review_notes else ""))
                                    st.success(
                                        f"✅ Execução da Notificação #{notification_id_review} aceita! Encaminhada para aprovação superior.")
                                else:
                                    new_status = 'aprovada'
                                    updates = {
                                        'status': new_status,
                                        'review_execution': review_details_to_save,
                                        'conclusion': {
                                            'concluded_by': user_username,
                                            'notes': review_notes or "Execução revisada e aceita pelo classificador.",
                                            'timestamp': datetime.now().isoformat(),
                                            'status_final': 'aprovada'
                                        },
                                        'approver': None
                                    }

                                    add_history_entry(
                                        notification_id_review, "Revisão de Execução: Conclusão Aceita e Finalizada",
                                        user_name,
                                        f"Execução revisada e aceita pelo classificador. Ciclo de gestão do evento concluído (não requeria aprovação superior)." + (
                                            f" Obs: {review_notes}" if review_notes else ""))
                                    st.success(
                                        f"✅ Execução da Notificação #{notification_id_review} revisada e aceita. Notificação concluída!")
                            elif review_decision_state == "Rejeitar Conclusão":
                                new_status = 'pendente_classificacao'
                                updates = {
                                    'status': new_status,
                                    'approver': None,
                                    'executors': [],
                                    'classification': None,
                                    'review_execution': None,
                                    'approval': None,
                                    'conclusion': None,
                                    'rejection_execution_review': {
                                        'reason': current_review_data.get('rejection_reason_review'),
                                        'reviewed_by': user_username,
                                        'timestamp': datetime.now().isoformat()
                                    }
                                }
                                add_history_entry(
                                    notification_id_review,
                                    "Revisão de Execução: Conclusão Rejeitada e Reclassificação Necessária",
                                    user_name,
                                    f"Execução rejeitada. Notificação movida para classificação inicial para reanálise e reatribuição. Motivo: {current_review_data.get('rejection_reason_review', '')[:150]}..." if len(
                                        current_review_data.get('rejection_reason_review', '')) > 150 else f"Execução rejeitada. Notificação movida para classificação inicial para reanálise e reatribuição. Motivo: {current_review_data.get('rejection_reason_review', '')}" + (
                                        f" Obs: {review_notes}" if review_notes else ""))
                                st.warning(
                                    f"⚠️ Execução da Notificação #{notification_id_review} rejeitada! Devolvida para classificação inicial para reanálise e reatribuição.")
                                st.info(
                                    "A notificação foi movida para o status 'pendente_classificacao' e aparecerá na aba 'Pendentes Classificação Inicial' para que a equipe de classificação possa reclassificá-la e redefinir o fluxo.")
                            update_notification(notification_id_review, updates)
                            st.session_state.review_classification_state.pop(notification_id_review, None)
                            st.session_state.pop('current_review_classification_id', None)
                            st.rerun()
            else:
                if pending_execution_review:
                    st.info(f"👆 Selecione uma notificação da lista acima para revisar a execução concluída.")

    with tab_closed_notifs:
        st.markdown("### Notificações Encerradas")

        if not closed_notifications:
            st.info("✅ Não há notificações encerradas no momento.")
        else:
            st.info(f"Total de notificações encerradas: {len(closed_notifications)}.")

            search_query = st.text_input(
                "🔎 Buscar Notificação Encerrada (Título, Descrição, ID):",
                key="closed_notif_search_input",
                placeholder="Ex: 'queda paciente', '12345', 'medicamento errado'"
            ).lower()

            filtered_closed_notifications = []
            if search_query:
                for notif in closed_notifications:
                    if search_query.isdigit() and int(search_query) == notif.get('id'):
                        filtered_closed_notifications.append(notif)
                    elif (search_query in notif.get('title', '').lower() or
                          search_query in notif.get('description', '').lower()):
                        filtered_closed_notifications.append(notif)
            else:
                filtered_closed_notifications = closed_notifications

            if not filtered_closed_notifications:
                st.warning("⚠️ Nenhuma notificação encontrada com os critérios de busca especificados.")
            else:
                filtered_closed_notifications.sort(key=lambda x: x.get('created_at', ''), reverse=True)

                st.markdown(f"**Notificações Encontradas ({len(filtered_closed_notifications)})**:")
                for notification in filtered_closed_notifications:
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

                    raw_classification_data = notification.get('classification')
                    if isinstance(raw_classification_data, dict):
                        classif_info_closed = raw_classification_data
                    else:
                        classif_info_closed = {}
                    deadline_date_str_closed = classif_info_closed.get('deadline_date')

                    concluded_timestamp_str = (notification.get('conclusion') or {}).get('timestamp')
                    deadline_status = get_deadline_status(deadline_date_str_closed, concluded_timestamp_str)
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
                            f"👁️ Visualizar Detalhes - Notificação #{notification.get('id', UI_TEXTS.text_na)}"):
                        # Usa st.session_state.user para passar o ID do usuário logado e username
                        display_notification_full_details(notification, st.session_state.user.get('id'), st.session_state.user.get('username'))