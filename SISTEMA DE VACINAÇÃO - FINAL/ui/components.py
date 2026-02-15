"""
components.py - Componentes reutilizáveis da UI
"""

from typing import Any, List, Optional, Tuple

import pandas as pd
import streamlit as st

from core.security import Security, Formatters


class UIComponents:
    """Componentes UI reutilizáveis"""
    
    @staticmethod
    def create_accessible_input(label: str, key: str, required: bool = False, **kwargs):
        """Cria input com acessibilidade aprimorada"""
        col1, col2 = st.columns([3, 1])
        with col1:
            if required:
                st.markdown(f'<label data-required="true">{label}</label>', unsafe_allow_html=True)
            else:
                st.markdown(f'<label>{label}</label>', unsafe_allow_html=True)

            hotkey = kwargs.pop('hotkey', None)
            if hotkey:
                with col2:
                    st.markdown(f'<span class="hotkey-hint">{hotkey}</span>', unsafe_allow_html=True)

            return st.text_input("", key=key, label_visibility="collapsed", **kwargs)

    @staticmethod
    def create_pagination_controls(total_items: int, items_per_page: int = 20, session_key: str = "pagina_atual") -> Tuple[int, int]:
        """Cria controles de paginação"""
        if session_key not in st.session_state:
            st.session_state[session_key] = 1
        
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)

        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])

        with col1:
            st.markdown(f"**Total:** {total_items} itens")

        with col2:
            if st.button("◀️", key=f"prev_{session_key}", disabled=st.session_state[session_key] <= 1):
                st.session_state[session_key] -= 1
                st.rerun()

        with col3:
            st.markdown(f"**{st.session_state[session_key]} / {total_pages}**")

        with col4:
            if st.button("▶️", key=f"next_{session_key}", disabled=st.session_state[session_key] >= total_pages):
                st.session_state[session_key] += 1
                st.rerun()

        with col5:
            per_page_key = f"per_page_{session_key}"
            current_per_page = st.session_state.get(per_page_key, 20)
            new_per_page = st.selectbox(
                "Itens por página:",
                [10, 20, 50, 100],
                index=[10, 20, 50, 100].index(current_per_page),
                key=per_page_key,
                label_visibility="collapsed"
            )
            if new_per_page != current_per_page:
                st.session_state[per_page_key] = new_per_page
                st.session_state[session_key] = 1
                st.rerun()

        return st.session_state[session_key], new_per_page

    @staticmethod
    def show_loading_indicator(message: str = "Carregando..."):
        """Mostra indicador de carregamento"""
        return st.spinner(message)

    @staticmethod
    def show_success_message(message: str):
        """Mostra mensagem de sucesso com ícone"""
        st.success(f"✅ {message}")

    @staticmethod
    def show_error_message(message: str):
        """Mostra mensagem de erro com ícone"""
        st.error(f"❌ {message}")

    @staticmethod
    def show_warning_message(message: str):
        """Mostra mensagem de aviso com ícone"""
        st.warning(f"⚠️ {message}")

    @staticmethod
    def create_tooltip(text: str, tooltip: str):
        """Cria elemento com tooltip"""
        st.markdown(f'<span data-tooltip="{tooltip}">{text}</span>', unsafe_allow_html=True)

    @staticmethod
    def create_form_step(step_num: int, title: str, active: bool = False, completed: bool = False):
        """Cria passo de formulário"""
        classes = "form-step"
        if active:
            classes += " active"
        if completed:
            classes += " completed"

        st.markdown(f'<div class="{classes}">{title}</div>', unsafe_allow_html=True)

    @staticmethod
    def render_servidor_card(servidor: pd.Series, vacinacao_service, pdf_service, logo_path: str, usuario_nome: str, nivel_acesso: str):
        """Renderiza card de servidor otimizado"""
        with st.expander(f"👤 {servidor.get('nome','')}", expanded=False):
            col1, col2 = st.columns([3, 1])

            with col1:
                idade = Formatters.calcular_idade(servidor.get("data_nascimento"))

                st.markdown(f"""
                **Matrícula:** `{servidor.get('numfunc','')}-{servidor.get('numvinc','')}`
                **CPF:** {Security.formatar_cpf(servidor.get('cpf'))}
                **Idade:** {idade or 'N/I'} anos
                **Superintendência:** {servidor.get('superintendencia', 'Não informado')}
                **Lotação:** {servidor.get('lotacao','')}
                **Local Físico:** {servidor.get('lotacao_fisica', 'Não informado')}
                **Cargo:** {servidor.get('cargo') or 'N/I'}
                **Situação:** {servidor.get('situacao_funcional') or 'ATIVO'}
                """)

                if st.button("📋 Ver Histórico", key=f"hist_{servidor.get('id_comp')}"):
                    with UIComponents.show_loading_indicator("Carregando histórico..."):
                        hist = vacinacao_service.historico_servidor(str(servidor.get("id_comp")))
                        if not hist.empty:
                            st.dataframe(hist[["vacina", "dose", "data_ap", "lote"]],
                                       use_container_width=True, hide_index=True)

            with col2:
                action = st.selectbox(
                    "Ações:",
                    ["Selecionar ação", "📄 Gerar Ficha", "📤 Exportar", "✏️ Editar", "🗑️ Excluir"],
                    key=f"actions_{servidor.get('id_comp')}"
                )

                if action == "📄 Gerar Ficha":
                    if st.button("Gerar", key=f"pdf_{servidor.get('id_comp')}"):
                        with UIComponents.show_loading_indicator("Gerando PDF..."):
                            hist = vacinacao_service.historico_servidor(str(servidor.get("id_comp")))
                            from core.services import RelatorioPDFService
                            pdf_bytes = RelatorioPDFService.gerar_ficha_cadastral_pdf(
                                logo_path,
                                dict(servidor),
                                hist.to_dict('records') if not hist.empty else []
                            )
                            st.download_button(
                                "📥 Baixar",
                                data=pdf_bytes,
                                file_name=f"ficha_{servidor['nome'].replace(' ', '_')}.pdf",
                                mime="application/pdf"
                            )

    @staticmethod
    def create_accessible_table(df: pd.DataFrame, key: str):
        """Cria tabela acessível com recursos avançados"""
        if df.empty:
            st.info("Nenhum dado para exibir.")
            return

        with st.container():
            col_search, col_filter, col_export = st.columns([3, 2, 1])

            with col_search:
                search = st.text_input("🔍 Filtrar tabela:", key=f"search_{key}")

            with col_filter:
                filter_col = st.selectbox(
                    "Filtrar por coluna:",
                    [""] + df.columns.tolist(),
                    key=f"filter_{key}"
                )

            with col_export:
                st.download_button(
                    "📥 CSV",
                    df.to_csv(index=False),
                    f"dados_{key}.csv",
                    "text/csv",
                    use_container_width=True
                )

            filtered_df = df.copy()
            if search:
                mask = filtered_df.astype(str).apply(
                    lambda x: x.str.contains(search, case=False, na=False)
                ).any(axis=1)
                filtered_df = filtered_df[mask]

            if filter_col and filter_col in filtered_df.columns:
                unique_vals = filtered_df[filter_col].dropna().unique()
                selected = st.multiselect(
                    f"Valores em {filter_col}:",
                    unique_vals,
                    key=f"multiselect_{key}"
                )
                if selected:
                    filtered_df = filtered_df[filtered_df[filter_col].isin(selected)]

            if len(filtered_df) > 100:
                st.info(f"Mostrando 100 de {len(filtered_df)} registros. Use os filtros para refinar.")
                filtered_df = filtered_df.head(100)

            st.dataframe(
                filtered_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "cpf": st.column_config.TextColumn(
                        "CPF",
                        help="CPF formatado",
                        width="medium"
                    ),
                    "nome": st.column_config.TextColumn(
                        "Nome",
                        help="Nome completo",
                        width="large"
                    ),
                }
            )

            with st.expander("📊 Estatísticas"):
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("Total", len(filtered_df))
                with col_stat2:
                    st.metric("Colunas", len(filtered_df.columns))
                with col_stat3:
                    st.metric("Dados", f"{filtered_df.size:,}")

    @staticmethod
    def breadcrumb(*items: str):
        """Renderiza breadcrumb"""
        html = '<div class="breadcrumb">'
        for i, item in enumerate(items):
            html += f'<span class="breadcrumb-item">{item}</span>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)