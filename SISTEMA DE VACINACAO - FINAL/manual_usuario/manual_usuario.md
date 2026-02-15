# Manual do Usuário - NASST Digital v1.0

Sistema de Controle de Vacinação de Servidores

## Sumário

1. [Introdução](#introdução)
2. [Acesso ao Sistema](#acesso-ao-sistema)
3. [Dashboard](#dashboard)
4. [Módulo de Servidores](#módulo-de-servidores)
5. [Módulo de Vacinação](#módulo-de-vacinação)
6. [Módulo de Campanhas](#módulo-de-campanhas)
7. [Módulo de Relatórios](#módulo-de-relatórios)
8. [Administração do Sistema](#administração-do-sistema)
9. [Perguntas Frequentes](#perguntas-frequentes)
10. [Suporte](#suporte)

---

## Introdução

O **NASST Digital** é um sistema desenvolvido para gerenciar e controlar a vacinação de servidores públicos. Ele substitui planilhas e controles manuais, oferecendo uma plataforma centralizada, segura e com capacidade de gerar relatórios gerenciais.

### Objetivos do Sistema

- Centralizar o cadastro de todos os servidores
- Registrar e controlar as vacinas aplicadas
- Gerenciar campanhas de vacinação
- Gerar relatórios de cobertura vacinal
- Alertar sobre doses atrasadas e próximas do vencimento
- Garantir a rastreabilidade através de logs de auditoria

### Perfis de Acesso

| Perfil | Permissões |
|--------|------------|
| **ADMIN** | Acesso total a todas as funcionalidades, incluindo administração de usuários e logs |
| **OPERADOR** | Pode cadastrar servidores, registrar vacinações e visualizar relatórios |
| **VISUALIZADOR** | Acesso apenas de consulta a dashboards e relatórios |

---

## Acesso ao Sistema

### Tela de Login

1. Abra o navegador e acesse o endereço do sistema
2. Na tela de login, informe:
   - **Usuário**: seu login de acesso
   - **Senha**: sua senha cadastrada
3. Clique em **"Entrar"**

![Tela de Login](imagens/tela_login.png)

### Primeiro Acesso

Na primeira vez que o sistema for instalado, existe um usuário padrão:

- **Usuário**: admin
- **Senha**: admin123

**IMPORTANTE**: Altere a senha do administrador imediatamente após o primeiro acesso!

### Recuperação de Senha

Caso esqueça sua senha, entre em contato com o administrador do sistema para realizar a redefinição.

---

## Dashboard

O Dashboard é a primeira tela exibida após o login. Ele apresenta um resumo das principais métricas do sistema.

### Métricas Principais

![Dashboard](imagens/dashboard.png)

| Card | Descrição |
|------|-----------|
| **Servidores Ativos** | Total de servidores com situação ativa |
| **Doses Aplicadas** | Total de vacinas aplicadas |
| **Cobertura** | Percentual de servidores vacinados |
| **Atrasados** | Número de doses com data de retorno vencida |

### Gráficos

- **Cobertura por Lotação**: Comparativo de servidores vacinados por setor
- **Doses nos Últimos 6 Meses**: Evolução mensal das aplicações

### Consulta Rápida

No rodapé do Dashboard, você pode fazer uma busca rápida por servidores digitando nome, CPF ou matrícula.

---

## Módulo de Servidores

O módulo de servidores permite gerenciar todo o cadastro de funcionários.

### Consultar Servidores

![Consulta de Servidores](imagens/consulta_servidores.png)

1. Acesse **Servidores** > **Consultar**
2. Utilize os filtros disponíveis:
   - Nome
   - Superintendência
   - Lotação
   - Situação (Ativo/Inativo)
3. Clique em **"Buscar"**
4. Os resultados serão exibidos em uma tabela
5. Utilize os botões para exportar os dados (CSV ou Excel)

### Cadastrar Servidor Individual

1. Acesse **Servidores** > **Cadastrar**
2. Preencha os dados pessoais:
   - Nome completo (obrigatório)
   - CPF (obrigatório, com validação automática)
   - Data de nascimento
   - Sexo
   - Telefone
   - E-mail
3. Preencha os dados funcionais:
   - Número funcional (gerado automaticamente, mas pode ser alterado)
   - Número de vínculo
   - Superintendência
   - Setor/Lotação
   - Cargo
   - Local físico
   - Tipo de vínculo
   - Situação funcional
   - Data de admissão
4. Clique em **"Salvar Servidor"**

### Importar Servidores em Lote

Para cadastrar vários servidores de uma vez:

1. Acesse **Servidores** > **Importar**
2. Prepare um arquivo Excel ou CSV com os dados
3. Faça o upload do arquivo
4. O sistema detectará automaticamente as colunas
5. Confirme o mapeamento das colunas
6. Configure as opções:
   - **Servidores já cadastrados**: O que fazer com duplicatas
   - **Criar novos servidores**: Se deve cadastrar novos registros
   - **Atualizar campos vazios**: Se deve preencher campos vazios nos registros existentes
7. Clique em **"Executar Importação"**

### Estrutura do Arquivo para Importação

| Coluna | Descrição | Obrigatório |
|--------|-----------|-------------|
| NOME | Nome completo do servidor | Sim |
| CPF | CPF (com ou sem pontuação) | Sim |
| NUMFUNC | Número funcional | Sim |
| NUMVINC | Número do vínculo | Sim |
| LOTACAO | Setor de lotação | Sim |
| SUPERINTENDENCIA | Superintendência | Não |
| CARGO | Cargo do servidor | Não |
| TELEFONE | Telefone para contato | Não |
| EMAIL | E-mail institucional | Não |
| DATA_NASCIMENTO | Data de nascimento | Não |
| DATA_ADMISSAO | Data de admissão | Não |

---

## Módulo de Vacinação

O módulo de vacinação permite registrar as aplicações de vacinas.

### Registrar Vacinação Individual

1. Acesse **Vacinação** > **Individual**
2. Busque o servidor pelo nome, CPF ou matrícula
3. Selecione o servidor na lista
4. Preencha os dados da vacinação:
   - Vacina (selecione da lista ou digite "Outra")
   - Dose (1ª Dose, 2ª Dose, Reforço, etc.)
   - Número do lote (marque a opção se não tiver o lote)
   - Data da aplicação
   - Data de retorno (calculada automaticamente)
   - Local da aplicação
   - Via de aplicação
   - Campanha (opcional)
5. Clique em **"Salvar Vacinação"**

### Vacinação Múltipla

Para aplicar a mesma vacina em um grupo de servidores:

1. Acesse **Vacinação** > **Múltipla**
2. Selecione os filtros desejados (superintendência, situação)
3. Escolha a vacina e dose
4. Defina a data de aplicação e retorno
5. Informe o lote (opcional)
6. Clique em **"Buscar Servidores"**
7. Revise a lista de servidores
8. Clique em **"Aplicar Vacina a Todos"**

### Importar Vacinação em Lote

Para registrar várias vacinações de uma vez:

1. Acesse **Vacinação** > **Em Lote**
2. Prepare um arquivo com as colunas:
   - `cpf` (obrigatório)
   - `vacina` (obrigatório)
   - `dose` (obrigatório)
   - `data_aplicacao` (formato DD/MM/AAAA)
3. Faça o upload do arquivo
4. Confirme o mapeamento das colunas
5. Clique em **"Validar Dados"**
6. Se tudo estiver correto, clique em **"Importar Todos"**

---

## Módulo de Campanhas

O módulo de campanhas permite gerenciar campanhas de vacinação.

### Listar Campanhas

1. Acesse **Campanhas** > **Listar Campanhas**
2. Utilize os filtros para refinar a busca
3. Para cada campanha, é possível:
   - Ver detalhes
   - Gerar relatório de desempenho
   - Editar (em desenvolvimento)
   - Excluir (apenas ADMIN, e apenas se não houver doses aplicadas)

### Criar Nova Campanha

1. Acesse **Campanhas** > **Nova Campanha**
2. Preencha os dados:
   - Nome da campanha
   - Vacina
   - Período (data início e fim)
   - Status (Planejada, Ativa, Concluída, Cancelada)
   - Público-alvo
   - Descrição
3. Clique em **"Criar Campanha"**

### Relatórios de Campanha

1. Acesse **Campanhas** > **Relatórios**
2. Clique em **"Gerar Relatório Completo"**
3. O sistema exibirá:
   - Estatísticas por status
   - Lista de todas as campanhas
   - Total de doses aplicadas por campanha

---

## Módulo de Relatórios

O módulo de relatórios oferece diversas visualizações dos dados.

### Relatórios Básicos

| Relatório | Descrição |
|-----------|-----------|
| **Cobertura por Lotação** | Vacinação por setor, com filtros por período |
| **Por Superintendência** | Cobertura agrupada por superintendência |
| **Doses Atrasadas** | Lista de doses com data de retorno vencida |
| **Servidores** | Ficha individual do servidor com histórico |

### Relatórios Avançados (ADMIN/OPERADOR)

| Relatório | Descrição |
|-----------|-----------|
| **Tendência Temporal** | Evolução mensal das vacinações |
| **Análise Demográfica** | Perfil dos vacinados (idade, sexo) |
| **Eficiência de Vacinas** | Métricas por tipo de vacina |
| **Metas e Objetivos** | Acompanhamento de metas de cobertura |

### Relatório de Produtividade (ADMIN/OPERADOR)

Este relatório mostra o desempenho da equipe:

1. Acesse **Produtividade**
2. Selecione o período desejado
3. Clique em **"Gerar Relatório"**
4. O sistema exibirá:
   - Ranking de vacinações por usuário
   - Métricas gerais do período
   - Detalhamento por usuário

### Exportar Relatórios

Todos os relatórios podem ser exportados em:
- **CSV**: Para análise em planilhas
- **Excel**: Relatório completo com múltiplas abas
- **PDF**: Para impressão ou compartilhamento

---

## Administração do Sistema

Módulo exclusivo para usuários com perfil **ADMIN**.

### Gerenciar Usuários

![Gerenciar Usuários](imagens/admin_usuarios.png)

1. Acesse **Administração** > **Gerenciar Usuários**
2. Selecione um usuário para editar
3. Opções disponíveis:
   - **Editar Dados**: Alterar nome, nível, lotação
   - **Resetar Senha**: Definir nova senha
   - **Ativar/Desativar**: Controlar acesso
   - **Excluir**: Remover usuário (apenas se não for o próprio)

### Criar Novo Usuário

1. Acesse **Administração** > **Usuários**
2. Preencha:
   - Login (único no sistema)
   - Nome completo
   - Senha
   - Nível de acesso
   - Lotação permitida
3. Clique em **"Criar Usuário"**

### Gerenciar Vacinas

1. Acesse **Administração** > **Vacinas**
2. Visualize a lista de vacinas cadastradas
3. Para cadastrar nova vacina:
   - Nome
   - Fabricante
   - Doses necessárias
   - Intervalo entre doses
   - Via de aplicação
   - Contraindicações

### Utilitários

**Backup do Banco de Dados**
1. Acesse **Administração** > **Utilitários**
2. Clique em **"Criar Backup"**
3. O arquivo será gerado e você poderá fazer o download

**Limpeza de Logs**
1. Defina quantos dias de logs deseja manter
2. Clique em **"Executar Limpeza"**

### Consulta SQL

Para administradores avançados, é possível executar consultas SQL diretamente:

1. Acesse **Administração** > **Utilitários**
2. Digite sua consulta (apenas SELECT é permitido)
3. Clique em **"Executar Consulta"**
4. Os resultados serão exibidos em tabela

---

## Perguntas Frequentes

### 1. Esqueci minha senha. O que fazer?
Entre em contato com o administrador do sistema. Ele poderá resetar sua senha.

### 2. Posso alterar minha própria senha?
Sim! No menu lateral, clique em **"Alterar Minha Senha"**. Você precisará informar sua senha atual e a nova senha.

### 3. O que significa "dose atrasada"?
Uma dose está atrasada quando a data de retorno (data prevista para a próxima dose) já passou e a nova aplicação não foi registrada.

### 4. Posso editar um servidor após cadastrado?
Atualmente, a edição não está disponível. Em caso de erro, é necessário excluir e recadastrar o servidor (apenas ADMIN).

### 5. Como faço para importar vários servidores?
Prepare um arquivo Excel seguindo o modelo disponível na seção de importação e faça o upload.

### 6. O que significa o ID_COMP?
É o identificador único do servidor, formado pela concatenação do número funcional e número de vínculo (ex: 12345-1).

### 7. Posso associar uma vacinação a mais de uma campanha?
Não. Cada vacinação pode ser associada a apenas uma campanha.

### 8. Como vejo o histórico completo de um servidor?
Na consulta de servidores, clique em **"Ver Histórico"** no card do servidor.

---

## Suporte

### Canais de Atendimento

- **E-mail**: suporte@nasst.digital
- **Telefone**: (00) 0000-0000
- **Horário**: Segunda a Sexta, das 8h às 18h

### Reportar Problemas

Ao reportar um problema, informe:
1. Seu nome e perfil de acesso
2. Descrição detalhada do ocorrido
3. Passos para reproduzir o problema
4. Prints da tela (se aplicável)

### Sugestões de Melhoria

O NASST Digital está em constante evolução. Envie suas sugestões para o e-mail de suporte.

---

## Histórico de Versões

| Versão | Data | Principais Mudanças |
|--------|------|---------------------|
| 1.0.0 | 2024 | Versão inicial |

---

© 2024 NASST Digital - Todos os direitos reservados