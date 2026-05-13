# architecture.md — Structural rules of this project

> What a new developer needs to avoid breaking conventions.
> **Written by you.** The agent reads it before planning major changes.

---

## Stack and layers

<!-- Describe the layers of your application and their responsibilities.
Example for .NET Clean Architecture:
- Domain: entities, value objects, repository interfaces. No external dependencies.
- Application: use cases, DTOs, application services. Depends only on Domain.
- Infrastructure: repository implementations, EF context, external services.
- API: controllers, middlewares, Program.cs. Depends on Application and Infrastructure.
-->

TODO: document your layers here.

---

## Naming conventions

<!-- e.g. PascalCase for classes, camelCase for variables, kebab-case for routes. -->

---

## Where things go

<!-- Tests next to code or in a separate folder, configs in /config, etc. -->

---

## Restrictions

<!-- Protected files/folders, banned dependencies, patterns we don't use. -->
- No force push to main or develop.
- No new dependencies without justification in the PR.
- No hardcoded secrets — always from env vars or .env.

---

## Important architectural decisions

<!-- ADR summaries. Details live in memory/decisions.md. -->
