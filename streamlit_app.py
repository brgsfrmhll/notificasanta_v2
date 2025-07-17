# streamlit_app.py

import streamlit as st
import json
import hashlib
import os
import sys # Importar sys (ainda pode ser útil para debug, mas não mais para path de script)
from datetime import datetime, date as dt_date_class, time as dt_time_class, timedelta
from typing import Dict, List, Optional, Any
import uuid
import pandas as pd
import time as time_module
import psycopg2
from psycopg2 import sql

# Importa as constantes e as funções utilitárias que serão compartilhadas
from constants import UI_TEXTS, FORM_DATA, DEADLINE_DAYS_MAPPING, DATA_DIR, ATTACHMENTS_DIR
from utils import _reset_form_state, _clear_execution_form_state, _clear_approval_form_state, get_deadline_status, format_date_time_summary, display_notification_full_details, save_uploaded_file_to_disk, get_attachment_data

# --- Configuração do Banco de Dados ---
DB_CONFIG = {
    "host": "localhost",
    "database": "notificasanta",
    "user": "streamlit",
    "password": "6105/*"
}

@st.cache_resource(ttl=3600) # Cache para a conexão do banco de dados (1 hora). O teste de vida abaixo a mantém fresca.
def get_db_connection():
    """
    Estabelece e retorna uma conexão com o banco de dados PostgreSQL.
    Adiciona um teste de vida para garantir que a conexão não esteja fechada.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        # Teste de vida da conexão: executa uma consulta simples.
        # Se a conexão estiver fechada ou inativa, isso gerará uma exceção.
        with conn.cursor() as cursor: # Use 'with' para garantir que o cursor seja fechado
            cursor.execute("SELECT 1")
        conn.commit() # Confirma a transação dummy para liberar o cursor
        return conn
    except psycopg2.Error as e:
        # Se a conexão falhou, limpa o cache para que uma nova seja tentada na próxima vez
        get_db_connection.clear()
        # Levantar uma exceção customizada para ser capturada e tratada de forma específica.
        raise ConnectionRefusedError(f"Falha ao conectar ou verificar a validade do banco de dados: {e}")

# --- Funções de Persistência e Banco de Dados (com caching e sem fechar conexões) ---

@st.cache_data(ttl=60) # Cache para usuários (1 minuto)
def load_users() -> List[Dict]:
    """Carrega dados de usuário do banco de dados."""
    conn = None
    try:
        conn = get_db_connection() # Obtém a conexão cacheada
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, password_hash, name, email, roles, active, created_at FROM users ORDER BY name")
        users_raw = cur.fetchall()
        cur.close()
        return [
            {
                "id": u[0],
                "username": u[1],
                "password": u[2],
                "name": u[3],
                "email": u[4],
                "roles": u[5],
                "active": u[6],
                "created_at": u[7].isoformat() if u[7] else None
            }
            for u in users_raw
        ]
    except psycopg2.Error as e:
        st.error(f"Erro ao carregar usuários: {e}")
        return []
    finally:
        pass # Não fecha a conexão, ela é gerenciada por st.cache_resource

def create_user(data: Dict) -> Optional[Dict]:
    """Cria um novo registro de usuário no banco de dados e invalida o cache."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE username = %s", (data.get('username', '').lower(),))
        if cur.fetchone():
            return None

        user_password_hash = hash_password(data.get('password', '').strip())
        cur.execute("""
            INSERT INTO users (username, password_hash, name, email, roles, active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, username, password_hash, name, email, roles, active, created_at
        """, (
            data.get('username', '').strip(),
            user_password_hash,
            data.get('name', '').strip(),
            data.get('email', '').strip(),
            data.get('roles', []),
            True,
            datetime.now().isoformat()
        ))
        conn.commit()
        new_user_raw = cur.fetchone()
        cur.close()
        load_users.clear() # Invalida o cache de usuários após a criação
        if new_user_raw:
            return {
                "id": new_user_raw[0],
                "username": new_user_raw[1],
                "password": new_user_raw[2],
                "name": new_user_raw[3],
                "email": new_user_raw[4],
                "roles": new_user_raw[5],
                "active": new_user_raw[6],
                "created_at": new_user_raw[7].isoformat()
            }
        return None
    except psycopg2.Error as e:
        st.error(f"Erro ao criar usuário: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        pass # Não fecha a conexão

def update_user(user_id: int, updates: Dict) -> Optional[Dict]:
    """Atualiza um registro de usuário existente no banco de dados e invalida o cache."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        set_clauses = []
        values = []
        for key, value in updates.items():
            if key == 'password' and value:
                set_clauses.append(sql.Identifier('password_hash') + sql.SQL(' = %s'))
                values.append(hash_password(value))
            elif key == 'roles':
                set_clauses.append(sql.Identifier(key) + sql.SQL(' = %s'))
                values.append(list(value))
            elif key not in ['id', 'username', 'created_at']:
                set_clauses.append(sql.Identifier(key) + sql.SQL(' = %s'))
                values.append(value)

        if not set_clauses:
            return None

        query = sql.SQL(
            "UPDATE users SET {} WHERE id = %s RETURNING id, username, password_hash, name, email, roles, active, created_at").format(
            sql.SQL(', ').join(set_clauses)
        )
        values.append(user_id)

        cur.execute(query, values)
        conn.commit()
        updated_user_raw = cur.fetchone()
        cur.close()
        load_users.clear() # Invalida o cache de usuários após a atualização
        if updated_user_raw:
            return {
                "id": updated_user_raw[0],
                "username": updated_user_raw[1],
                "password": updated_user_raw[2],
                "name": updated_user_raw[3],
                "email": updated_user_raw[4],
                "roles": updated_user_raw[5],
                "active": updated_user_raw[6],
                "created_at": updated_user_raw[7].isoformat()
            }
        return None
    except psycopg2.Error as e:
        st.error(f"Erro ao atualizar usuário: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        pass # Não fecha a conexão

@st.cache_data(ttl=5) # Cache para notificações (5 segundos)
def load_notifications() -> List[Dict]:
    """Carrega dados de notificação do banco de dados, incluindo dados relacionados."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                id, title, description, location, occurrence_date, occurrence_time,
                reporting_department, reporting_department_complement, notified_department,
                notified_department_complement, event_shift, immediate_actions_taken,
                immediate_action_description, patient_involved, patient_id, patient_outcome_obito,
                additional_notes, status, created_at,
                classification, rejection_classification, review_execution, approval,
                rejection_approval, rejection_execution_review, conclusion,
                executors, approver
            FROM notifications ORDER BY created_at DESC
        """)
        notifications_raw = cur.fetchall()

        column_names = [desc[0] for desc in cur.description]
        notifications = []
        for row in notifications_raw:
            notification = dict(zip(column_names, row))
            if notification.get('occurrence_date'):
                notification['occurrence_date'] = notification['occurrence_date'].isoformat()
            if notification.get('occurrence_time'):
                notification['occurrence_time'] = notification['occurrence_time'].isoformat()
            if notification.get('created_at'):
                notification['created_at'] = notification['created_at'].isoformat()

            # Passa a conexão e cursor para as funções auxiliares usarem a mesma transação
            notification['attachments'] = get_notification_attachments(notification['id'], conn, cur)
            notification['history'] = get_notification_history(notification['id'], conn, cur)
            notification['actions'] = get_notification_actions(notification['id'], conn, cur)

            notifications.append(notification)
        cur.close()
        return notifications
    except psycopg2.Error as e:
        st.error(f"Erro ao carregar notificações: {e}")
        return []
    finally:
        pass # Não fecha a conexão

def create_notification(data: Dict, uploaded_files: Optional[List[Any]] = None) -> Dict:
    """
    Cria um novo registro de notificação no banco de dados e seus anexos iniciais,
    invalidando o cache de notificações.
    """
    conn = get_db_connection()
    notification_id = None
    try:
        cur = conn.cursor()

        occurrence_date_iso = data.get('occurrence_date').isoformat() if isinstance(data.get('occurrence_date'), dt_date_class) else None
        occurrence_time_str = data.get('occurrence_time').isoformat() if isinstance(data.get('occurrence_time'), dt_time_class) else None

        cur.execute("""
            INSERT INTO notifications (
                title, description, location, occurrence_date, occurrence_time,
                reporting_department, reporting_department_complement, notified_department,
                notified_department_complement, event_shift, immediate_actions_taken,
                immediate_action_description, patient_involved, patient_id, patient_outcome_obito,
                additional_notes, status, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data.get('title', '').strip(),
            data.get('description', '').strip(),
            data.get('location', '').strip(),
            occurrence_date_iso,
            occurrence_time_str,
            data.get('reporting_department', '').strip(),
            data.get('reporting_department_complement', '').strip(),
            data.get('notified_department', '').strip(),
            data.get('notified_department_complement', '').strip(),
            data.get('event_shift', UI_TEXTS.selectbox_default_event_shift),
            data.get('immediate_actions_taken') == "Sim",
            data.get('immediate_action_description', '').strip() if data.get('immediate_actions_taken') == "Sim" else None,
            data.get('patient_involved') == "Sim",
            data.get('patient_id', '').strip() if data.get('patient_involved') == "Sim" else None,
            (True if data.get('patient_outcome_obito') == "Sim" else False if data.get('patient_outcome_obito') == "Não" else None) if data.get('patient_involved') == "Sim" else None,
            data.get('additional_notes', '').strip(),
            "pendente_classificacao",
            datetime.now().isoformat()
        ))
        notification_id = cur.fetchone()[0]

        if uploaded_files:
            for file in uploaded_files:
                saved_file_info = save_uploaded_file_to_disk(file, notification_id)
                if saved_file_info:
                    cur.execute("""
                        INSERT INTO notification_attachments (notification_id, unique_name, original_name)
                        VALUES (%s, %s, %s)
                    """, (notification_id, saved_file_info['unique_name'], saved_file_info['original_name']))

        add_history_entry(
            notification_id,
            "Notificação criada",
            "Sistema (Formulário Público)",
            f"Notificação enviada para classificação. Título: {data.get('title', 'Sem título')[:100]}..." if len(
                data.get('title', '')) > 100 else f"Notificação enviada para classificação. Título: {data.get('title', 'Sem título')}",
            conn=conn,
            cursor=cur
        )

        conn.commit()
        cur.close()
        load_notifications.clear() # Invalida o cache de notificações após a criação

        # Retorna a notificação completa para consistência (recarrega do cache)
        all_notifications_cached = load_notifications()
        created_notification = next((n for n in all_notifications_cached if n['id'] == notification_id), None)
        return created_notification

    except psycopg2.Error as e:
        st.error(f"Erro ao criar notificação: {e}")
        if conn:
            conn.rollback()
        return {}
    finally:
        pass # Não fecha a conexão

def update_notification(notification_id: int, updates: Dict):
    """
    Atualiza um registro de notificação, invalidando o cache de notificações.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        set_clauses = []
        values = []

        column_mapping = {
            'immediate_actions_taken': lambda x: True if x == "Sim" else False if x == "Não" else None,
            'patient_involved': lambda x: True if x == "Sim" else False if x == "Não" else None,
            'patient_outcome_obito': lambda x: (True if x == "Sim" else False if x == "Não" else None),
            'occurrence_date': lambda x: x.isoformat() if isinstance(x, dt_date_class) else x,
            'occurrence_time': lambda x: x.isoformat() if isinstance(x, dt_time_class) else x,
            'classification': lambda x: json.dumps(x) if x is not None else None,
            'rejection_classification': lambda x: json.dumps(x) if x is not None else None,
            'review_execution': lambda x: json.dumps(x) if x is not None else None,
            'approval': lambda x: json.dumps(x) if x is not None else None,
            'rejection_approval': lambda x: json.dumps(x) if x is not None else None,
            'rejection_execution_review': lambda x: json.dumps(x) if x is not None else None,
            'conclusion': lambda x: json.dumps(x) if x is not None else None,
            'executors': lambda x: x # psycopg2 lida bem com arrays Python para INTEGER[]
        }

        for key, value in updates.items():
            if key not in ['id', 'created_at', 'attachments', 'actions', 'history']:
                if key in column_mapping:
                    set_clauses.append(sql.Identifier(key) + sql.SQL(' = %s'))
                    values.append(column_mapping[key](value))
                else:
                    set_clauses.append(sql.Identifier(key) + sql.SQL(' = %s'))
                    values.append(value)

        if not set_clauses:
            return None

        query = sql.SQL(
            "UPDATE notifications SET {} WHERE id = %s").format(
            sql.SQL(', ').join(set_clauses)
        )
        values.append(notification_id)

        cur.execute(query, values)
        conn.commit()
        cur.close()
        load_notifications.clear() # Invalida o cache de notificações após a atualização

        # Retorna a notificação completa para consistência (recarrega do cache)
        all_notifications_cached = load_notifications()
        updated_notification = next((n for n in all_notifications_cached if n['id'] == notification_id), None)
        return updated_notification

    except psycopg2.Error as e:
        st.error(f"Erro ao atualizar notificação: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        pass # Não fecha a conexão

# Funções auxiliares para buscar dados relacionados (usadas por load_notifications)
def get_notification_attachments(notification_id: int, conn=None, cur=None) -> List[Dict]:
    """Busca anexos para uma notificação específica. Pode usar conexão e cursor existentes."""
    local_conn = conn
    local_cur = cur
    try:
        if not (local_conn and local_cur): # Se não recebeu conn/cur, tenta pegar do cache
            local_conn = get_db_connection()
            local_cur = local_conn.cursor()

        local_cur.execute("SELECT unique_name, original_name FROM notification_attachments WHERE notification_id = %s",
                          (notification_id,))
        attachments_raw = local_cur.fetchall()
        return [{"unique_name": att[0], "original_name": att[1]} for att in attachments_raw]
    except psycopg2.Error as e:
        st.error(f"Erro ao carregar anexos da notificação {notification_id}: {e}")
        return []
    finally:
        # Se a conexão e cursor foram criados localmente, feche-os.
        # Se foram passados como argumento, não feche, pois são gerenciados pelo chamador.
        if not (conn and cur) and local_cur: local_cur.close()
        if not (conn and cur) and local_conn and local_conn is not conn: local_conn.close()


def get_notification_history(notification_id: int, conn=None, cur=None) -> List[Dict]:
    """Busca entradas de histórico para uma notificação. Pode usar conexão e cursor existentes."""
    local_conn = conn
    local_cur = cur
    try:
        if not (local_conn and local_cur):
            local_conn = get_db_connection()
            local_cur = local_conn.cursor()

        local_cur.execute(
            "SELECT action_type, performed_by, action_timestamp, details FROM notification_history WHERE notification_id = %s ORDER BY action_timestamp",
            (notification_id,))
        history_raw = local_cur.fetchall()
        return [
            {
                "action": h[0],
                "user": h[1],
                "timestamp": h[2].isoformat() if h[2] else None,
                "details": h[3]
            }
            for h in history_raw
        ]
    except psycopg2.Error as e:
        st.error(f"Erro ao carregar histórico da notificação {notification_id}: {e}")
        return []
    finally:
        if not (conn and cur) and local_cur: local_cur.close()
        if not (conn and cur) and local_conn and local_conn is not conn: local_conn.close()

def get_notification_actions(notification_id: int, conn=None, cur=None) -> List[Dict]:
    """Busca ações de executores para uma notificação. Pode usar conexão e cursor existentes."""
    local_conn = conn
    local_cur = cur
    try:
        if not (local_conn and local_cur):
            local_conn = get_db_connection()
            local_cur = local_conn.cursor()

        local_cur.execute(
            "SELECT executor_id, executor_name, description, action_timestamp, final_action_by_executor, evidence_description, evidence_attachments FROM notification_actions WHERE notification_id = %s ORDER BY action_timestamp",
            (notification_id,))
        actions_raw = local_cur.fetchall()
        return [
            {
                "executor_id": a[0],
                "executor_name": a[1],
                "description": a[2],
                "timestamp": a[3].isoformat() if a[3] else None,
                "final_action_by_executor": a[4],
                "evidence_description": a[5],
                "evidence_attachments": a[6]
            }
            for a in actions_raw
        ]
    except psycopg2.Error as e:
        st.error(f"Erro ao carregar ações da notificação {notification_id}: {e}")
        return []
    finally:
        if not (conn and cur) and local_cur: local_cur.close()
        if not (conn and cur) and local_conn and local_conn is not conn: local_conn.close()


def add_history_entry(notification_id: int, action: str, user: str, details: str = "", conn=None, cursor=None):
    """
    Adiciona uma entrada ao histórico de uma notificação, invalidando o cache de notificações.
    """
    local_conn = conn
    local_cur = cursor
    try:
        if not (local_conn and local_cur):
            local_conn = get_db_connection()
            local_cur = local_conn.cursor()

        local_cur.execute("""
            INSERT INTO notification_history (notification_id, action_type, performed_by, action_timestamp, details)
            VALUES (%s, %s, %s, %s, %s)
        """, (notification_id, action, user, datetime.now().isoformat(), details))

        if not (conn and cursor):
            local_conn.commit()
        load_notifications.clear() # Invalida o cache de notificações
        return True
    except psycopg2.Error as e:
        st.error(f"Erro ao adicionar entrada de histórico para notificação {notification_id}: {e}")
        if local_conn and not local_conn.closed and not (conn and cursor):
            local_conn.rollback()
        return False
    finally:
        if not (conn and cur) and local_cur: local_cur.close()
        if not (conn and cur) and local_conn and local_conn is not conn: local_conn.close()

def add_notification_action(notification_id: int, action_data: Dict, conn=None, cur=None):
    """
    Adiciona uma ação de executor a uma notificação, invalidando o cache de notificações.
    """
    local_conn = conn
    local_cur = cur
    try:
        if not (local_conn and local_cur):
            local_conn = get_db_connection()
            local_cur = local_conn.cursor()

        local_cur.execute("""
            INSERT INTO notification_actions (
                notification_id, executor_id, executor_name, description, action_timestamp,
                final_action_by_executor, evidence_description, evidence_attachments
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            notification_id,
            action_data.get('executor_id'),
            action_data.get('executor_name'),
            action_data.get('description'),
            action_data.get('timestamp'),
            action_data.get('final_action_by_executor'),
            action_data.get('evidence_description'),
            json.dumps(action_data.get('evidence_attachments')) if action_data.get('evidence_attachments') else None
        ))
        if not (conn and cur):
            local_conn.commit()
        load_notifications.clear() # Invalida o cache de notificações
        return True
    except psycopg2.Error as e:
        st.error(f"Erro ao adicionar ação para notificação {notification_id}: {e}")
        if local_conn and not local_conn.closed and not (conn and cursor):
            local_conn.rollback()
        return False
    finally:
        if not (conn and cur) and local_cur: local_cur.close()
        if not (conn and cur) and local_conn and local_conn is not conn: local_conn.close()

# --- Funções de Autenticação e Autorização ---

def hash_password(password: str) -> str:
    """Faz o hash de uma senha usando SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Autentica um usuário com base no nome de usuário e senha."""
    users = load_users()
    hashed_password = hash_password(password)
    for user in users:
        if (user.get('username', '').lower() == username.lower() and
                user.get('password') == hashed_password and
                user.get('active', True)):
            return user
    return None

def logout_user():
    """Desloga o usuário atual."""
    st.session_state.authenticated = False
    st.session_state.user = None
    _reset_form_state()
    if 'initial_classification_state' in st.session_state: st.session_state.pop('initial_classification_state')
    if 'review_classification_state' in st.session_state: st.session_state.pop('review_classification_state')
    if 'current_initial_classification_id' in st.session_state: st.session_state.pop('current_initial_classification_id')
    if 'current_review_classification_id' in st.session_state: st.session_state.pop('current_review_classification_id')
    if 'approval_form_state' in st.session_state: st.session_state.pop('approval_form_state')
    
    # Resetar a flag de redirecionamento para que na próxima vez o user seja redirecionado para a home
    st.session_state.redirect_done = False 
    st.success("Deslogado com sucesso!")
    # Redireciona para a página de criação de notificação após o logout
    st.switch_page("pages/1_Nova_Notificacao.py")


def check_permission(required_role: str) -> bool:
    """Verifica se o usuário logado possui a função necessária ou é um admin."""
    if not st.session_state.authenticated or st.session_state.user is None:
        return False
    user_roles = st.session_state.user.get('roles', [])
    return required_role in user_roles or 'admin' in user_roles

def get_users_by_role(role: str) -> List[Dict]:
    """Retorna usuários ativos com uma função específica."""
    users = load_users()
    # Adicionando explicitamente a verificação de 'active' = True, embora load_users já faça isso
    return [user for user in users if role in user.get('roles', []) and user.get('active', True)]

# --- Configuração do Streamlit e CSS Customizado ---
st.set_page_config(
    page_title="NotificaSanta",
    page_icon="favicon/logo.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# NOVO CSS: Oculta o menu de navegação nativo do Streamlit na sidebar
st.markdown(r"""
<style>
    /* Esconde o menu de navegação nativo gerado pelo Streamlit */
    div[data-testid="stSidebarNav"] {
        display: none !important;
    }

    /* Esconde botões e decorações padrão do Streamlit */
    button[data-testid="stDeployButton"],
    .stDeployButton,
    footer,
    #stDecoration,
    .stAppDeployButton {
        display: none !important;
    }

    /* Ajuste de margem superior para o container principal do Streamlit */
    .reportview-container {
        margin-top: -2em;
    }

    /* Garante que a Sidebar fique ACIMA de outros elementos fixos, se houver */
    div[data-testid="stSidebar"] {
        z-index: 9999 !important; /* Prioridade de empilhamento muito alta */
    }

    /* Adjust Streamlit's default margins for sidebar content */
    [data-testid="stSidebarContent"] {
        padding-top: 10px;
    }

    /* Logo - Reduced size and moved up */
    div[data-testid="stSidebar"] img {
        transform: scale(0.6);
        transform-origin: top center;
        margin-top: -80px;
        margin-bottom: -20px;
    }

    /* Estilo do cabeçalho principal da aplicação */
    .main-header {
        text-align: center;
        color: #2E86AB;
        margin-bottom: 30px;
    }

    /* Novo Estilo para o Título Principal da Sidebar */
    [data-testid="stSidebarContent"] .sidebar-main-title {
        text-align: center !important;
        color: #00008B !important;
        font-size: 1.76em !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2) !important;
        margin-top: -30px !important;
    }

    /* Novo Estilo para o Subtítulo da Sidebar */
    [data-testid="stSidebarContent"] .sidebar-subtitle {
        text-align: center !important;
        color: #333 !important;
        font-size: 0.72em !important;
        font-weight: 400 !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        margin-top: -30px !important;
        margin-bottom: 5px !important;
    }

    /* Estilo geral para cartões de notificação */
    .notification-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        background-color: #f9f9f9;
        color: #2E86AB;
    }

    /* Cores e destaque para diferentes status de notificação */
    .status-pendente_classificacao { color: #ff9800; font-weight: bold; }
    .status-classificada { color: #2196f3; font-weight: bold; }
    .status-em_execucao { color: #9c27b0; font-weight: bold; }
    .status-aguardando_classificador { color: #ff5722; font-weight: bold; }
    .status-revisao_classificador_execucao { color: #8BC34A; font-weight: bold; }
    .status-aguardando_aprovacao { color: #ffc107; font-weight: bold; }
    .status-aprovada { color: #4caf50; font-weight: bold; }
    .status-concluida { color: #4caf50; font-weight: bold; }
    .status-rejeitada { color: #f44336; font-weight: bold; }
    .status-reprovada { color: #f44336; font-weight: bold; }
    /* Estilo para o conteúdo da barra lateral */
    .sidebar .sidebar-content {
        background-color: #f0f2f6;
    }

    /* Estilo para a caixa de informações do usuário na sidebar */
    .user-info {
        background-color: #e8f4fd;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 20px;
    }

    /* Estilo para seções de formulário */
    .form-section {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 4px solid #2E86AB;
    }

    /* Estilo para campos condicionais em formulários (ex: detalhes de ação imediata) */
    .conditional-field {
        background-color: #fff3cd;
        padding: 10px;
        border-radius: 5px;
        border-left: 3px solid #ffc107;
        margin: 10px 0;
    }

    /* Estilo para campos obrigatórios */
    .required-field {
        color: #dc3545;
        font-weight: bold;
    }

    /* Cores específicas para botões "Sim" e "Não" selecionados */
    div.stButton > button[data-testid='stButton'][data-key*='_sim_step'][data-selected='true'] {
        border-color: #4caf50;
        color: #4caf50;
    }
    div.stButton > button[data-testid='stButton'][data-key*='_nao_step'][data-selected='true'] {
        border-color: #f44336;
        color: #f44336;
    }

    /* Negrito geral para labels dentro de blocos horizontais do Streamlit */
    div[data-testid="stHorizontalBlock"] div[data-testid^="st"] label p {
        font-weight: bold;
    }

    /* Estilo para cartões de métricas no dashboard */
    .metric-card {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }

    .metric-card h4 {
        margin-top: 0;
        color: #333;
    }

    .metric-card p {
        font-size: 1.8em;
        font-weight: bold;
        color: #2E86AB;
        margin-bottom: 0;
    }

    /* Estilo para o rodapé da sidebar */
    .sidebar-footer {
        text-align: center;
        margin-top: 20px;
        padding: 10px;
        color: #888;
        font-size: 0.75em;
        border-top: 1px solid #eee;
    }

    /* Remove padding do container principal, pois o rodapé fixo foi removido */
    div[data-testid="stAppViewContainer"] {
        padding-bottom: 0px;
    }

    /* Estilos para o fundo do cartão de notificação com base no status do prazo */
    .notification-card.card-prazo-dentro {
        background-color: #e6ffe6;
        border: 1px solid #4CAF50;
    }

    /* Estilos para o fundo do cartão de notificação com base no status do prazo */
    .notification-card.card-prazo-fora {
        background-color: #ffe6e6;
        border: 1px solid #F44336;
    }

    /* Estilos para status de prazo */
    .deadline-ontrack { color: #4CAF50; font-weight: bold; }
    .deadline-duesoon { color: #FFC107; font-weight: bold; }

    /* Estilo para entrada de ação individual */
    .action-entry-card {
        border: 1px solid #cceeff;
        border-left: 5px solid #2E86AB;
        border-radius: 8px;
        padding: 12px;
        margin-top: 10px;
        margin-bottom: 10px;
        background-color: #f0f8ff;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }

    .action-entry-card strong {
        color: #2E86AB;
    }

    .action-entry-card em {
        color: #555;
    }

    /* Estilo para "minhas" ações na execução */
    .my-action-entry-card {
        border: 1px solid #d4edda;
        border-left: 5px solid #28a745;
        border-radius: 8px;
        padding: 12px;
        margin-top: 10px;
        margin-bottom: 10px;
        background-color: #eaf7ed;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }

    .my-action-entry-card strong {
        color: #28a745;
    }

    /* Estilo para a seção de evidências dentro de uma ação */
    .evidence-section {
        background-color: #ffffff;
        border-top: 1px dashed #cccccc;
        margin-top: 10px;
        padding-top: 10px;
    }

    .evidence-section h6 {
        color: #666;
        margin-bottom: 5px;
    }

    options = {
        'show_menu': False }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

</style>
""", unsafe_allow_html=True)

# --- Funções de Renderização da Interface (UI) da Sidebar ---

def show_sidebar():
    """Renderiza a barra lateral com navegação e informações do usuário/login."""
    with st.sidebar:
        st.image("logo.png", use_container_width=True)
        st.markdown("<h2 class='sidebar-main-title'>Portal de Notificações</h2>", unsafe_allow_html=True)
        st.markdown("<h3 class='sidebar-subtitle'>Santa Casa de Poços de Caldas</h3>", unsafe_allow_html=True)
        st.markdown("---")

        # Verifica se o usuário está logado
        # Esta verificação é segura agora, pois st.session_state.authenticated é inicializado antes de show_sidebar ser chamado.
        if st.session_state.authenticated and st.session_state.user:
            st.markdown(f"""
            <div class="user-info">
                <strong>👤 {st.session_state.user.get('name', 'Usuário')}</strong><br>
                <small>{st.session_state.user.get('username', UI_TEXTS.text_na)}</small><br>
                <small>Funções: {', '.join(st.session_state.user.get('roles', [])) or 'Nenhuma'}</small>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("### 📋 Menu Principal")

            # --- BOTÕES DE NAVEGAÇÃO CUSTOMIZADOS ---
            user_roles = st.session_state.user.get('roles', [])

            # Botão "Nova Notificação" (geralmente acessível a todos)
            if st.button("📝 Nova Notificação", key="nav_create_notif", use_container_width=True):
                st.switch_page("pages/1_Nova_Notificacao.py")

            # Botão "Dashboard" (acessível para Classificador e Admin)
            if 'classificador' in user_roles or 'admin' in user_roles:
                if st.button("📊 Dashboard de Notificações", key="nav_dashboard", use_container_width=True):
                    st.switch_page("pages/2_Dashboard.py")

            # Botão "Classificação/Revisão" (acessível para Classificador e Admin)
            if 'classificador' in user_roles or 'admin' in user_roles:
                if st.button("🔍 Classificação/Revisão", key="nav_classification", use_container_width=True):
                    st.switch_page("pages/3_Classificacao_e_Revisao.py")

            # Botão "Execução" (acessível para Executor e Admin)
            if 'executor' in user_roles or 'admin' in user_roles:
                if st.button("⚡ Execução", key="nav_execution", use_container_width=True):
                    st.switch_page("pages/4_Execucao.py")

            # Botão "Aprovação" (acessível para Aprovador e Admin)
            if 'aprovador' in user_roles or 'admin' in user_roles:
                if st.button("✅ Aprovação", key="nav_approval", use_container_width=True):
                    st.switch_page("pages/5_Aprovacao.py")

            # Botão "Administração" (acessível apenas para Admin)
            if 'admin' in user_roles:
                if st.button("⚙️ Administração", key="nav_admin", use_container_width=True):
                    st.switch_page("pages/6_Administracao.py")
            # --- FIM DOS BOTÕES DE NAVEGAÇÃO CUSTOMIZADOS ---

            st.markdown("---")
            if st.button("🚪 Sair", key="nav_logout", use_container_width=True):
                logout_user() # Esta função já chama st.switch_page

        else:
            st.markdown("### 🔐 Login do Operador")
            with st.form("sidebar_login_form"):
                username = st.text_input("Usuário", key="sidebar_username_form")
                password = st.text_input("Senha", type="password", key="sidebar_password_form")
                if st.form_submit_button("🔑 Entrar", use_container_width=True):
                    user = authenticate_user(st.session_state.sidebar_username_form,
                                             st.session_state.sidebar_password_form)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.success(f"Login realizado com sucesso! Bem-vindo, {user.get('name', 'Usuário')}.")
                        st.session_state.pop('sidebar_username_form', None)
                        st.session_state.pop('sidebar_password_form', None)
                        
                        # Limpa o flag de redirecionamento para que o redirecionamento pós-login aconteça
                        st.session_state.redirect_done = False 

                        # Após o login, redireciona para a página padrão para usuários logados
                        if 'classificador' in user.get('roles', []) or 'admin' in user.get('roles', []):
                            st.switch_page("pages/3_Classificacao_e_Revisao.py")
                        else:
                            st.switch_page("pages/1_Nova_Notificacao.py") # Página padrão para outros usuários
                    else:
                        st.error("Usuário ou senha inválidos!")
            st.markdown("---")

        st.markdown("""
        <div class="sidebar-footer">
            NotificaSanta v1.1.2<br>
            &copy; 2025 Todos os direitos reservados
        </div>
        """, unsafe_allow_html=True)

# --- Inicialização da Aplicação ---
def init_database():
    """Garante que os diretórios de dados e arquivos iniciais existam e cria tabelas no DB."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(ATTACHMENTS_DIR):
        os.makedirs(ATTACHMENTS_DIR)

    conn = None
    try:
        conn = get_db_connection() # Esta função agora verifica a validade da conexão
        cur = conn.cursor()

        # Criar tabelas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                roles TEXT[] NOT NULL DEFAULT '{}',
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);

            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                title VARCHAR(500) NOT NULL,
                description TEXT NOT NULL,
                location VARCHAR(255),
                occurrence_date DATE,
                occurrence_time TIME,
                reporting_department VARCHAR(255),
                reporting_department_complement VARCHAR(255),
                notified_department VARCHAR(255),
                notified_department_complement VARCHAR(255),
                event_shift VARCHAR(50),
                immediate_actions_taken BOOLEAN,
                immediate_action_description TEXT,
                patient_involved BOOLEAN,
                patient_id VARCHAR(255),
                patient_outcome_obito BOOLEAN,
                additional_notes TEXT,
                status VARCHAR(50) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

                classification JSONB,
                rejection_classification JSONB,
                review_execution JSONB,
                approval JSONB,
                rejection_approval JSONB,
                rejection_execution_review JSONB,
                conclusion JSONB,

                executors INTEGER[] DEFAULT '{}',
                approver INTEGER REFERENCES users(id),

                search_vector TSVECTOR
            );
            CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications (status);
            CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications (created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_notifications_approver ON notifications (approver);
            CREATE INDEX IF NOT EXISTS idx_notifications_classification_gin ON notifications USING GIN (classification);
            CREATE INDEX IF NOT EXISTS idx_notifications_executors_gin ON notifications USING GIN (executors);
            CREATE INDEX IF NOT EXISTS idx_notifications_search_vector ON notifications USING GIN (search_vector);

            CREATE OR REPLACE FUNCTION update_notification_search_vector() RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_vector := to_tsvector('portuguese',
                    COALESCE(NEW.title, '') || ' ' ||
                    COALESCE(NEW.description, '') || ' ' ||
                    COALESCE(NEW.location, '') || ' ' ||
                    COALESCE(NEW.reporting_department, '') || ' ' ||
                    COALESCE(NEW.patient_id, '')
                );
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trg_notifications_search_vector ON notifications;
            CREATE TRIGGER trg_notifications_search_vector
            BEFORE INSERT OR UPDATE ON notifications
            FOR EACH ROW EXECUTE FUNCTION update_notification_search_vector();

            CREATE TABLE IF NOT EXISTS notification_attachments (
                id SERIAL PRIMARY KEY,
                notification_id INTEGER NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
                unique_name VARCHAR(255) NOT NULL,
                original_name VARCHAR(255) NOT NULL,
                uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_attachments_notification_id ON notification_attachments (notification_id);

            CREATE TABLE IF NOT EXISTS notification_history (
                id SERIAL PRIMARY KEY,
                notification_id INTEGER NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
                action_type VARCHAR(255) NOT NULL,
                performed_by VARCHAR(255),
                action_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                details TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_history_notification_id ON notification_history (notification_id);
            CREATE INDEX IF NOT EXISTS idx_history_timestamp ON notification_history (action_timestamp);

            CREATE TABLE IF NOT EXISTS notification_actions (
                id SERIAL PRIMARY KEY,
                notification_id INTEGER NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
                executor_id INTEGER REFERENCES users(id),
                executor_name VARCHAR(255),
                description TEXT NOT NULL,
                action_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                final_action_by_executor BOOLEAN NOT NULL DEFAULT FALSE,
                evidence_description TEXT,
                evidence_attachments JSONB
            );
            CREATE INDEX IF NOT EXISTS idx_actions_notification_id ON notification_actions (notification_id);
            CREATE INDEX IF NOT EXISTS idx_actions_executor_id ON notification_actions (executor_id);
            CREATE INDEX IF NOT EXISTS idx_actions_timestamp ON notification_actions (action_timestamp);
        """)

        # Verifica se o usuário 'admin' padrão existe, se não, cria
        # Acesso direto a conn.cursor() já garante que a conexão está ativa devido ao get_db_connection()
        cur_check_admin = conn.cursor()
        try:
            cur_check_admin.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
            if cur_check_admin.fetchone()[0] == 0:
                admin_password_hash = hash_password("6105/*")
                cur_check_admin.execute("""
                    INSERT INTO users (username, password_hash, name, email, roles, active)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, ('admin', admin_password_hash, 'Administrador', 'admin@hospital.com',
                      ['admin', 'classificador', 'executor', 'aprovador'], True))
                conn.commit() # Commit no conn principal
                st.toast("Usuário administrador padrão criado no banco de dados!")
        except psycopg2.Error as e:
            st.error(f"Erro ao verificar/criar usuário admin: {e}")
            if conn:
                conn.rollback()
            st.stop()
        finally:
            if cur_check_admin:
                cur_check_admin.close()

    except psycopg2.Error as e:
        st.error(f"Erro ao inicializar o banco de dados: {e}")
        # Re-lançar a exceção para que main_app_logic a capture e chame st.stop()
        raise
    finally:
        pass # CRUCIAL: NÃO FECHAR A CONEXÃO AQUI! Ela é gerenciada pelo @st.cache_resource.

# Main execution logic for the app
def main_app_logic():
    # 1. Inicializa st.session_state para autenticação e outros dados
    # ESTE BLOCO DEVE VIR PRIMEIRO PARA GARANTIR QUE AS CHAVES EXISTAM ANTES DE QUALQUER ACESSO.
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    if 'user' not in st.session_state: st.session_state.user = None
    if 'initial_classification_state' not in st.session_state: st.session_state.initial_classification_state = {}
    if 'review_classification_state' not in st.session_state: st.session_state.review_classification_state = {}
    if 'current_initial_classification_id' not in st.session_state: st.session_state.current_initial_classification_id = None
    if 'current_review_classification_id' not in st.session_state: st.session_state.current_review_classification_id = None
    if 'approval_form_state' not in st.session_state: st.session_state.approval_form_state = {}
    if 'redirect_done' not in st.session_state: st.session_state.redirect_done = False
    
    # 2. Sempre exibir a sidebar primeiro para garantir que a UI básica seja desenhada.
    show_sidebar()

    # 3. Inicializar o banco de dados e tratar erros críticos.
    #    Se init_database falhar, exibe uma mensagem de erro na UI já desenhada e para.
    try:
        init_database()
    except Exception as e: # Captura exceções de init_database e get_db_connection
        st.error(f"Um erro crítico ocorreu durante a inicialização da aplicação: {e}")
        st.info("Por favor, verifique a conexão com o banco de dados e tente novamente.")
        st.stop() # Para a execução após exibir a mensagem de erro na UI.

    # 4. Redirecionamento inicial para a página de criação de notificação se não autenticado
    #    e ainda não foi redirecionado nesta sessão.
    # A maneira mais confiável de verificar se estamos na página raiz (streamlit_app.py)
    # em multi-page apps é verificar se st.query_params está vazio.
    # Quando o Streamlit carrega a página raiz, a URL não tem ?page=nome_da_pagina.
    is_home_page_root_url = not st.query_params
    
    # Se estamos na URL raiz E o usuário não está autenticado E o redirecionamento inicial ainda não foi feito
    if is_home_page_root_url and not st.session_state.authenticated and not st.session_state.redirect_done:
        st.session_state.redirect_done = True # Marca que o redirecionamento foi feito/tentado
        st.switch_page("pages/1_Nova_Notificacao.py")
        # A execução será transferida para a nova página. O código abaixo não será executado nesta passagem.
        
    # Este conteúdo será exibido na área principal SOMENTE se o usuário estiver na página 'Home' (streamlit_app.py)
    # e não houver um redirecionamento automático (e.g., após o login ou se o usuário navegar de volta para acá).
    if st.session_state.authenticated:
        st.markdown("<h1 class='main-header'>Bem-vindo(a) ao NotificaSanta!</h1>", unsafe_allow_html=True)
        st.info("Utilize o menu lateral para navegar entre as funcionalidades.")
    else:
        st.markdown("<h1 class='main-header'>Bem-vindo(a) ao NotificaSanta!</h1>", unsafe_allow_html=True)
        st.info("Por favor, faça login para acessar o sistema ou utilize o menu lateral para criar uma nova notificação.")


if __name__ == "__main__":
    main_app_logic()
