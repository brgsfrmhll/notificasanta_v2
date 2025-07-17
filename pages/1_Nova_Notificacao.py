# pages/1_Nova_Notificacao.py

import streamlit as st
from datetime import datetime, date as dt_date_class, time as dt_time_class
import time as time_module

# Importa funções e constantes do arquivo principal e de utilidades
from streamlit_app import create_notification
from constants import UI_TEXTS, FORM_DATA
from utils import _reset_form_state, format_date_time_summary


def run():
    """
    Renderiza a página para criar novas notificações como um formulário multi-etapa.
    Controla as etapas usando st.session_state e gerencia a persistência explícita de dados e a validação.
    """
    st.markdown("<h1 class='main-header'>📝 Nova Notificação (Formulário NNC)</h1>", unsafe_allow_html=True)
    if not st.session_state.authenticated:
        st.info("Para acompanhar o fluxo completo de uma notificação (classificação, execução, aprovação), faça login.")

    if 'form_step' not in st.session_state:
        _reset_form_state()

    current_data = st.session_state.create_form_data
    current_step = st.session_state.form_step

    if current_step == 5:
        st.balloons()
        st.markdown(r"""
        <div style="text-align: center; margin-top: 100px;">
            <h1 style="color: #2E86AB; font-size: 3em;">
                ✅ Notificação Enviada com Sucesso! 😊
            </h1>
            <p style="font-size: 1.2em; color: #555;">
                Obrigado pela sua participação! Voltando para um novo formulário...
            </p>
        </div>
        """, unsafe_allow_html=True)
        time_module.sleep(2)
        _reset_form_state()
        # Não precisa de st.rerun() aqui, o Streamlit vai re-renderizar a página
        # após o sleep e o reset do form_step.
        return

    st.markdown(f"### Etapa {current_step}")

    if current_step == 1:
        with st.container():
            st.markdown("""
            <div class="form-section">
                <h3>📋 Etapa 1: Detalhes da Ocorrência</h3>
                <p>Preencha as informações básicas sobre o evento ocorrido.</p>
            </div>
            """, unsafe_allow_html=True)

            current_data['title'] = st.text_input(
                "Título da Notificação*", value=current_data['title'], placeholder="Breve resumo da notificação",
                help="Descreva brevemente o evento ocorrido", key="create_title_state_refactored")
            current_data['location'] = st.text_input(
                "Local do Evento*", value=current_data['location'],
                placeholder="Ex: UTI - Leito 05, Centro Cirúrgico - Sala 3",
                help="Especifique o local exato onde ocorreu o evento", key="create_location_state_refactored")

            col1, col2 = st.columns(2)
            with col1:
                current_data['occurrence_date'] = st.date_input(
                    "Data da Ocorrência do Evento*", value=current_data['occurrence_date'],
                    help="Selecione a data em que o evento ocorreu", key="create_occurrence_date_state_refactored",
                    format="DD/MM/YYYY")
            with col2:
                current_data['occurrence_time'] = st.time_input(
                    "Hora Aproximada do Evento", value=current_data['occurrence_time'],
                    help="Hora aproximada em que o evento ocorreu.", key="create_event_time_state_refactored")

            reporting_dept_options = [UI_TEXTS.selectbox_default_department_select] + FORM_DATA.SETORES
            current_data['reporting_department'] = st.selectbox(
                "Setor Notificante*",
                options=reporting_dept_options,
                index=reporting_dept_options.index(current_data['reporting_department'])
                      if current_data['reporting_department'] in reporting_dept_options
                      else 0,
                help="Selecione o setor responsável por notificar o evento",
                key="create_reporting_dept_state_refactored"
            )
            current_data['reporting_department_complement'] = st.text_input(
                "Complemento do Setor Notificante", value=current_data['reporting_department_complement'],
                placeholder="Informações adicionais do setor (opcional)",
                help="Detalhes adicionais sobre o setor notificante (Ex: Equipe A, Sala 101)",
                key="create_reporting_dept_comp_state_refactored")

            event_shift_options = [UI_TEXTS.selectbox_default_event_shift] + FORM_DATA.turnos
            current_data['event_shift'] = st.selectbox(
                "Turno do Evento*", options=event_shift_options,
                index=event_shift_options.index(current_data['event_shift']) if current_data['event_shift'] in event_shift_options else 0,
                help="Turno em que o evento ocorreu", key="create_event_shift_state_refactored")

            current_data['description'] = st.text_area(
                "Descrição Detalhada do Evento*", value=current_data['description'],
                placeholder="Descreva:\n• O que aconteceu?\n• Quando aconteceu?\n• Onde aconteceu?\n• Quem esteve envolvido?\n• Como aconteceu?\n• Consequências observadas",
                height=150,
                key="create_description_state_refactored")

            st.markdown("<span class='required-field'>* Campos obrigatórios</span>", unsafe_allow_html=True)
            st.markdown("---")

    elif current_step == 2:
        with st.container():
            st.markdown("""
            <div class="form-section">
                <h3>⚡ Etapa 2: Ações Imediatas</h3>
                <p>Indique se alguma ação foi tomada imediatamente após o evento.</p>
            </div>
            """, unsafe_allow_html=True)

            immediate_actions_taken_options = [UI_TEXTS.selectbox_default_immediate_actions_taken, "Sim", "Não"]
            current_data['immediate_actions_taken'] = st.selectbox(
                "Foram tomadas ações imediatas?*", options=immediate_actions_taken_options,
                index=immediate_actions_taken_options.index(current_data['immediate_actions_taken']) if current_data['immediate_actions_taken'] in immediate_actions_taken_options else 0,
                key="immediate_actions_taken_state_refactored", help="Indique se alguma ação foi tomada...")
            st.markdown("<span class='required-field'>* Campo obrigatório</span>", unsafe_allow_html=True)

            if current_data['immediate_actions_taken'] == 'Sim':
                st.markdown("""
                <div class="conditional-field">
                    <h4>📝 Detalhes das Ações Imediatas</h4>
                    <p>Descreva detalhadamente as ações que foram tomadas.</p>
                </div>
                """, unsafe_allow_html=True)
                current_data['immediate_action_description'] = st.text_area(
                    "Descrição detalhada da ação realizada*", value=current_data['immediate_action_description'],
                    placeholder="Descreva:\n• Quais ações foram tomadas?\n• Por quem foram executadas?\n• Quando foram realizadas?\n• Resultados obtidos",
                    height=150,
                    key="create_immediate_action_desc_state_refactored",
                    help="Forneça um relato completo...")
                st.markdown("<span class='required-field'>* Campo obrigatório</span>", unsafe_allow_html=True)
            else:
                current_data['immediate_action_description'] = ""

            st.markdown("---")

    elif current_step == 3:
        with st.container():
            st.markdown("""
            <div class="form-section">
                <h3>🏥 Etapa 3: Impacto no Paciente</h3>
                <p>Indique se o evento teve qualquer tipo de envolvimento ou impacto em um paciente.</p>
            </div>
            """, unsafe_allow_html=True)

            patient_involved_options = [UI_TEXTS.selectbox_default_patient_involved, "Sim", "Não"]
            current_data['patient_involved'] = st.selectbox(
                "O evento atingiu algum paciente?*", options=patient_involved_options,
                index=patient_involved_options.index(current_data['patient_involved']) if current_data['patient_involved'] in patient_involved_options else 0,
                key="patient_involved_state_refactored",
                help="Indique se o evento teve qualquer tipo de envolvimento...")
            st.markdown("<span class='required-field'>* Campo obrigatório</span>", unsafe_allow_html=True)

            if current_data['patient_involved'] == 'Sim':
                st.markdown("""
                <div class="conditional-field">
                    <h4>🏥 Informações do Paciente Afetado</h4>
                    <p>Preencha as informações do paciente envolvido no evento.</p>
                </div>
                """, unsafe_allow_html=True)
                col5, col6 = st.columns(2)
                with col5:
                    current_data['patient_id'] = st.text_input(
                        "Número do Atendimento/Prontuário*", value=current_data['patient_id'],
                        placeholder="Ex: 123456789", key="create_patient_id_refactored",
                        help="Número de identificação do paciente...")
                with col6:
                    patient_outcome_obito_options = [UI_TEXTS.selectbox_default_patient_outcome_obito, "Sim", "Não"]
                    current_data['patient_outcome_obito'] = st.selectbox(
                        "O paciente evoluiu com óbito?*", options=patient_outcome_obito_options,
                        index=patient_outcome_obito_options.index(current_data['patient_outcome_obito']) if current_data['patient_outcome_obito'] in patient_outcome_obito_options else 0,
                        key="create_patient_outcome_obito_refactored",
                        help="Indique se o evento resultou diretamente no óbito do paciente.")
                st.markdown("<span class='required-field'>* Campos obrigatórios</span>", unsafe_allow_html=True)
            else:
                current_data['patient_id'] = ""
                current_data['patient_outcome_obito'] = UI_TEXTS.selectbox_default_patient_outcome_obito

            st.markdown("---")

    elif current_step == 4:
        with st.container():
            st.markdown("""
            <div class="form-section">
                <h3>📄 Etapa 4: Informações Adicionais e Evidências</h3>
                <p>Complete as informações adicionais e anexe documentos, se aplicável.</p>
            </div>
            """, unsafe_allow_html=True)

            col7, col8 = st.columns(2)
            with col7:
                notified_dept_options = [UI_TEXTS.selectbox_default_department_select] + FORM_DATA.SETORES
                current_data['notified_department'] = st.selectbox(
                    "Setor Notificado*",
                    options=notified_dept_options,
                    index=notified_dept_options.index(current_data['notified_department'])
                          if current_data['notified_department'] in notified_dept_options
                          else 0,
                    help="Selecione o setor que será notificado sobre o evento",
                    key="create_notified_dept_refactored"
                )
            with col8:
                current_data['notified_department_complement'] = st.text_input(
                    "Complemento do Setor Notificado", value=current_data['notified_department_complement'],
                    placeholder="Informações adicionais (opcional)",
                    help="Detalhes adicionais sobre o setor notificante (Ex: Equipe A, Sala 101)",
                    key="create_notified_dept_comp_refactored"
                )
            st.markdown("<span class='required-field'>* Campo obrigatório (Setor Notificado)</span>",
                        unsafe_allow_html=True)

            current_data['additional_notes'] = st.text_area(
                "Observações Adicionais", value=current_data['additional_notes'],
                placeholder="Qualquer outra informação que considere relevante.",
                height=100, key="additional_notes_refactored",
                help="Adicione qualquer outra informação relevante...")
            st.markdown("---")

            st.markdown("### Documentos e Evidências")
            uploaded_files_list_widget = st.file_uploader(
                "Anexar arquivos relacionados ao evento (Opcional)", type=None, accept_multiple_files=True,
                help="Anexe fotos, documentos...", key="create_attachments_refactored"
            )

            current_data['attachments'] = st.session_state.get('create_attachments_refactored', [])

            if current_data.get('attachments'):
                st.info(
                    f"   {len(current_data['attachments'])} arquivo(s) selecionado(s): {', '.join([f.name for f in current_data['attachments']])}")

            st.markdown("---")

    col_prev, col_cancel_btn, col_next_submit = st.columns(3)

    with col_prev:
        if current_step > 1 and current_step < 5:
            if st.button("◀️ Voltar", key=f"step_back_btn_refactored_{current_step}",
                         use_container_width=True):
                st.session_state.form_step -= 1
                st.rerun()

    with col_cancel_btn:
        if current_step < 5:
            if st.button("🚫 Cancelar Notificação", key="step_cancel_btn_refactored",
                         use_container_width=True):
                _reset_form_state()
                st.rerun()

    with col_next_submit:
        if current_step < 4:
            if st.button(f"➡️ Próximo",
                         key=f"step_next_btn_refactored_{current_step}", use_container_width=True):
                validation_errors = []

                if current_step == 1:
                    if not current_data['title'].strip(): validation_errors.append(
                        'Etapa 1: Título da Notificação é obrigatório.')
                    if not current_data['description'].strip(): validation_errors.append(
                        'Etapa 1: Descrição Detalhada é obrigatória.')
                    if not current_data['location'].strip(): validation_errors.append(
                        'Etapa 1: Local do Evento é obrigatório.')
                    if current_data['occurrence_date'] is None or not isinstance(current_data['occurrence_date'],
                                                                                 dt_date_class): validation_errors.append(
                        'Etapa 1: Data da Ocorrência é obrigatória.')
                    if current_data['reporting_department'] == UI_TEXTS.selectbox_default_department_select:
                        validation_errors.append('Etapa 1: Setor Notificante é obrigatório.')
                    if current_data['event_shift'] == UI_TEXTS.selectbox_default_event_shift: validation_errors.append(
                        'Etapa 1: Turno do Evento é obrigatório.')

                elif current_step == 2:
                    if current_data['immediate_actions_taken'] == UI_TEXTS.selectbox_default_immediate_actions_taken: validation_errors.append(
                        'Etapa 2: É obrigatório indicar se foram tomadas Ações Imediatas (Sim/Não).')
                    if current_data['immediate_actions_taken'] == "Sim" and not current_data['immediate_action_description'].strip(): validation_errors.append(
                        "Etapa 2: Descrição das ações imediatas é obrigatória quando há ações imediatas.")
                elif current_step == 3:
                    if current_data['patient_involved'] == UI_TEXTS.selectbox_default_patient_involved: validation_errors.append(
                        'Etapa 3: É obrigatório indicar se o Paciente foi Afetado (Sim/Não).')
                    if current_data['patient_involved'] == "Sim":
                        if not current_data['patient_id'].strip(): validation_errors.append(
                            "Etapa 3: Número do Atendimento/Prontuário é obrigatório quando paciente é afetado.")
                        if current_data['patient_outcome_obito'] == UI_TEXTS.selectbox_default_patient_outcome_obito: validation_errors.append(
                            "Etapa 3: Evolução para óbito é obrigatório quando paciente é afetado.")

                if validation_errors:
                    st.error("⚠️ **Por favor, corrija os seguintes erros:**")
                    for error in validation_errors:
                        st.warning(error)
                else:
                    st.session_state.form_step += 1
                    st.rerun()

        elif current_step == 4:
            with st.form("submit_form_refactored_step4", clear_on_submit=False):
                submit_button = st.form_submit_button("📤 Enviar Notificação", use_container_width=True)

                if submit_button:
                    st.subheader("Validando e Enviando Notificação...")
                    validation_errors = []

                    if not current_data['title'].strip(): validation_errors.append(
                        'Etapa 1: Título da Notificação é obrigatório.')
                    if not current_data['description'].strip(): validation_errors.append(
                        'Etapa 1: Descrição Detalhada é obrigatória.')
                    if not current_data['location'].strip(): validation_errors.append(
                        'Etapa 1: Local do Evento é obrigatório.')
                    if current_data['occurrence_date'] is None or not isinstance(current_data['occurrence_date'], dt_date_class): validation_errors.append(
                        'Etapa 1: Data da Ocorrência é obrigatória.')
                    if not current_data['reporting_department'] or \
                       current_data['reporting_department'] == UI_TEXTS.selectbox_default_department_select:
                        validation_errors.append("Etapa 1: Setor Notificante é obrigatório.")
                    if current_data['event_shift'] == UI_TEXTS.selectbox_default_event_shift: validation_errors.append(
                        'Etapa 1: Turno do Evento é obrigatório.')
                    if current_data['immediate_actions_taken'] == UI_TEXTS.selectbox_default_immediate_actions_taken: validation_errors.append(
                        'Etapa 2: É obrigatório indicar se foram tomadas Ações Imediatas (Sim/Não).')
                    if current_data['immediate_actions_taken'] == "Sim" and not current_data['immediate_action_description'].strip(): validation_errors.append(
                        "Etapa 2: Descrição das ações imediatas é obrigatória quando há ações imediatas.")
                    if current_data['patient_involved'] == UI_TEXTS.selectbox_default_patient_involved: validation_errors.append(
                        'Etapa 3: É obrigatório indicar se o Paciente foi Afetado (Sim/Não).')
                    if current_data['patient_involved'] == "Sim":
                        if not current_data['patient_id'].strip(): validation_errors.append(
                            "Etapa 3: Número do Atendimento/Prontuário é obrigatório quando paciente é afetado.")
                        if current_data['patient_outcome_obito'] == UI_TEXTS.selectbox_default_patient_outcome_obito: validation_errors.append(
                            "Etapa 3: Evolução para óbito é obrigatório quando paciente é afetado.")
                    if not current_data['notified_department'] or \
                       current_data['notified_department'] == UI_TEXTS.selectbox_default_department_select:
                        validation_errors.append("Etapa 4: Setor Notificado é obrigatório.")

                    if validation_errors:
                        st.error("⚠️ **Por favor, corrija os seguintes erros antes de enviar:**")
                        for error in validation_errors:
                            st.warning(error)
                    else:
                        notification_data_to_save = current_data.copy()
                        uploaded_files_list = notification_data_to_save.pop('attachments', [])
                        try:
                            notification = create_notification(notification_data_to_save, uploaded_files_list)
                            st.success(f"✅ **Notificação #{notification['id']} criada com sucesso!**")
                            st.info(
                                "📋 Sua notificação foi enviada para classificação e será processada pela equipe responsável.")
                            with st.expander("📄 Resumo da Notificação Enviada", expanded=False):
                                occurrence_datetime_summary = format_date_time_summary(
                                    notification_data_to_save.get('occurrence_date'),
                                    notification_data_to_save.get('occurrence_time')
                                )

                                st.write(f"**ID:** #{notification['id']}")
                                st.write(f"**Título:** {notification_data_to_save.get('title', UI_TEXTS.text_na)}")
                                st.write(f"**Local:** {notification_data_to_save.get('location', UI_TEXTS.text_na)}")
                                st.write(f"**Data/Hora do Evento:** {occurrence_datetime_summary}")
                                st.write(
                                    f"**Turno:** {notification_data_to_save.get('event_shift', UI_TEXTS.text_na)}")
                                reporting_department = notification_data_to_save.get('reporting_department',
                                                                                    UI_TEXTS.text_na)
                                reporting_complement = notification_data_to_save.get('reporting_department_complement')
                                reporting_dept_display = f"{reporting_department}{f' ({reporting_complement})' if reporting_complement else ''}"
                                st.write(f"**Setor Notificante:** {reporting_dept_display}")

                                notified_department = notification_data_to_save.get('notified_department',
                                                                                    UI_TEXTS.text_na)
                                notified_complement = notification_data_to_save.get('notified_department_complement')
                                notified_dept_display = f"{notified_department}{f' ({notified_complement})' if notified_complement else ''}"
                                st.write(f"**Setor Notificado:** {notified_dept_display}")

                                st.write(
                                    f"**Descrição:** {notification_data_to_save.get('description', UI_TEXTS.text_na)[:200]}..." if len(
                                        notification_data_to_save.get('description', '')) > 200 else notification_data_to_save.get('description', UI_TEXTS.text_na))
                                st.write(
                                    f"**Ações Imediatas Tomadas:** {notification_data_to_save.get('immediate_actions_taken', UI_TEXTS.text_na)}")
                                if notification_data_to_save.get('immediate_actions_taken') == 'Sim':
                                    st.write(
                                        f"**Descrição Ações Imediatas:** {notification_data_to_save.get('immediate_action_description', UI_TEXTS.text_na)[:200]}..." if len(
                                            notification_data_to_save.get('immediate_action_description', '')) > 200 else notification_data_to_save.get('immediate_action_description', UI_TEXTS.text_na))
                                st.write(
                                    f"**Paciente Envolvido:** {notification_data_to_save.get('patient_involved', UI_TEXTS.text_na)}")
                                if notification_data_to_save.get('patient_involved') == 'Sim':
                                    st.write(
                                        f"**N° Atendimento:** {notification_data_to_save.get('patient_id', UI_TEXTS.text_na)}")
                                    outcome_text = 'Sim' if notification_data_to_save.get('patient_outcome_obito') is True else 'Não' if notification_data_to_save.get('patient_outcome_obito') is False else 'Não informado'
                                    st.write(f"**Evoluiu para óbito:** {outcome_text}")
                                if notification_data_to_save.get('additional_notes'):
                                    st.write(
                                        f"**Observações Adicionais:** {notification_data_to_save.get('additional_notes', UI_TEXTS.text_na)[:200]}..." if len(
                                            notification_data_to_save.get('additional_notes', '')) > 200 else notification_data_to_save.get('additional_notes', UI_TEXTS.text_na))
                                if uploaded_files_list:
                                    st.write(
                                        f"**Anexos:** {len(uploaded_files_list)} arquivo(s) - {', '.join([f.name for f in uploaded_files_list])}")
                                else:
                                    st.write("**Anexos:** Nenhum arquivo anexado.")

                            st.session_state.form_step = 5
                            st.rerun()

                        except Exception as e:
                            st.error(f"❌ Ocorreu um erro ao finalizar a notificação: {e}")
                            st.warning("Por favor, revise as informações e tente enviar novamente.")
