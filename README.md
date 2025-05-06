# Trabalho de Conclusão de Curso - 3° TADS | 2025

Repositório para o Trabalho de Conclusão de Curso (TCC) do curso de Tecnologia em Análise e Desenvolvimento de Sistemas - 3° TADS | Instituto Federal do Paraná - IFPR.

**Aluno:** João Vitor Campõe Galescky  
**Orientador:** Prof. M.e Edmar André Bellorini  
**Co-orientador:** Prof. Dr. Darlon Vasata

---

## Tema

**Criptografia Homomórfica Aplicada em um Sistema de Eleição para Dispositivos Móveis**

Este projeto propõe a implementação de um sistema de eleição eletrônico que utiliza criptografia homomórfica para garantir a privacidade e a segurança dos votos, mesmo durante o processamento. A aplicação será projetada inicialmente para dispositivos móveis, com possibilidade de adaptação posterior para _web_.

---

## Objetivos
### Objetivo Geral
Este trabalho tem como objetivo avaliar a viabilidade do uso da Criptografia Homomórfica em um sistema de eleição.

### Objetivos Específicos
- Avaliar a viabilidade da aplicação da criptografia totalmente homomórfica (FHE) em sistemas de eleição;
- Desenvolver um protótipo funcional de uma aplicação de eleição segura utilizando _Svelte_ no frontend e _FastAPI_ no _backend_;
- Utilizar o esquema de criptografia BFV (Brakerski/Fan-Vercauteren) com a biblioteca _Pyfhel_;
- Armazenar votos criptografados em banco de dados relacional (_MySQL_);
- Garantir segurança, confidencialidade, integridade e anonimato durante o processo de eleição.

---

## Tecnologias Utilizadas

### Frameworks
- [Svelte](https://svelte.dev) – Interface da aplicação para dispositivos móveis e web;
- [FastAPI](https://fastapi.tiangolo.com) – Backend em _Python_ para integração com a biblioteca de criptografia.

### Linguagens
- _JavaScript_ (_frontend_);
- _Python_ (_backend_);
- _SQL_ (banco de dados).

### Bibliotecas e Dependências
- [Pyfhel](https://github.com/ibarrond/Pyfhel) – Biblioteca de criptografia homomórfica baseada em BFV.

### Banco de Dados
- [MySQL](https://www.mysql.com) – Armazenamento dos votos criptografados e dados auxiliares.

---

## Ferramentas de Desenvolvimento

- [Visual Studio Code](https://code.visualstudio.com) – Editor de código-fonte;
- [MySQL Workbench](https://www.mysql.com/products/workbench) – Modelagem e administração do banco de dados;
- [Figma](https://www.figma.com) – Protótipos de interface e fluxo de navegação;
- [Mermaid](https://mermaid.js.org) – Diagramação de fluxos, sequências e arquitetura.

---

## Esquema Criptográfico

- **BFV (Brakerski-Fan-Vercauteren):** Esquema de criptografia homomórfica que permite operações de adição e multiplicação sobre dados criptografados, ideal para contagem de votos de forma segura e privada.

---

## Instituição

[![IFPR Logo](https://user-images.githubusercontent.com/126702799/234438114-4db30796-20ad-4bec-b118-246ebbe9de63.png)](https://www.ifpr.edu.br)

**Instituto Federal do Paraná - IFPR - Campus [Cascavel](https://ifpr.edu.br/cascavel/)**  
Curso: Tecnologia em Análise e Desenvolvimento de Sistemas.

---

> Documento elaborado com [StackEdit](https://stackedit.io).
