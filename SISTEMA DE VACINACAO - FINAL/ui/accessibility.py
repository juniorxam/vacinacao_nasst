"""
accessibility.py - Componentes de acessibilidade aprimorados
"""

import streamlit as st
from typing import Optional, Dict, Any


class AccessibilityManager:
    """Gerencia recursos de acessibilidade da aplicação"""
    
    @staticmethod
    def inject_accessibility_js():
        """Injeta JavaScript para melhorar acessibilidade"""
        st.markdown("""
        <script>
        // Melhorar navegação por teclado
        document.addEventListener('keydown', function(e) {
            // Foco na busca quando pressionar F
            if (e.key === 'f' || e.key === 'F') {
                const searchInputs = document.querySelectorAll('input[type="text"]');
                for (let input of searchInputs) {
                    if (input.placeholder && input.placeholder.toLowerCase().includes('buscar')) {
                        input.focus();
                        e.preventDefault();
                        break;
                    }
                }
            }
            
            // Atalho para salvar (Ctrl+S)
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                const submitButtons = document.querySelectorAll('button[type="submit"]');
                if (submitButtons.length > 0) {
                    submitButtons[0].click();
                }
            }
            
            // Atalho para cancelar (Ctrl+Q)
            if (e.ctrlKey && e.key === 'q') {
                e.preventDefault();
                const cancelButtons = Array.from(document.querySelectorAll('button')).filter(
                    btn => btn.textContent.includes('Cancelar')
                );
                if (cancelButtons.length > 0) {
                    cancelButtons[0].click();
                }
            }
        });
        
        // Anunciar mudanças para leitores de tela
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    const alerts = document.querySelectorAll('.stAlert, .stSuccess, .stError, .stWarning');
                    alerts.forEach(function(alert) {
                        alert.setAttribute('role', 'alert');
                        alert.setAttribute('aria-live', 'polite');
                    });
                }
            });
        });
        
        observer.observe(document.body, { childList: true, subtree: true });
        
        // Melhorar foco visível
        const style = document.createElement('style');
        style.textContent = `
            :focus {
                outline: 3px solid #4A90E2 !important;
                outline-offset: 2px !important;
                box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.3) !important;
            }
            
            .skip-to-content {
                position: absolute;
                left: -9999px;
                top: auto;
                width: 1px;
                height: 1px;
                overflow: hidden;
            }
            
            .skip-to-content:focus {
                position: fixed;
                top: 10px;
                left: 10px;
                width: auto;
                height: auto;
                padding: 10px;
                background: #4A90E2;
                color: white;
                z-index: 9999;
                text-decoration: none;
                border-radius: 4px;
                outline: 3px solid white;
            }
        `;
        document.head.appendChild(style);
        
        // Adicionar link "Pular para conteúdo"
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.className = 'skip-to-content';
        skipLink.textContent = 'Pular para o conteúdo principal';
        document.body.insertBefore(skipLink, document.body.firstChild);
        </script>
        
        <style>
        /* Alto contraste */
        .high-contrast {
            background-color: black !important;
            color: yellow !important;
        }
        
        .high-contrast button {
            background-color: yellow !important;
            color: black !important;
            border: 2px solid white !important;
        }
        
        /* Texto aumentado */
        .large-text {
            font-size: 1.3em !important;
        }
        
        /* Indicador de campos obrigatórios */
        label[data-required="true"]::after {
            content: " *";
            color: #ff0000;
            font-weight: bold;
        }
        </style>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def create_accessible_button(
        label: str,
        key: str,
        help_text: Optional[str] = None,
        shortcut: Optional[str] = None,
        **kwargs
    ):
        """Cria botão acessível com atalho e descrição"""
        if shortcut:
            # Adicionar indicador de atalho no label
            if "(" not in label and ")" not in label:
                label = f"{label} ({shortcut})"
        
        # Criar container com aria-label
        container = st.container()
        with container:
            if help_text:
                st.markdown(
                    f'<span id="help-{key}" style="display: none;">{help_text}</span>',
                    unsafe_allow_html=True
                )
            
            button = st.button(
                label,
                key=key,
                **kwargs
            )
            
            # Adicionar atributos ARIA via JavaScript
            st.markdown(f"""
            <script>
            (function() {{
                const btn = document.querySelector('[key="{key}"] button');
                if (btn) {{
                    btn.setAttribute('aria-label', '{label}');
                    if ('{help_text}') {{
                        btn.setAttribute('aria-describedby', 'help-{key}');
                    }}
                }}
            }})();
            </script>
            """, unsafe_allow_html=True)
            
            return button
    
    @staticmethod
    def create_accessible_input(
        label: str,
        key: str,
        input_type: str = "text",
        required: bool = False,
        help_text: Optional[str] = None,
        **kwargs
    ):
        """Cria input acessível com label associada"""
        # Gerar ID único
        input_id = f"input-{key}"
        
        # Container com role
        st.markdown(f'<div role="group" aria-labelledby="label-{key}">', unsafe_allow_html=True)
        
        # Label com ID
        required_mark = ' <span style="color: red;">*</span>' if required else ''
        st.markdown(
            f'<label id="label-{key}" for="{input_id}" class="input-label">{label}{required_mark}</label>',
            unsafe_allow_html=True
        )
        
        # Input
        if help_text:
            st.markdown(
                f'<span id="help-{key}" style="font-size: 0.9em; color: #666;">{help_text}</span>',
                unsafe_allow_html=True
            )
        
        # Criar input apropriado baseado no tipo
        value = kwargs.pop('value', '')
        placeholder = kwargs.pop('placeholder', '')
        
        if input_type == "text":
            result = st.text_input(
                label="",  # Label vazia pois já criamos manualmente
                key=key,
                value=value,
                placeholder=placeholder,
                label_visibility="collapsed",
                **kwargs
            )
        elif input_type == "password":
            result = st.text_input(
                label="",
                key=key,
                value=value,
                placeholder=placeholder,
                type="password",
                label_visibility="collapsed",
                **kwargs
            )
        elif input_type == "number":
            result = st.number_input(
                label="",
                key=key,
                value=value if value else 0,
                label_visibility="collapsed",
                **kwargs
            )
        elif input_type == "textarea":
            result = st.text_area(
                label="",
                key=key,
                value=value,
                placeholder=placeholder,
                label_visibility="collapsed",
                **kwargs
            )
        else:
            result = st.text_input(
                label="",
                key=key,
                value=value,
                placeholder=placeholder,
                label_visibility="collapsed",
                **kwargs
            )
        
        # Adicionar atributos ARIA via JavaScript
        st.markdown(f"""
        <script>
        (function() {{
            const input = document.querySelector('[key="{key}"] input, [key="{key}"] textarea');
            if (input) {{
                input.id = '{input_id}';
                input.setAttribute('aria-labelledby', 'label-{key}');
                if ('{help_text}') {{
                    input.setAttribute('aria-describedby', 'help-{key}');
                }}
                if ({str(required).lower()}) {{
                    input.setAttribute('aria-required', 'true');
                }}
            }}
        }})();
        </script>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        return result
    
    @staticmethod
    def create_accessible_selectbox(
        label: str,
        options: list,
        key: str,
        required: bool = False,
        help_text: Optional[str] = None,
        **kwargs
    ):
        """Cria selectbox acessível"""
        # Gerar ID único
        select_id = f"select-{key}"
        
        # Container
        st.markdown(f'<div role="group" aria-labelledby="label-select-{key}">', unsafe_allow_html=True)
        
        # Label
        required_mark = ' <span style="color: red;">*</span>' if required else ''
        st.markdown(
            f'<label id="label-select-{key}" for="{select_id}">{label}{required_mark}</label>',
            unsafe_allow_html=True
        )
        
        if help_text:
            st.markdown(
                f'<span id="help-select-{key}" style="font-size: 0.9em; color: #666;">{help_text}</span>',
                unsafe_allow_html=True
            )
        
        # Selectbox
        index = kwargs.pop('index', 0)
        result = st.selectbox(
            label="",
            options=options,
            index=index,
            key=key,
            label_visibility="collapsed",
            **kwargs
        )
        
        # Atributos ARIA
        st.markdown(f"""
        <script>
        (function() {{
            const select = document.querySelector('[key="{key}"] select');
            if (select) {{
                select.id = '{select_id}';
                select.setAttribute('aria-labelledby', 'label-select-{key}');
                if ('{help_text}') {{
                    select.setAttribute('aria-describedby', 'help-select-{key}');
                }}
                if ({str(required).lower()}) {{
                    select.setAttribute('aria-required', 'true');
                }}
            }}
        }})();
        </script>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        return result
    
    @staticmethod
    def announce_message(message: str, priority: str = "polite"):
        """Anuncia mensagem para leitores de tela"""
        st.markdown(f"""
        <div aria-live="{priority}" aria-atomic="true" style="position: absolute; width: 1px; height: 1px; overflow: hidden;">
            {message}
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def create_high_contrast_toggle():
        """Cria botão para alternar alto contraste"""
        if 'high_contrast' not in st.session_state:
            st.session_state.high_contrast = False
        
        col1, col2, col3 = st.columns([1, 1, 10])
        with col1:
            if st.button(
                "👁️" + (" (AC)" if st.session_state.high_contrast else ""),
                help="Alternar alto contraste (Ctrl+Shift+C)",
                key="contrast_toggle"
            ):
                st.session_state.high_contrast = not st.session_state.high_contrast
                st.rerun()
        
        if st.session_state.high_contrast:
            st.markdown("""
            <style>
            .main, .stApp {
                background-color: black !important;
                color: yellow !important;
            }
            .stButton button {
                background-color: yellow !important;
                color: black !important;
                border: 2px solid white !important;
            }
            .stTextInput input, .stSelectbox select {
                background-color: #333 !important;
                color: yellow !important;
                border: 1px solid yellow !important;
            }
            label, .stMarkdown, p, h1, h2, h3, h4 {
                color: yellow !important;
            }
            [data-testid="stSidebar"] {
                background-color: #222 !important;
                border-right: 2px solid yellow !important;
            }
            </style>
            """, unsafe_allow_html=True)