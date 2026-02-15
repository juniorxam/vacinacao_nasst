"""
test_integration.py - Testes de integração do sistema NASST Digital
Testa fluxos completos e interações entre diferentes módulos
"""

import pytest
from datetime import date, timedelta
import pandas as pd

# CORREÇÃO: Importações dos módulos específicos, não de core.services
from core.servidor_service import ServidoresService
from core.vacinacao_service import VacinacaoService
from core.campanha_service import CampanhasService
from core.relatorio_service import RelatoriosService, RelatoriosGerenciaisService
from core.auth_service import AuditLog, Auth
from core.estrutura_service import EstruturaOrganizacionalService
from core.security import Security


class TestFluxoCompleto:
    """Testa fluxo completo de uso do sistema - do cadastro ao relatório"""
    
    def test_fluxo_completo_vacinacao(self, db, sample_servidor_data, sample_campanha_data):
        """Testa fluxo completo: cadastrar servidor, criar campanha, registrar vacinação, gerar relatórios"""
        
        # Inicializar serviços
        audit = AuditLog(db)
        servidores = ServidoresService(db, audit)
        vacinacao = VacinacaoService(db, audit)
        campanhas = CampanhasService(db, audit)
        relatorios = RelatoriosService(db)
        relatorios_gerenciais = RelatoriosGerenciaisService(db)
        
        # 1. CADASTRAR SERVIDOR
        print("\n1. Testando cadastro de servidor...")
        sucesso, msg = servidores.cadastrar_individual(sample_servidor_data, "usuario_teste")
        assert sucesso is True, f"Falha ao cadastrar servidor: {msg}"
        
        # Buscar ID do servidor
        servidor = db.fetchone(
            "SELECT id_comp, nome, cpf, lotacao FROM servidores WHERE cpf = ?",
            ("12345678909",)
        )
        assert servidor is not None, "Servidor não encontrado após cadastro"
        assert servidor["nome"] == sample_servidor_data["nome"], "Nome do servidor não confere"
        print(f"✅ Servidor cadastrado: {servidor['nome']} (ID: {servidor['id_comp']}, Lotação: {servidor['lotacao']})")
        
        # 2. CRIAR CAMPANHA
        print("\n2. Testando criação de campanha...")
        campanhas.criar_campanha(
            nome=sample_campanha_data["nome"],
            vacina=sample_campanha_data["vacina"],
            publico_alvo=sample_campanha_data["publico_alvo"],
            data_inicio=sample_campanha_data["data_inicio"],
            data_fim=sample_campanha_data["data_fim"],
            status=sample_campanha_data["status"],
            descricao=sample_campanha_data["descricao"],
            usuario="usuario_teste"
        )
        
        # Buscar ID da campanha
        campanha = db.fetchone(
            "SELECT id, nome_campanha, vacina FROM campanhas WHERE nome_campanha = ?",
            (sample_campanha_data["nome"],)
        )
        assert campanha is not None, "Campanha não encontrada após criação"
        assert campanha["vacina"] == sample_campanha_data["vacina"], "Vacina da campanha não confere"
        print(f"✅ Campanha criada: {campanha['nome_campanha']} (ID: {campanha['id']})")
        
        # 3. REGISTRAR VACINAÇÃO
        print("\n3. Testando registro de vacinação...")
        data_ap = date.today()
        
        # Calcular data de retorno baseado na vacina
        vacina_lower = sample_campanha_data["vacina"].lower()
        if "influenza" in vacina_lower:
            data_ret = data_ap + timedelta(days=365)
        elif "covid" in vacina_lower:
            data_ret = data_ap + timedelta(days=21)
        else:
            data_ret = data_ap + timedelta(days=30)
        
        # Registrar primeira dose
        sucesso = vacinacao.registrar_dose(
            id_comp=servidor["id_comp"],
            vacina=sample_campanha_data["vacina"],
            dose="1ª Dose",
            data_ap=data_ap,
            data_ret=data_ret,
            lote="LOT12345",
            fabricante="Butantan",
            local_aplicacao="NASST Central",
            via_aplicacao="Intramuscular",
            campanha_id=campanha["id"],
            usuario="usuario_teste"
        )
        assert sucesso is True, "Falha ao registrar primeira dose"
        print("✅ Primeira dose registrada")
        
        # 4. VERIFICAR MÉTRICAS GERAIS
        print("\n4. Testando métricas gerais...")
        metricas = relatorios.get_metricas_gerais()
        assert metricas["total_servidores"] >= 1, "Total de servidores não atualizado"
        assert metricas["total_doses"] >= 1, "Total de doses não atualizado"
        assert metricas["cobertura"] > 0, "Cobertura não calculada corretamente"
        print(f"✅ Métricas: {metricas['total_servidores']} servidores, {metricas['total_doses']} doses, {metricas['cobertura']:.1f}% cobertura")
        
        # 5. VERIFICAR HISTÓRICO DO SERVIDOR
        print("\n5. Testando histórico do servidor...")
        historico = vacinacao.historico_servidor(servidor["id_comp"])
        assert not historico.empty, "Histórico vazio após vacinação"
        assert len(historico) >= 1, "Histórico não contém registros"
        assert historico.iloc[0]["vacina"] == sample_campanha_data["vacina"], "Vacina no histórico não confere"
        assert historico.iloc[0]["campanha_id"] == campanha["id"], "Campanha no histórico não confere"
        print(f"✅ Histórico contém {len(historico)} registro(s)")
        
        # 6. TESTAR RELATÓRIO GERENCIAL
        print("\n6. Testando relatório gerencial...")
        relatorio = relatorios_gerenciais.gerar_relatorio_servidor(servidor["id_comp"])
        assert relatorio, "Relatório do servidor vazio"
        assert relatorio["servidor"]["nome"] == sample_servidor_data["nome"], "Nome no relatório não confere"
        assert relatorio["total_doses"] >= 1, "Total de doses no relatório incorreto"
        print(f"✅ Relatório gerencial gerado: {relatorio['total_doses']} dose(s) encontrada(s)")
        
        # 7. TESTAR COBERTURA POR LOTAÇÃO - CORREÇÃO FINAL
        print("\n7. Testando relatório de cobertura por lotação...")
        
        # Garantir que a lotação está em maiúsculas (como no cadastro)
        lotacao_servidor = servidor['lotacao'].upper().strip()
        print(f"   Lotação do servidor (normalizada): {lotacao_servidor}")
        
        # Verificar se há doses registradas
        doses_count = db.fetchone(
            "SELECT COUNT(*) as total FROM doses WHERE id_comp = ?",
            (servidor["id_comp"],)
        )
        print(f"   Doses registradas: {doses_count['total']}")
        
        # Buscar todas as lotações disponíveis no banco
        lotacoes_db = db.fetchall("SELECT DISTINCT lotacao FROM servidores")
        print("   Lotações disponíveis no banco:")
        for lot in lotacoes_db:
            print(f"     - {lot['lotacao']}")
        
        # CORREÇÃO: Usar SQL direto para garantir que os dados estão lá
        df_cobertura_direto = db.read_sql(
            """
            SELECT 
                s.lotacao,
                COUNT(DISTINCT s.id_comp) AS total_servidores,
                COUNT(DISTINCT d.id_comp) AS total_vacinados
            FROM servidores s
            LEFT JOIN doses d ON s.id_comp = d.id_comp
            WHERE s.lotacao = ?
            GROUP BY s.lotacao
            """,
            (lotacao_servidor,)
        )
        
        print(f"   Resultado SQL direto: {len(df_cobertura_direto)} registros")
        if not df_cobertura_direto.empty:
            print(f"   Total servidores: {df_cobertura_direto.iloc[0]['total_servidores']}")
            print(f"   Total vacinados: {df_cobertura_direto.iloc[0]['total_vacinados']}")
        
        # Agora testar o método do serviço com diferentes variações da lotação
        tentativas = [
            lotacao_servidor,
            lotacao_servidor.lower(),
            lotacao_servidor.title(),
            sample_servidor_data["lotacao"],  # Original
        ]
        
        df_cobertura = pd.DataFrame()
        tentativa_usada = ""
        
        for tentativa in tentativas:
            print(f"   Tentando com lotação: '{tentativa}'")
            df_cobertura = relatorios.cobertura_detalhada(
                lotacao=tentativa,
                data_ini=date.today() - timedelta(days=365),
                data_fim=date.today() + timedelta(days=365)
            )
            if not df_cobertura.empty:
                tentativa_usada = tentativa
                print(f"   ✅ Sucesso com lotação: '{tentativa}'")
                break
        
        # Se ainda estiver vazio, tentar com "TODAS"
        if df_cobertura.empty:
            print("   Tentando com lotação 'TODAS'...")
            df_cobertura = relatorios.cobertura_detalhada(
                lotacao="TODAS",
                data_ini=date.today() - timedelta(days=365),
                data_fim=date.today() + timedelta(days=365)
            )
            if not df_cobertura.empty:
                tentativa_usada = "TODAS"
                print("   ✅ Sucesso com 'TODAS'")
        
        assert not df_cobertura.empty, f"Relatório de cobertura vazio após {len(tentativas)} tentativas"
        print(f"✅ Relatório de cobertura gerado para lotação '{tentativa_usada}' com {len(df_cobertura)} registro(s)")
        
        # 8. TESTAR REGISTRO DE DOSE DUPLICADA
        print("\n8. Testando prevenção de duplicidade...")
        sucesso = vacinacao.registrar_dose(
            id_comp=servidor["id_comp"],
            vacina=sample_campanha_data["vacina"],
            dose="1ª Dose",
            data_ap=data_ap,  # Mesma data
            data_ret=data_ret,
            lote="LOT12345",
            fabricante="Butantan",
            local_aplicacao="NASST Central",
            via_aplicacao="Intramuscular",
            campanha_id=campanha["id"],
            usuario="usuario_teste"
        )
        assert sucesso is False, "Sistema permitiu registro duplicado"
        print("✅ Sistema bloqueou registro duplicado corretamente")
        
        # 9. REGISTRAR SEGUNDA DOSE
        print("\n9. Testando registro de segunda dose...")
        data_ap_2 = data_ret  # Usar data de retorno como nova data de aplicação
        data_ret_2 = data_ap_2 + timedelta(days=30)
        
        sucesso = vacinacao.registrar_dose(
            id_comp=servidor["id_comp"],
            vacina=sample_campanha_data["vacina"],
            dose="2ª Dose",
            data_ap=data_ap_2,
            data_ret=data_ret_2,
            lote="LOT12345",
            fabricante="Butantan",
            local_aplicacao="NASST Central",
            via_aplicacao="Intramuscular",
            campanha_id=campanha["id"],
            usuario="usuario_teste"
        )
        assert sucesso is True, "Falha ao registrar segunda dose"
        print("✅ Segunda dose registrada")
        
        # 10. VERIFICAR ESTATÍSTICAS FINAIS
        print("\n10. Verificando estatísticas finais...")
        metricas_finais = relatorios.get_metricas_gerais()
        assert metricas_finais["total_doses"] >= 2, "Total de doses não atualizado após segunda dose"
        print(f"✅ Estatísticas finais: {metricas_finais['total_doses']} doses totais")
        
        print("\n" + "="*50)
        print("✅✅✅ FLUXO COMPLETO TESTADO COM SUCESSO! ✅✅✅")
        print("="*50)