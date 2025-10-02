# TODO - CoinWatch Development Roadmap

## ✅ Completed

### Phase 1 - Quick Wins (Partially Complete)
- [x] Dry run mode (`--dry-run` flag)
- [x] Config validator (`--validate` flag)
- [x] Project renamed to CoinWatch
- [x] Updated README with new features

## 🔄 In Progress

### Phase 1 - Quick Wins (Remaining)
- [ ] **Better error messages**
  - Replace stack traces with user-friendly messages
  - Add context to API errors
  - Improve config loading error messages

- [ ] **CLI for coin management**
  - `./coinwatch add <coin-id> --ath 50,60,70 --price 80000,70000`
  - `./coinwatch list`
  - `./coinwatch remove <coin-id>`
  - `./coinwatch test` (alias for --dry-run)

## 📋 Planned

### Phase 2 - Modular Architecture (1 day)
- [ ] **Refactor to modular structure**
  ```
  coinwatch/
    ├── core/
    │   ├── fetcher.py      # Data fetching
    │   ├── analyzer.py     # Alert logic
    │   └── storage.py      # Config & state
    ├── notifiers/
    │   ├── base.py         # Abstract notifier
    │   ├── discord.py      # Discord impl
    │   ├── telegram.py     # Telegram impl
    │   └── webhook.py      # Generic webhook
    ├── cli.py              # CLI interface
    └── main.py             # Entry point
  ```

- [ ] **Plugin system for notifiers**
  - Abstract base class for notifiers
  - Easy to add new notification channels

- [ ] **Telegram support**
  - Implement Telegram notifier
  - Add to config

### Phase 3 - Advanced Features (weekend)
- [ ] **Docker support**
  - Dockerfile
  - docker-compose.yml
  - One-command deployment

- [ ] **Simple web dashboard**
  - View last alerts
  - See next check time
  - Health status

- [ ] **One-liner install**
  - `curl -sSL install.sh | bash`
  - Auto-setup script

- [ ] **Example configs**
  - `configs/conservative.json`
  - `configs/aggressive.json`
  - `configs/hodler.json`

### Future Enhancements
- [ ] More technical indicators (RSI, MACD)
- [ ] Portfolio tracking
- [ ] Email alerts
- [ ] Slack integration
- [ ] Multi-profile support
- [ ] Web UI for management
- [ ] Historical alert log
- [ ] Alert statistics/analytics

## 🐛 Known Issues
- None currently

## 💡 Ideas to Consider
- Hosted SaaS version for non-technical users
- Mobile app notifications
- Alert templates/presets
- Community coin lists
- Price prediction integration
- DeFi protocol monitoring
