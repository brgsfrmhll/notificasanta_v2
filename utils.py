# utils.py

import streamlit as st
import os
from datetime import datetime, date as dt_date_class, time as dt_time_class, timedelta
from typing import Dict, List, Optional, Any
import uuid

# Importa as constantes
from constants import UI_TEXTS, ATTACHMENTS_DIR, DEADLINE_DAYS_MAPPING

# Importa as funções do streamlit_app que interagem com o DB, para evitar circular imports
# As funções que usam st.session_state e st.rerun() serão tratadas nas páginas ou no main.
# As funções de DB que são chamadas aqui precisam ser importadas do streamlit_app
# Adicionei os imports comentados, mas certifique-se que o streamlit_app.py as define para que possam ser importadas.
# from streamlit_app import get_notification_attachments, get_notification_history, get_notification_actions, load_users

def get_deadline_status(deadline_date_str: Optional[str], completion_timestamp_str: Optional[str] = None) -> Dict:
    """
    Calcula o status do prazo com base no prazo final e, caso aplicável, também se a notificação foi concluída a tempo.
    Retorna um dicionário com 'text' (status) e 'class' (classe CSS para estilo).
    """
    if not deadline_date_str:
        return {"text": UI_TEXTS.deadline_days_nan, "class": ""}

    try:
        deadline_date = dt_date_class.fromisoformat(deadline_date_str)

        if completion_timestamp_str:
            completion_date = datetime.fromisoformat(completion_timestamp_str).date()
            if completion_date <= deadline_date:
                return {"text": UI_TEXTS.deadline_status_ontrack, "class": "deadline-ontrack"}
            else:
                return {"text": UI_TEXTS.deadline_status_overdue, "class": "deadline-overdue"}
        else:
            today = dt_date_class.today()
            days_diff = (deadline_date - today).days

            if days_diff < 0:
                return {"text": UI_TEXTS.deadline_status_overdue, "class": "deadline-overdue"}
            elif days_diff <= 7:
                return {"text": UI_TEXTS.deadline_status_duesoon, "class": "deadline-duesoon"}
            else:
                return {"text": UI_TEXTS.deadline_status_ontrack, "class": "deadline-ontrack"}
    except ValueError:
        return {"text": UI_TEXTS.text_na, "class": ""}

def format_date_time_summary(date_val: Any, time_val: Any) -> str:
    """Formata data e hora opcional para exibição."""
    date_part_formatted = UI_TEXTS.text_na
    time_part_formatted = ''

    if isinstance(date_val, dt_date_class):
        date_part_formatted = date_val.strftime('%d/%m/%Y')
    elif isinstance(date_val, str) and date_val:
        try:
            date_part_formatted = datetime.fromisoformat(date_val).date().strftime('%d/%m/%Y')
        except ValueError:
            date_part_formatted = 'Data inválida'
    elif date_val is None:
        date_part_formatted = 'Não informada'

    if isinstance(time_val, dt_time_class):
        time_part_formatted = f" às {time_val.strftime('%H:%M')}"
    elif isinstance(time_val, str) and time_val and time_val.lower() != 'none':
        try:
            time_str_part = time_val.split('.')[0]
            try:
                time_obj = datetime.strptime(time_str_part, '%H:%M:%S').time()
                if time_obj == datetime.strptime("00:00:00", '%H:%M:%S').time():
                    time_part_formatted = ''
                else:
                    time_part_formatted = f" às {time_obj.strftime('%H:%M')}"
            except ValueError:
                try:
                    time_obj = datetime.strptime("00:00", '%H:%M').time()
                    if time_obj == datetime.strptime("00:00", '%H:%M').time():
                        time_part_formatted = ''
                    else:
                        time_part_formatted = f" às {time_obj.strftime('%H:%M')}"
                except ValueError:
                    time_part_formatted = f" às {time_val}"
                    time_obj = None
        except ValueError:
            time_part_formatted = f" às {time_val}"
    elif time_val is None:
        time_part_formatted = ''

    return f"{date_part_formatted}{time_part_formatted}"

def _clear_execution_form_state(notification_id: int):
    """Limpa as chaves do session_state para o formulário de execução após o envio."""
    key_desc = f"exec_action_desc_{notification_id}_refactored"
    key_choice = f"exec_action_choice_{notification_id}_refactored"
    key_evidence_desc = f"exec_evidence_desc_{notification_id}_refactored"
    key_evidence_attachments = f"exec_evidence_attachments_{notification_id}_refactored"

    if key_desc in st.session_state:
        del st.session_state[key_desc]
    if key_choice in st.session_state:
        del st.session_state[key_choice]
    if key_evidence_desc in st.session_state:
        del st.session_state[key_evidence_desc]
    if key_evidence_attachments in st.session_state:
        del st.session_state[key_evidence_attachments]

def _clear_approval_form_state(notification_id: int):
    """Limpa as chaves do session_state para o formulário de aprovação."""
    key_notes = f"approval_notes_{notification_id}_refactored"
    key_decision = f"approval_decision_{notification_id}_refactored"

    if key_notes in st.session_state:
        del st.session_state[key_notes]
    if key_decision in st.session_state:
        del st.session_state[key_decision]

    if 'approval_form_state' in st.session_state and notification_id in st.session_state.approval_form_state:
        del st.session_state.approval_form_state[notification_id]

def _reset_form_state():
    """Reinicia as variáveis de estado para o formulário de criação de notificação e outros estados específicos da página."""
    keys_to_clear = [
        'form_step', 'create_form_data',
        'create_title_state_refactored', 'create_location_state_refactored',
        'create_occurrence_date_state_refactored', 'create_event_time_state_refactored',
        'create_reporting_dept_state_refactored', 'create_reporting_dept_comp_state_refactored',
        'create_event_shift_state_refactored', 'create_description_state_refactored',
        'immediate_actions_taken_state_refactored', 'create_immediate_action_desc_state_refactored',
        'patient_involved_state_refactored', 'create_patient_id_state_refactored',
        'create_patient_outcome_obito_state_refactored', 'create_notified_dept_state_refactored',
        'create_notified_dept_comp_state_refactored', 'additional_notes_state_refactored',
        'create_attachments_state_refactored',
        # Dashboard states
        'dashboard_filter_status', 'dashboard_filter_nnc', 'dashboard_filter_priority',
        'dashboard_filter_date_start', 'dashboard_filter_date_end', 'dashboard_search_query',
        'dashboard_sort_column', 'dashboard_sort_ascending', 'dashboard_current_page', 'dashboard_items_per_page'
    ]
    current_keys = set(st.session_state.keys())
    for key in current_keys:
        if key in keys_to_clear:
            st.session_state.pop(key, None)

    st.session_state.form_step = 1
    st.session_state.create_form_data = {
        'title': '', 'location': '', 'occurrence_date': datetime.now().date(),
        'occurrence_time': datetime.now().time(),
        'reporting_department': UI_TEXTS.selectbox_default_department_select,
        'reporting_department_complement': '', 'event_shift': UI_TEXTS.selectbox_default_event_shift,
        'description': '',
        'immediate_actions_taken': UI_TEXTS.selectbox_default_immediate_actions_taken,
        'immediate_action_description': '',
        'patient_involved': UI_TEXTS.selectbox_default_patient_involved,
        'patient_id': '',
        'patient_outcome_obito': UI_TEXTS.selectbox_default_patient_outcome_obito,
        'notified_department': UI_TEXTS.selectbox_default_department_select,
        'notified_department_complement': '', 'additional_notes': '', 'attachments': []
    }

def save_uploaded_file_to_disk(uploaded_file: Any, notification_id: int) -> Optional[Dict]:
    """Salva um arquivo enviado para o diretório de anexos no disco e retorna suas informações."""
    if uploaded_file is None:
        return None
    original_name = uploaded_file.name
    safe_original_name = "".join(c for c in original_name if c.isalnum() or c in ('.', '_', '-')).rstrip('.')
    unique_filename = f"{notification_id}_{uuid.uuid4().hex}_{safe_original_name}"
    file_path = os.path.join(ATTACHMENTS_DIR, unique_filename)
    try:
        os.makedirs(ATTACHMENTS_DIR, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return {"unique_name": unique_filename, "original_name": original_name}
    except Exception as e:
        st.error(f"Erro ao salvar o anexo {original_name} no disco: {e}")
        return None

def get_attachment_data(unique_filename: str) -> Optional[bytes]:
    """Lê o conteúdo de um arquivo de anexo do disco."""
    file_path = os.path.join(ATTACHMENTS_DIR, unique_filename)
    try:
        with open(file_path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        st.warning(f"Anexo não encontrado no caminho: {unique_filename}")
        return None
    except Exception as e:
        st.error(f"Erro ao ler o anexo {unique_filename}: {e}")
        return None

def display_notification_full_details(notification: Dict, user_id_logged_in: Optional[int] = None,
                                      user_username_logged_in: Optional[str] = None):
    """
    Exibe os detalhes completos de uma notificação.
    A função get_notification_actions deve ser importada do streamlit_app.
    """
    # Importação LOCAL para evitar circular imports no topo do utils.py
    # Assumimos que essas funções estão disponíveis no streamlit_app.py
    from streamlit_app import get_notification_actions, load_users # Carregar users para nomes de executor

    st.markdown("### Detalhes da Notificação")
    col_det1, col_det2 = st.columns(2)
    with col_det1:
        st.markdown("**📝 Evento Reportado Original**")
        st.write(f"**Título:** {notification.get('title', UI_TEXTS.text_na)}")
        st.write(f"**Local:** {notification.get('location', UI_TEXTS.text_na)}")
        occurrence_datetime_summary = format_date_time_summary(notification.get('occurrence_date'),
                                                               notification.get('occurrence_time'))
        st.write(f"**Data/Hora Ocorrência:** {occurrence_datetime_summary}")
        st.write(f"**Setor Notificante:** {notification.get('reporting_department', UI_TEXTS.text_na)}")
        if notification.get('immediate_actions_taken') and notification.get('immediate_action_description'):
            st.write(
                f"**Ações Imediatas Reportadas:** {notification.get('immediate_action_description', UI_TEXTS.text_na)[:100]}...")

    with col_det2:
        st.markdown("**⏱️ Informações de Gestão e Classificação**")
        classif = notification.get('classification') or {}
        st.write(f"**Classificação NNC:** {classif.get('nnc', UI_TEXTS.text_na)}")
        if classif.get('nivel_dano'): st.write(f"**Nível de Dano:** {classif.get('nivel_dano', UI_TEXTS.text_na)}")
        st.write(f"**Prioridade:** {classif.get('prioridade', UI_TEXTS.text_na)}")
        st.write(f"**Never Event:** {classif.get('never_event', UI_TEXTS.text_na)}")
        st.write(f"**Evento Sentinela:** {'Sim' if classif.get('is_sentinel_event') else 'Não'}")
        st.write(f"**Tipo Principal:** {classif.get('event_type_main', UI_TEXTS.text_na)}")
        sub_type_display_closed = ''
        if classif.get('event_type_sub'):
            if isinstance(classif['event_type_sub'], list):
                sub_type_display_closed = ', '.join(classif['event_type_sub'])
            else:
                sub_type_display_closed = str(classif['event_type_sub'])
        if sub_type_display_closed: st.write(f"**Especificação:** {sub_type_display_closed}")
        st.write(f"**Classificação OMS:** {', '.join(classif.get('oms', [UI_TEXTS.text_na]))}")
        st.write(f"**Classificado por:** {classif.get('classificador', UI_TEXTS.text_na)}")

        deadline_date_str = classif.get('deadline_date')
        if deadline_date_str:
            deadline_date_formatted = datetime.fromisoformat(deadline_date_str).strftime('%d/%m/%Y')
            completion_timestamp_str = (notification.get('conclusion') or {}).get('timestamp')
            deadline_status = get_deadline_status(deadline_date_str, completion_timestamp_str)
            st.markdown(
                f"**Prazo de Conclusão:** {deadline_date_formatted} (<span class='{deadline_status['class']}'>{deadline_status['text']}</span>)",
                unsafe_allow_html=True)
        else:
            st.write(f"**Prazo de Conclusão:** {UI_TEXTS.deadline_days_nan}")

    st.markdown("**📝 Descrição Completa do Evento**")
    st.info(notification.get('description', UI_TEXTS.text_na))
    if classif.get('notes'):
        st.markdown("**📋 Orientações / Observações do Classificador**")
        st.success(classif.get('notes', UI_TEXTS.text_na))

    if notification.get('actions'):
        st.markdown("#### ⚡ Histórico de Ações")
        for action in sorted(notification['actions'], key=lambda x: x.get('timestamp', '')):
            action_type = "🏁 CONCLUSÃO (Executor)" if action.get('final_action_by_executor') else "📝 AÇÃO Registrada"
            action_timestamp = action.get('timestamp', UI_TEXTS.text_na)
            if action_timestamp != UI_TEXTS.text_na:
                try:
                    action_timestamp = datetime.fromisoformat(action_timestamp).strftime('%d/%m/%Y %H:%M:%S')
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
                                        key=f"download_action_evidence_{notification['id']}_{unique_name}"
                                    )
                                else:
                                    st.write(f"Anexo: {original_name} (arquivo não encontrado ou corrompido)")
                    st.markdown(f"""</div>""", unsafe_allow_html=True)

            st.markdown("---")

    if notification.get('review_execution'):
        st.markdown("#### 🛠️ Revisão de Execução")
        review_exec = notification['review_execution']
        st.write(f"**Decisão:** {review_exec.get('decision', UI_TEXTS.text_na)}")
        st.write(f"**Revisado por:** {review_exec.get('reviewed_by', UI_TEXTS.text_na)}")
        st.write(f"**Observações:** {review_exec.get('notes', UI_TEXTS.text_na)}")
        if review_exec.get('rejection_reason'):
            st.write(f"**Motivo Rejeição:** {review_exec.get('rejection_reason', UI_TEXTS.text_na)}")
    if notification.get('approval'):
        st.markdown("#### ✅ Aprovação Final")
        approval_info = notification['approval']
        if user_username_logged_in and approval_info.get('approved_by') == user_username_logged_in:
            st.markdown(f"""
            <div style='background-color: #e6ffe6; padding: 10px; border-radius: 5px; border-left: 3px solid #4CAF50;'>
                <strong>Decisão:</strong> {approval_info.get('decision', UI_TEXTS.text_na)}
                <br>
                <strong>Aprovado por:</strong> VOCÊ ({approval_info.get('approved_by', UI_TEXTS.text_na)})
                <br>
                <strong>Observações:</strong> {approval_info.get('notes', UI_TEXTS.text_na)}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.write(f"**Decisão:** {approval_info.get('decision', UI_TEXTS.text_na)}")
            st.write(f"**Aprovado por:** {approval_info.get('approved_by', UI_TEXTS.text_na)}")
            st.write(f"**Observações:** {approval_info.get('notes', UI_TEXTS.text_na)}")

    if notification.get('rejection_classification'):
        st.markdown("#### ❌ Rejeição na Classificação Inicial")
        rej_classif = notification['rejection_classification']
        st.write(f"**Motivo:** {rej_classif.get('reason', UI_TEXTS.text_na)}")
        st.write(f"**Rejeitado por:** {rej_classif.get('classified_by', UI_TEXTS.text_na)}")

    if notification.get('rejection_approval'):
        st.markdown("#### ⛔ Reprovada na Aprovação")
        rej_appr = notification['rejection_approval']
        if user_username_logged_in and rej_appr.get('rejected_by') == user_username_logged_in:
            st.markdown(f"""
            <div style='background-color: #ffe6e6; padding: 10px; border-radius: 5px; border-left: 3px solid #f44336;'>
                <strong>Motivo:</strong> {rej_appr.get('reason', UI_TEXTS.text_na)}
                <br>
                <strong>Reprovado por:</strong> VOCÊ ({rej_appr.get('rejected_by', UI_TEXTS.text_na)})
            </div>
            """, unsafe_allow_html=True)
        else:
            st.write(f"**Motivo:** {rej_appr.get('reason', UI_TEXTS.text_na)}")
            st.write(f"**Reprovado por:** {rej_appr.get('rejected_by', UI_TEXTS.text_na)}")

    if notification.get('rejection_execution_review'):
        st.markdown("#### 🔄 Execução Rejeitada (Revisão do Classificador)")
        rej_exec_review = notification['rejection_execution_review']
        if user_username_logged_in and rej_exec_review.get('reviewed_by') == user_username_logged_in:
            st.markdown(f"""
            <div style='background-color: #ffe6e6; padding: 10px; border-radius: 5px; border-left: 3px solid #f44336;'>
                <strong>Motivo:</strong> {rej_exec_review.get('reason', UI_TEXTS.text_na)}
                <br>
                <strong>Rejeitado por:</strong> VOCÊ ({rej_exec_review.get('reviewed_by', UI_TEXTS.text_na)})
            </div>
            """, unsafe_allow_html=True)
        else:
            st.write(f"**Motivo:** {rej_exec_review.get('reason', UI_TEXTS.text_na)}")
            st.write(f"**Rejeitado por:** {rej_exec_review.get('reviewed_by', UI_TEXTS.text_na)}")

    if notification.get('attachments'):
        st.markdown("#### 📎 Anexos")
        for attach_info in notification['attachments']:
            unique_name_to_use = None
            original_name_to_use = None
            if isinstance(attach_info, dict) and 'unique_name' in attach_info and 'original_name' in attach_info:
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
                        key=f"download_closed_{notification['id']}_{unique_name_to_use}"
                    )
                else:
                    st.write(f"Anexo: {original_name_to_use} (arquivo não encontrado ou corrompido)")

    st.markdown("---")