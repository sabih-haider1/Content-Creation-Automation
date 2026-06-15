# Phase 1: Immediate Tasks

This document tracks the immediate tasks for each team member to refine the project.

## 👤 Sabih (Integrator)
- [ ] **Infrastructure**: Update `docker-compose.yml` and `Dockerfile` to ensure `tokens/` and `output/` folders are persistent.
- [x] **Standards**: Create `CONTRIBUTING.md` defining naming conventions and commit structures.

## 👤 Harmain (Bot & UX)
- [ ] **Command Suite**: Build out the `/settings` command for user preferences (Voice, Niche).
- [ ] **Feedback**: Add status indicators ("typing...", "uploading...") in Telegram during processing.

## 👤 Jaber (AI & Content)
- [ ] **Deep Scraping**: Improve `utils.py` with `BeautifulSoup` for better link content extraction.
- [ ] **Prompt Engineering**: Create script "Personalities" (e.g., Funny, Professional, Documentary).

## 👤 Umer (Video/TTS)
- [ ] **Overlays**: Add subtitle logic to `video_builder.py`.
- [ ] **Voice Library**: Map multiple `edge-tts` voices to the bot selection.

## 👤 Rehan (Backend/Auth)
- [ ] **Auth Security**: Move `client_secret.json` to environment variables or secure storage.
- [ ] **Multi-Platform**: Start mapping TikTok and Instagram API routes using multi-user logic.
