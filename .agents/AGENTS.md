# Home Agent Workspace Rules & Context

## Hardware Context & Constraints
- **Current Development Hardware**: MacBook Air M4 (Fanless).
  - *Constraint*: Basic fanless MacBook Air M4 heats up quickly and throttles performance under sustained heavy local LLM loads.
  - *Rule*: Keep current features lightweight. Avoid implementing features that require continuous background generation, large RAG document chunking/embeddings, or real-time audio streaming (STT/TTS) while developing on this machine.
- **Target Deployment Hardware**: Mac Mini M4 Pro (Active Cooling).
  - *Context*: The user is planning to purchase a Mac Mini M4 Pro to serve as a dedicated, cooled, high-bandwidth home server.
  - *Rule*: Heavyweight features (Speech-to-Text via Whisper, Text-to-Speech via Kokoro/Piper, Semantic Document Vault, background IMAP email analysis) are planned for implementation and profiling once the Mac Mini M4 Pro setup is active.

## Active Priority Roadmap (MacBook Air Friendly)
1. Proactive Telegram alerts (Fast, simple APScheduler database scans + Telegram push).
2. Calendar conflict warning (Zero-load frontend-only validation).
3. Chat budgeting consultant (Fast read queries + one-shot short assistant answers).
