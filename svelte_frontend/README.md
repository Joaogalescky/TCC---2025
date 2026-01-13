# Frontend - Sistema de Eleição com Criptografia Homomórfica

## Descrição

Este diretório implementa a interface de usuário do sistema de eleição eletrônico com criptografia homomórfica. Desenvolvida com Svelte 5 e SvelteKit, a aplicação oferece uma experiência moderna e responsiva para o processo democrático digital, servindo como camada de apresentação que interage com o backend criptográfico.

## Arquitetura e Tecnologias

### Framework Principal
- **Svelte 5**: Framework reativo para construção de interfaces de usuário
- **SvelteKit**: Meta-framework que fornece roteamento, SSR e outras funcionalidades avançadas
- **TypeScript**: Linguagem de programação tipada para maior robustez do código

### Estilização e UI
- **Tailwind CSS 4**: Framework CSS utilitário para estilização responsiva
- **@tailwindcss/typography**: Plugin para tipografia aprimorada

### Ferramentas de Desenvolvimento
- **Vite**: Bundler e servidor de desenvolvimento
- **Vitest**: Framework de testes unitários
- **Playwright**: Ferramenta para testes end-to-end
- **ESLint**: Linter para análise estática de código

## Estrutura do Projeto

```
svelte_frontend/
├── src/
│   ├── lib/
│   │   ├── api.ts              # Cliente HTTP para comunicação com backend
│   │   ├── components/         # Componentes reutilizáveis
│   │   │   └── Toast.svelte    # Componente de notificações
│   │   └── stores/             # Gerenciamento de estado global
│   │       └── auth.ts         # Store de autenticação
│   ├── routes/                 # Páginas da aplicação
│   │   ├── +layout.svelte      # Layout base da aplicação
│   │   ├── +page.svelte        # Página inicial (redirecionamento)
│   │   ├── election/           # Módulo de eleições
│   │   ├── login/              # Módulo de autenticação
│   │   └── register/           # Módulo de cadastro
│   ├── app.html               # Template HTML base
│   └── app.d.ts               # Definições de tipos TypeScript
├── static/                    # Arquivos estáticos
├── tests/                     # Testes automatizados
└── package.json              # Configurações e dependências
```

## Funcionalidades Implementadas

### 1. Sistema de Autenticação
- **Login**: Autenticação via email/senha com tokens JWT
- **Registro**: Cadastro de novos usuários no sistema
- **Gerenciamento de Sessão**: Persistência de estado de autenticação

### 2. Interface de Votação
- **Listagem de Eleições**: Visualização de eleições disponíveis
- **Seleção de Candidatos**: Interface para escolha de candidatos
- **Processo de Votação**: Submissão segura de votos criptografados

### 3. Atualizações em Tempo Real
- **Server-Sent Events (SSE)**: Recebimento de atualizações automáticas
- **Sincronização de Estado**: Atualização dinâmica da interface

### 4. Gerenciamento de Estado
- **Svelte Stores**: Gerenciamento reativo do estado da aplicação
- **Persistência Local**: Armazenamento de tokens de autenticação

## Configuração e Execução

### Pré-requisitos
- Node.js (versão 18 ou superior)
- npm, pnpm ou yarn

### Instalação de Dependências
```bash
npm install
```

### Execução em Modo de Desenvolvimento
```bash
npm run dev
```
A aplicação estará disponível em `http://localhost:5173`

### Execução com Abertura Automática do Navegador
```bash
npm run dev -- --open
```

### Construção para Produção
```bash
npm run build
```

### Visualização da Build de Produção
```bash
npm run preview
```

### Execução de Testes
```bash
# Testes unitários
npm run test:unit

# Todos os testes
npm run test
```

## Comunicação com Backend

A aplicação frontend comunica-se com o backend FastAPI através de uma API REST implementada no arquivo `src/lib/api.ts`. As principais operações incluem:

### Endpoints de Autenticação
- `POST /auth/token`: Obtenção de token de acesso
- `POST /users`: Registro de novos usuários

### Endpoints de Eleições
- `GET /elections`: Listagem de eleições disponíveis
- `GET /elections/{id}/candidates`: Obtenção de candidatos por eleição

### Endpoints de Votação
- `POST /vote/election/{id}`: Submissão de voto criptografado
- `GET /vote/results/{id}`: Consulta de resultados da eleição

## Segurança e Privacidade

### Autenticação
- Utilização de tokens JWT para autenticação stateless
- Armazenamento seguro de tokens no localStorage
- Validação automática de expiração de tokens

### Comunicação
- Headers de autorização em todas as requisições autenticadas
- Tratamento de erros de autenticação com redirecionamento automático

### Interface de Usuário
- Validação de formulários no lado cliente
- Feedback visual para operações assíncronas
- Tratamento de estados de carregamento e erro

## Considerações de Desenvolvimento

### Padrões de Código
- Utilização de TypeScript para tipagem estática
- Componentes Svelte com sintaxe moderna (runes)
- Separação clara entre lógica de negócio e apresentação

### Responsividade
- Design responsivo utilizando Tailwind CSS
- Adaptação para diferentes tamanhos de tela
- Acessibilidade básica implementada

### Performance
- Lazy loading de rotas via SvelteKit
- Otimização automática de bundles via Vite
- Gerenciamento eficiente de estado reativo

## Integração com Sistema Criptográfico

O frontend atua como interface transparente para o sistema criptográfico:
- **Abstração Criptográfica**: Oculta a complexidade da criptografia homomórfica do usuário
- **Transmissão Segura**: Envia dados de votação via HTTPS para processamento criptográfico
- **Validação de Integridade**: Recebe confirmações sem exposição de dados sensíveis
- **Apresentação de Resultados**: Exibe contagens descriptografadas mantendo privacidade individual