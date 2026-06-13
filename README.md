# ai-video-workflow

End-to-end AI video automation: script → shot generation → human review → YouTube publish, with a durable task queue & dashboard.

## Business Context

- **Category:** security and governance tool
- **Audience:** builders and operators who need safer repositories, cleaner handoffs, and repeatable security checks.
- **Repository status:** Public repository. Keep examples, docs, and issues free of credentials, private data, and machine-specific paths.
- **Topics:** ai-video, automation, content-creation, fastapi, orchestration, pixverse, python, video-generation, workflow, youtube

## What This Project Is For

- End-to-end AI video automation: script → shot generation → human review → YouTube publish, with a durable task queue & dashboard.
- Find repository risks early without exposing secrets in reports.
- Make security review repeatable across public and private codebases.

## Where It Fits

This repository belongs in the trust-and-safety layer of the workbench: it helps make code, configuration, and public handoffs safer before they are reused or shown to clients.

## Technical Overview

- **Primary language:** Python
- **Detected stack:** Python, Node.js, Python project metadata, Python dependencies, Docker, Docker Compose, Next.js, React, Tailwind CSS, TypeScript
- **Default branch:** `main`
- **Visibility:** `PUBLIC`
- **License:** Apache License 2.0

## Repository Map

- `api`
- `docs`
- `tests`
- `.devcontainer`
- `.dockerignore`
- `.env.example`
- `Dockerfile`
- `LICENSE`
- `NOTICE`
- `ORCHESTRATOR_README.md`
- `README.md`
- `SECURITY.md`

## Quick Start

Use the commands that match the current project state:

```bash
npm install
npm run dev
npm start
npm run build
npm run lint
```

| Command | Purpose |
|---|---|
| `npm install` | Install project dependencies. |
| `npm run dev` | next dev |
| `npm start` | next start |
| `npm run build` | next build |
| `npm run lint` | eslint |

## Operating Notes

- Keep real credentials out of the repository. Use local environment files, GitHub repository secrets, or the deployment platform secret manager.
- If a `.env.example` file exists, treat it as documentation only; never commit filled-in `.env` files.
- Before publishing screenshots, demos, or client examples, remove private names, internal paths, account IDs, and API endpoints.
- The `Repository Hygiene` workflow is a lightweight guardrail, not a replacement for product-specific tests.

## Delivery Checklist

- [ ] README describes the user, business outcome, and operating boundary.
- [ ] Setup or preview commands are current and do not rely on private machine state.
- [ ] No real secrets, private user data, or machine-local state are tracked.
- [ ] Screenshots, demos, or sample outputs are safe to share publicly when the repository is public.
- [ ] Product-specific tests or smoke checks are documented before production use.

## Roadmap

- Tighten the fastest path from clone to useful demo.
- Add project-specific screenshots, sample outputs, or a short walkthrough where useful.
- Promote repeated manual steps into scripts, tests, or documented workflows.
- Keep security, privacy, and licensing boundaries explicit as the project evolves.

## Maintainer Notes

Maintained by [Tony Sheng](https://github.com/shengdabai). This README is written as a business-facing handoff: it should help a future collaborator, client, or reviewer understand why the repository exists, how to inspect it, and what must be true before it is reused or shipped.
