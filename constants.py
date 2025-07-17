# constants.py

import os
from datetime import datetime, date as dt_date_class, time as dt_time_class

# --- Diretórios de Dados e Arquivos (para anexos) ---
DATA_DIR = "data"
ATTACHMENTS_DIR = os.path.join(DATA_DIR, "attachments")


# Mapeamento de prazos para conclusão da notificação
DEADLINE_DAYS_MAPPING = {
    "Não conformidade": 30,
    "Circunstância de Risco": 30,
    "Near Miss": 30,
    "Evento sem dano": 10,
    "Evento com dano": {
        "Dano leve": 7,
        "Dano moderado": 5,
        "Dano grave": 3,
        "Óbito": 3
    }
}

# --- Classes de Dados Globais ---

class UI_TEXTS:
    selectbox_default_event_shift = "Selecionar Turno"
    selectbox_default_immediate_actions_taken = "Selecione"
    selectbox_default_patient_involved = "Selecione"
    selectbox_default_patient_outcome_obito = "Selecione"
    selectbox_default_initial_event_type = "Selecione"
    selectbox_default_initial_severity = "Selecione"
    selectbox_default_notification_select = "Selecione uma notificação..."
    text_na = "N/A"
    selectbox_default_procede_classification = "Selecione"
    selectbox_default_classificacao_nnc = "Selecione"
    selectbox_default_nivel_dano = "Selecione"
    selectbox_default_prioridade_resolucao = "Selecione"
    selectbox_default_never_event = "Selecione"
    selectbox_default_evento_sentinela = "Selecione"
    selectbox_default_tipo_principal = "Selecione"
    multiselect_instruction_placeholder = "Selecione uma ou mais opções..."
    multiselect_event_spec_label_prefix = "Especificação do Evento "
    multiselect_event_spec_label_suffix = ":"
    multiselect_classification_oms_label = "Classificação OMS:* (selecionar ao menos um)"
    selectbox_default_requires_approval = "Selecione"
    selectbox_default_approver = "Selecione"
    selectbox_default_decisao_revisao = "Selecione"
    selectbox_default_acao_realizar = "Selecione"
    multiselect_assign_executors_label = "Atribuir Executores Responsáveis:*"
    selectbox_default_decisao_aprovacao = "Selecione"
    multiselect_all_option = "Todos"
    selectbox_sort_by_placeholder = "Ordenar por..."
    selectbox_sort_by_label = "Ordenar por:"
    selectbox_items_per_page_placeholder = "Itens por página..."
    selectbox_items_per_page_label = "Itens por página:"
    selectbox_default_admin_debug_notif = "Selecione uma notificação..."
    selectbox_never_event_na_text = "Não Aplicável (N/A)"
    multiselect_user_roles_label = "Funções do Usuário:*"

    # Novos textos para status de prazo
    deadline_status_ontrack = "No Prazo"
    deadline_status_duesoon = "Prazo Próximo"
    deadline_status_overdue = "Atrasada"
    deadline_days_nan = "Nenhum prazo definido"
    selectbox_default_department_select = "Selecione o Setor..."

    # Constantes para filtros do dashboard
    multiselect_filter_status_label = "Filtrar por Status:"
    multiselect_filter_nnc_label = "Filtrar por Classificação NNC:"
    multiselect_filter_priority_label = "Filtrar por Prioridade:"


class FORM_DATA:
    turnos = ["Diurno", "Noturno", "Não sei informar"]
    classificacao_nnc = ["Não conformidade", "Circunstância de Risco", "Near Miss", "Evento sem dano",
                         "Evento com dano"]
    niveis_dano = ["Dano leve", "Dano moderado", "Dano grave", "Óbito"]
    prioridades = ["Baixa", "Média", "Alta", "Crítica"]

    SETORES = [
        "Superintendência", "Agência Transfusional (AGT)", "Ala A", "Ala B",
        "Ala C", "Ala E", "Almoxarifado", "Assistência Social",
        "Ambulatório Bariátrica/Reparadora", "CCIH", "CDI", "Centro Cirúrgico",
        "Centro Obstétrico", "CME", "Comercial/Tesouraria", "Compras",
        "Comunicação", "Contabilidade", "CPD (TI)", "DPI",
        "Diretoria Assistencial", "Diretoria Clínica", "Diretoria Financeira",
        "Diretoria Técnica", "Departamento Pessoal (RH)", "Ambulatório Egresso (Especialidades)",
        "EMTN", "Farmácia Clínica", "Farmácia Central", "Farmácia Oncológica (Manipulação Quimioterapia)",
        "Farmácia UNACON", "Farmácia Satélite UTI",
        "Faturamento", "Fisioterapia", "Fonoaudiologia", "Gestão de Leitos",
        "Hemodiálise", "Higienização", "Internação/Autorização (Convênio)", "Iodoterapia",
        "Laboratório de Análises Clínicas", "Lavanderia", "Manutenção Equipamentos", "Manutenção Predial",
        "Maternidade", "Medicina do Trabalho", "NHE", "Odontologia", "Ouvidoria", "Pediatria",
        "Portaria/Gestão de Acessos", "Psicologia", "Qualidade", "Quimioterapia (Salão de Quimio)",
        "Recepção", "Recrutamento e Seleção", "Regulação", "SAME", "SESMT",
        "Serviço de Nutrição e Dietética", "SSB", "Urgência e Emergência/Pronto Socorro",
        "UNACON", "UTI Adulto", "UTI Neo e Pediátrica"
    ]
    never_events = [
        "Cirurgia no local errado do corpo, no paciente errado ou o procedimento errado",
        "Retenção de corpo estranho em paciente após a cirurgia",
        "Morte de paciente ou lesão grave associada ao uso de dispositivo médico",
        "Morte de paciente ou lesão grave associada à incompatibilidade de tipo sanguíneo",
        "Morte de paciente ou lesão grave associada a erro de medicação",
        "Morte de paciente ou lesão grave associada à trombose venosa profunda (TVP) ou embolia pulmonar (EP) após artroplastia total de quadril ou joelho",
        "Morte de paciente ou lesão grave associada a hipoglicemia",
        "Morte de paciente ou lesão grave associada à infecção hospitalar",
        "Morte de paciente ou lesão grave associada a úlcera por pressão (escaras) adquirida no hospital",
        "Morte de paciente ou lesão grave associada à contenção inadequada",
        "Morte ou lesão grave associada à falha ou uso incorreto de equipamentos de proteção individual (EPIs)",
        "Morte de paciente ou lesão grave associada à queda do paciente",
        "Morte de paciente ou lesão grave associada à violência física ou sexual no ambiente hospitalar",
        "Morte de paciente ou lesão grave associada ao desaparecimento de paciente"
    ]
    tipos_evento_principal = {
        "Clínico": [
            "Infecção Relacionada à Assistência à Saúde (IRAS)",
            "Administração de Antineoplásicos",
            "META 1 - Identificação Incorreta do Paciente",
            "META 2 - Falha na Comunicação entre Profissionais",
            "META 3 - Problema com Medicamento (Segurança Medicamentosa)",
            "META 4 - Procedimento Incorreto (Cirurgia/Parto)",
            "META 5 - Higiene das Mãos Inadequada",
            "META 6 - Queda de Paciente e Lesão por Pressão",
            "Transfusão Inadequada de Sangue ou Derivados",
            "Problema com Dispositivo/Equipamento Médico",
            "Evento Crítico ou Intercorrência Grave em Processo Seguro",
            "Problema Nutricional Relacionado à Assistência",
            "Não Conformidade com Protocolos Gerenciados",
            "Quebra de SLA (Atraso ou Falha na Assistência)",
            "Evento Relacionado ao Parto e Nascimento",
            "Crise Convulsiva em Ambiente Assistencial",
            "[Hemodiálise] Coagulação do Sistema Extracorpóreo",
            "[Hemodiálise] Desconexão Acidental da Agulha de Punção da Fístula Arteriovenosa",
            "[Hemodiálise] Desconexão Acidental do Cateter às Linhas de Hemodiálise",
            "[Hemodiálise] Embolia Pulmonar Relacionada à Hemodiálise",
            "[Hemodiálise] Exteriorização Acidental da Agulha de Punção da Fístula Arteriovenosa",
            "[Hemodiálise] Exteriorização Acidental do Cateter de Hemodiálise",
            "[Hemodiálise] Falha na Identificação do Dialisador ou das Linhas de Hemodiálise",
            "[Hemodiálise] Falha no Fluxo Sanguíneo do Cateter de Hemodiálise",
            "[Hemodiálise] Falha no Fluxo Sanguíneo da Fístula Arteriovenosa",
            "[Hemodiálise] Hematoma Durante a Passagem do Cateter de Hemodiálise",
            "[Hemodiálise] Hemólise Relacionada à Hemodiálise",
            "[Hemodiálise] Infiltração, Edema ou Hematoma na Fístula Arteriovenosa",
            "[Hemodiálise] Pneumotórax Durante a Passagem do Cateter de Hemodiálise",
            "[Hemodiálise] Pseudoaneurisma na Fístula Arteriovenosa",
            "[Hemodiálise] Punção Arterial Acidental Durante Inserção do Cateter de Hemodiálise",
            "[Hemodiálise] Rotura da Fístula Arteriovenosa",
            "[Hemodiálise] Sangramento pelo Óstio do Cateter de Hemodiálise",
            "[Hemodiálise] Outras Falhas Relacionadas à Hemodiálise"
        ],
        "Não-clínico": [
            "Incidente de Segurança Patrimonial",
            "Problema Estrutural/Instalações",
            "Problema de Abastecimento/Logística",
            "Incidente de TI/Dados",
            "Erro Administrativo",
            "Outros Eventos Não-clínicos"
        ],
        "Ocupacional": [
            "Acidente com Material Biológico",
            "Acidente de Trabalho (geral)",
            "Doença Ocupacional",
            "Exposição a Agentes de Risco",
            "Outros Eventos Ocupacionais"
        ],
        "Queixa técnica": [],
        "Outros": []
    }
    classificacao_oms = [
        "Quedas", "Infecções", "Medicação", "Cirurgia", "Identificação do Paciente",
        "Procedimentos", "Dispositivos Médicos", "Urgência/Emergência",
        "Segurança do Ambiente", "Comunicação", "Recursos Humanos", "Outros"
    ]