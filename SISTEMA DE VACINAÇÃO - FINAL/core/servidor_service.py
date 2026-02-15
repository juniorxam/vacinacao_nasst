"""
servidor_service.py - Serviço de gerenciamento de servidores
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from core.auth_service import AuditLog  # CORRIGIDO: import absoluto com core.
from core.security import Security, Formatters  # CORRIGIDO: import absoluto com core.


class ServidoresService:
    def __init__(self, db: "Database", audit: AuditLog) -> None:
        self.db = db
        self.audit = audit

    def gerar_matricula_automatica(self) -> str:
        row = self.db.fetchone("SELECT numfunc FROM servidores ORDER BY CAST(numfunc AS INTEGER) DESC LIMIT 1")
        if row and row["numfunc"] is not None:
            try:
                return str(int(row["numfunc"]) + 1)
            except Exception:
                return "1000"
        return "1000"

    def obter_lotacoes(self) -> List[str]:
        """Obtém lista de setores da estrutura organizacional"""
        df = self.db.read_sql(
            "SELECT DISTINCT setor FROM estrutura_organizacional WHERE ativo = 1 ORDER BY setor"
        )
        if df.empty:
            # Fallback para o método antigo
            df = self.db.read_sql("SELECT DISTINCT lotacao FROM servidores ORDER BY lotacao")
            if df.empty:
                return []
            return [str(x) for x in df["lotacao"].dropna().tolist()]
        return [str(x) for x in df["setor"].dropna().tolist()]

    def obter_lotacoes_fisicas(self) -> List[str]:
        """Obtém lista de locais físicos da estrutura organizacional"""
        df = self.db.read_sql(
            "SELECT DISTINCT local_fisico FROM estrutura_organizacional WHERE local_fisico IS NOT NULL AND local_fisico != '' ORDER BY local_fisico"
        )
        if df.empty:
            return ["ANEXO 1", "ANEXO 7", "SEDE", "ETSUS", "CES", "ESTOQUE REGULADOR", "Não informado"]
        return [str(x) for x in df["local_fisico"].dropna().tolist()]
    
    def obter_superintendencias(self) -> List[str]:
        """Obtém lista de superintendências cadastradas"""
        df = self.db.read_sql(
            "SELECT DISTINCT superintendencia FROM estrutura_organizacional WHERE superintendencia IS NOT NULL AND superintendencia != '' ORDER BY superintendencia"
        )
        if df.empty:
            return [
                "GABINETE",
                "Superintendência de Assuntos Jurídicos",
                "Superintendência de Gestão e Acompanhamento Estratégico",
                "Superintendência Executiva do Fundo Estadual de Saúde",
                "Superintendência de Gestão Profissional e Educação na Saúde",
                "Superintendência de Gestão Administrativa",
                "Superintendência de Aquisição e Estratégias de Logística",
                "Superintendência da Central de Licitação",
                "Superintendência de Vigilância em Saúde",
                "Superintendência de Políticas de Atenção à Saúde",
                "Superintendência da Rede de Cuidados à Pessoa com Deficiência",
                "Superintendência de Unidades Hospitalares Próprias",
                "Não informado"
            ]
        return [str(x) for x in df["superintendencia"].dropna().tolist()]

    def obter_cargos_existentes(self) -> List[str]:
        df = self.db.read_sql(
            """
            SELECT DISTINCT cargo
            FROM servidores
            WHERE cargo IS NOT NULL
              AND cargo != ''
              AND cargo != 'Nao informado'
            ORDER BY cargo
            """
        )
        if df.empty:
            return []
        return [str(x) for x in df["cargo"].dropna().tolist()]

    def cadastrar_individual(self, dados: Dict[str, Any], usuario_cadastro: str) -> Tuple[bool, str]:
        try:
            numfunc = str(dados["numfunc"]).strip()
            numvinc = str(dados["numvinc"]).strip()
            id_comp = f"{numfunc}-{numvinc}"

            cpf_limpo = Security.clean_cpf(dados.get("cpf"))
            if not Security.validar_cpf(cpf_limpo):
                return False, "CPF invalido"

            nome = str(dados.get("nome", "")).strip().upper()
            lotacao = str(dados.get("lotacao", "")).strip().upper()
            if not nome or not lotacao:
                return False, "Nome e lotacao sao obrigatorios"

            cargo = dados.get("cargo")
            if cargo:
                cargo = str(cargo).upper().strip()

            existe = self.db.fetchone(
                "SELECT id_comp FROM servidores WHERE id_comp = ?",
                (id_comp,),
            )
            if existe:
                return False, "Servidor ja cadastrado (matricula ja existe)"

            self.db.execute(
                """
                INSERT INTO servidores
                (id_comp, numfunc, numvinc, nome, cpf, data_nascimento, sexo, cargo,
                 lotacao, lotacao_fisica, superintendencia, telefone, email, data_admissao,
                 tipo_vinculo, situacao_funcional, usuario_cadastro)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    id_comp,
                    numfunc,
                    numvinc,
                    nome,
                    cpf_limpo,
                    Formatters.parse_date(dados.get("data_nascimento")).isoformat() if Formatters.parse_date(dados.get("data_nascimento")) else None,
                    dados.get("sexo"),
                    cargo,
                    lotacao,
                    dados.get("lotacao_fisica"),
                    dados.get("superintendencia"),
                    dados.get("telefone"),
                    (str(dados["email"]).lower().strip() if dados.get("email") else None),
                    Formatters.parse_date(dados.get("data_admissao")).isoformat() if Formatters.parse_date(dados.get("data_admissao")) else None,
                    dados.get("tipo_vinculo"),
                    dados.get("situacao_funcional", "ATIVO"),
                    usuario_cadastro,
                ),
            )

            self.audit.registrar(usuario_cadastro, "SERVIDORES", "Cadastrou servidor individual", f"{nome} - {cpf_limpo}")
            return True, "Servidor cadastrado com sucesso!"
        except Exception as e:
            return False, f"Erro ao cadastrar: {str(e)}"

    @staticmethod
    def detectar_colunas_arquivo(df: pd.DataFrame) -> Dict[str, str]:
        m: Dict[str, str] = {}
        for col in df.columns:
            col_upper = str(col).upper().strip()

            if any(term in col_upper for term in ["NOME", "SERVIDOR"]):
                m["NOME"] = col
            elif "CPF" in col_upper:
                m["CPF"] = col
            elif any(term in col_upper for term in ["TIPO_VINCULO", "VINCULO"]):
                m["TIPO_VINCULO"] = col
            elif any(term in col_upper for term in ["NUMERO FUNCIONAL", "NUMERO_FUNCIONAL"]):
                m.setdefault("NUMFUNC", col)
            elif any(term in col_upper for term in ["NUMFUNC", "MATRICULA"]):
                m["NUMFUNC"] = col
            elif "NUMVINC" in col_upper:
                m["NUMVINC"] = col
            elif any(term in col_upper for term in ["LOTACAO", "SETOR"]):
                m["LOTACAO"] = col
            elif any(term in col_upper for term in ["LOCAL", "LOCAL2"]):
                m["LOTACAO_FISICA"] = col
            elif any(term in col_upper for term in ["SUPERINTENDENCIA", "SUPERINTENDÊNCIA", "SUP"]):
                m["SUPERINTENDENCIA"] = col
            elif any(term in col_upper for term in ["CARGO", "FUNCAO", "POSTO"]):
                m["CARGO"] = col
            elif any(term in col_upper for term in ["TELEFONE", "FONE", "CELULAR", "CONTATO", "TEL"]):
                m["TELEFONE"] = col
            elif any(term in col_upper for term in ["EMAIL", "E-MAIL", "E_MAIL"]):
                m["EMAIL"] = col
            elif any(term in col_upper for term in ["NASCIMENTO", "NASC", "DATANASC", "DATA_NASC"]):
                m["DATA_NASCIMENTO"] = col
            elif any(term in col_upper for term in ["ADMISSAO", "EXERCICIO", "DATA_ADM"]):
                m["DATA_ADMISSAO"] = col
            elif "SEXO" in col_upper or "GENERO" in col_upper:
                m["SEXO"] = col

        return m

    @staticmethod
    def _normalize_optional_value(v: Any) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        if not s or s.upper() in {"NAN", "NULL", "NONE"}:
            return None
        return s

    def importar_em_lote(
        self,
        df_raw: pd.DataFrame,
        mapeamento_final: Dict[str, str],
        acao_duplicados: str,
        modo_comparacao: str,
        criar_novos: bool,
        atualizar_vazios: bool,
        notificar_diferencas: bool,
        usuario: str,
    ) -> Tuple[Dict[str, int], List[str], List[Dict[str, Any]]]:
        stats = {"inseridos": 0, "atualizados": 0, "ignorados": 0, "erros": 0, "diferencas_detectadas": 0}
        erros: List[str] = []
        diferencas: List[Dict[str, Any]] = []

        required = ["NOME", "CPF", "NUMFUNC", "NUMVINC", "LOTACAO"]
        for r in required:
            if not mapeamento_final.get(r):
                raise ValueError(f"Campo obrigatorio nao mapeado: {r}")

        df = df_raw.copy()

        staging_cols: Dict[str, str] = {k: v for k, v in mapeamento_final.items() if v}
        stg = pd.DataFrame({k: df[v] for k, v in staging_cols.items()}).copy()

        for col in stg.columns:
            stg[col] = stg[col].astype(str).str.strip()

        mask_min = np.ones(len(stg), dtype=bool)
        for r in required:
            mask_min &= stg[r].notna() & (stg[r].str.upper().isin(["NAN", "NULL", "NONE"]) == False) & (stg[r] != "")
        stg = stg[mask_min].copy()
        if stg.empty:
            return stats, ["Nenhuma linha com dados minimos validos."], diferencas

        stg["CPF_LIMPO"] = stg["CPF"].map(Security.clean_cpf)
        stg["CPF_VALIDO"] = stg["CPF_LIMPO"].map(Security.validar_cpf)

        invalid_rows = stg[~stg["CPF_VALIDO"]]
        for idx, r in invalid_rows.head(200).iterrows():
            erros.append(f"Linha ~{int(idx)+2}: CPF invalido {r.get('CPF')}")
        stats["erros"] += int((~stg["CPF_VALIDO"]).sum())

        stg = stg[stg["CPF_VALIDO"]].copy()
        if stg.empty:
            return stats, erros, diferencas

        stg["ID_COMP"] = stg["NUMFUNC"].astype(str) + "-" + stg["NUMVINC"].astype(str)

        dup_in_file = stg.duplicated(subset=["ID_COMP"], keep=False)
        if dup_in_file.any():
            dups = stg[dup_in_file]["ID_COMP"].unique()
            for dup in dups[:10]:
                erros.append(f"ID_COMP duplicado no arquivo: {dup}")
            stg = stg.drop_duplicates(subset=["ID_COMP"], keep="first")

        stg["NOME"] = stg["NOME"].astype(str).str.upper()
        stg["LOTACAO"] = stg["LOTACAO"].astype(str).str.upper()
        if "LOTACAO_FISICA" in stg.columns:
            stg["LOTACAO_FISICA"] = stg["LOTACAO_FISICA"].astype(str).str.upper()
        if "SUPERINTENDENCIA" in stg.columns:
            stg["SUPERINTENDENCIA"] = stg["SUPERINTENDENCIA"].astype(str).str.upper()
        if "CARGO" in stg.columns:
            stg["CARGO"] = stg["CARGO"].astype(str).str.upper()

        existentes = self.db.read_sql(
            "SELECT id_comp, cpf, nome, lotacao, cargo, telefone, email, data_nascimento, sexo, data_admissao, tipo_vinculo, situacao_funcional, superintendencia, lotacao_fisica FROM servidores"
        )
        if existentes.empty:
            existentes = pd.DataFrame(columns=["id_comp", "cpf"])

        existentes["id_comp"] = existentes["id_comp"].astype(str)

        stg = stg.merge(existentes, left_on="ID_COMP", right_on="id_comp", how="left", suffixes=("", "_EX"))
        stg["EXISTE"] = stg["id_comp"].notna()
        
        key_update = "id_comp"
        key_from = "ID_COMP"

        campos_opcionais = {
            "CARGO": "cargo",
            "LOTACAO_FISICA": "lotacao_fisica",
            "SUPERINTENDENCIA": "superintendencia",
            "TELEFONE": "telefone",
            "EMAIL": "email",
            "DATA_NASCIMENTO": "data_nascimento",
            "SEXO": "sexo",
            "DATA_ADMISSAO": "data_admissao",
            "TIPO_VINCULO": "tipo_vinculo",
            "SITUACAO_FUNCIONAL": "situacao_funcional",
        }

        if notificar_diferencas and stg["EXISTE"].any():
            diffs_limit = 200
            df_exist = stg[stg["EXISTE"]].copy()
            count_diffs = 0

            for _, r in df_exist.iterrows():
                dif: Dict[str, Dict[str, Any]] = {}
                for campo_src, campo_db in campos_opcionais.items():
                    if campo_src in r and f"{campo_db}_EX" in df_exist.columns:
                        v_new = self._normalize_optional_value(r.get(campo_src))
                        v_old = self._normalize_optional_value(r.get(f"{campo_db}_EX"))
                        if v_new != v_old and v_new is not None:
                            dif[campo_src] = {"antigo": v_old, "novo": v_new}
                if dif:
                    stats["diferencas_detectadas"] += 1
                    count_diffs += 1
                    if count_diffs <= diffs_limit:
                        diferencas.append(
                            {"linha": None, "nome": r.get("NOME"), "cpf": r.get("CPF_LIMPO"), "diferencas": dif}
                        )

        update_rows = stg[stg["EXISTE"]].copy()
        updates: List[Tuple[str, List[Any]]] = []
        updated_count = 0
        ignored_count = 0

        mapeamento_campos = {
            "NOME": "nome",
            "CPF_LIMPO": "cpf",
            "NUMFUNC": "numfunc",
            "NUMVINC": "numvinc",
            "LOTACAO": "lotacao",
            "LOTACAO_FISICA": "lotacao_fisica",
            "SUPERINTENDENCIA": "superintendencia",
            "CARGO": "cargo",
            "TELEFONE": "telefone",
            "EMAIL": "email",
            "DATA_NASCIMENTO": "data_nascimento",
            "SEXO": "sexo",
            "DATA_ADMISSAO": "data_admissao",
            "TIPO_VINCULO": "tipo_vinculo",
            "SITUACAO_FUNCIONAL": "situacao_funcional",
        }

        if not update_rows.empty:
            if acao_duplicados == "Manter existente e ignorar novo":
                ignored_count += len(update_rows)
            else:
                for _, r in update_rows.iterrows():
                    data_to_set: Dict[str, Any] = {}
                    for src, dbcol in mapeamento_campos.items():
                        if src not in r:
                            continue
                        new_val = self._normalize_optional_value(r.get(src))
                        if new_val is None:
                            continue
                            
                        if dbcol in ["data_nascimento", "data_admissao"]:
                            dt = Formatters.parse_date(new_val)
                            if dt: 
                                new_val = dt.isoformat()

                        if acao_duplicados == "Sobrescrever todos os dados":
                            data_to_set[dbcol] = new_val
                            continue

                        old_val = self._normalize_optional_value(r.get(f"{dbcol}_EX"))
                        if old_val is None or (atualizar_vazios and (old_val == "")):
                            data_to_set[dbcol] = new_val

                    if not data_to_set:
                        ignored_count += 1
                        continue

                    set_clause = ", ".join([f"{k} = ?" for k in data_to_set.keys()])
                    params = list(data_to_set.values())

                    mk = str(r.get(key_from))
                    params.append(mk)
                    q = f"UPDATE servidores SET {set_clause} WHERE id_comp = ?"

                    updates.append((q, params))
                    updated_count += 1

        insert_rows = stg[~stg["EXISTE"]].copy()
        inserts_params: List[Tuple[Any, ...]] = []

        if not insert_rows.empty:
            if not criar_novos:
                ignored_count += len(insert_rows)
            else:
                for _, r in insert_rows.iterrows():
                    id_comp = str(r.get("ID_COMP"))
                    cpf_limpo = str(r.get("CPF_LIMPO"))
                    nome = str(r.get("NOME", "")).upper()
                    lotacao = str(r.get("LOTACAO", "")).upper()

                    lotacao_fisica = self._normalize_optional_value(r.get("LOTACAO_FISICA"))
                    superintendencia = self._normalize_optional_value(r.get("SUPERINTENDENCIA"))
                    cargo = self._normalize_optional_value(r.get("CARGO"))
                    telefone = self._normalize_optional_value(r.get("TELEFONE"))
                    email = self._normalize_optional_value(r.get("EMAIL"))
                    data_nascimento = Formatters.parse_date(r.get("DATA_NASCIMENTO"))
                    if data_nascimento: 
                        data_nascimento = data_nascimento.isoformat()
                    
                    sexo = self._normalize_optional_value(r.get("SEXO"))
                    
                    data_admissao = Formatters.parse_date(r.get("DATA_ADMISSAO"))
                    if data_admissao: 
                        data_admissao = data_admissao.isoformat()
                    tipo_vinculo = self._normalize_optional_value(r.get("TIPO_VINCULO"))
                    situacao_funcional = self._normalize_optional_value(r.get("SITUACAO_FUNCIONAL")) or "ATIVO"

                    inserts_params.append(
                        (
                            id_comp,
                            str(r.get("NUMFUNC")),
                            str(r.get("NUMVINC")),
                            nome,
                            cpf_limpo,
                            data_nascimento,
                            sexo,
                            (cargo.upper() if cargo else None),
                            lotacao,
                            (lotacao_fisica.upper() if lotacao_fisica else None),
                            (superintendencia.upper() if superintendencia else None),
                            telefone,
                            (email.lower() if email else None),
                            data_admissao,
                            tipo_vinculo,
                            situacao_funcional,
                            usuario,
                        )
                    )

        if updates:
            with self.db.connect() as conn:
                for q, p in updates:
                    try:
                        conn.execute(q, p)
                    except Exception as e:
                        erros.append(f"Erro ao atualizar {p[-1]}: {str(e)}")
                        stats["erros"] += 1
        
        if inserts_params:
            try:
                self.db.executemany(
                    """
                    INSERT INTO servidores
                    (id_comp, numfunc, numvinc, nome, cpf, data_nascimento, sexo, cargo,
                     lotacao, lotacao_fisica, superintendencia, telefone, email, data_admissao,
                     tipo_vinculo, situacao_funcional, usuario_cadastro)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    inserts_params,
                )
                stats["inseridos"] += len(inserts_params)
            except Exception as e:
                erros.append(f"Erro em lote, tentando linha por linha: {str(e)}")
                stats["inseridos"] = 0
                with self.db.connect() as conn:
                    for params in inserts_params:
                        try:
                            conn.execute(
                                """
                                INSERT INTO servidores
                                (id_comp, numfunc, numvinc, nome, cpf, data_nascimento, sexo, cargo,
                                 lotacao, lotacao_fisica, superintendencia, telefone, email, data_admissao,
                                 tipo_vinculo, situacao_funcional, usuario_cadastro)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                params,
                            )
                            stats["inseridos"] += 1
                        except Exception as row_error:
                            erros.append(f"Erro ao inserir {params[0]}: {str(row_error)}")
                            stats["erros"] += 1

        stats["atualizados"] += updated_count
        stats["ignorados"] += ignored_count

        self.audit.registrar(
            usuario,
            "SERVIDORES",
            "Importacao em massa",
            f"{stats['inseridos']} novos, {stats['atualizados']} atualizados, {stats['erros']} erros",
        )

        return stats, erros, diferencas

    def buscar_servidores(self, termo: str, limit: int = 10) -> pd.DataFrame:
        termo = (termo or "").strip()
        if not termo:
            return pd.DataFrame()
        like = f"%{termo}%"
        return self.db.read_sql(
            """
            SELECT *
            FROM servidores
            WHERE nome LIKE ?
               OR cpf LIKE ?
               OR id_comp LIKE ?
               OR numfunc LIKE ?
            LIMIT ?
            """,
            (like, like, like, like, int(limit)),
        )

    def excluir_servidor(self, id_comp: str, usuario: str) -> None:
        with self.db.connect() as conn:
            conn.execute("DELETE FROM doses WHERE id_comp = ?", (id_comp,))
            conn.execute("DELETE FROM servidores WHERE id_comp = ?", (id_comp,))
        self.audit.registrar(usuario, "SERVIDORES", "Excluiu servidor", id_comp)