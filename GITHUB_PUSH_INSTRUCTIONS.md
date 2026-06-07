# Pushing to GitHub - Instructions

## 1. Revoke the exposed token NOW


## 2. Create the GitHub repo

- Go to https://github.com/new
- Name: `ai-engineer-portfolio`
- Description: "Self-hosted LLM agent on a laptop GPU - RAG, fine-tuning, tool calling"
- **Do NOT** initialize with README, .gitignore, or license (we have them)
- Visibility: Public (for portfolio) or Private
- Click "Create repository"

## 3. Push the code

### Option A: HTTPS with credential manager (easiest)

```bash
cd "C:\Users\aborb\.minimax-agent\projects\ai-engineer-portfolio"
git remote add origin https://github.com/YOUR-USER/ai-engineer-portfolio.git
git push -u origin main
```

When prompted:
- Username: your GitHub username
- Password: paste the **new** token (not the old one)

Windows will save it in the Credential Manager, so future pushes don't ask.

### Option B: Environment variable (more secure, no saved credentials)

```powershell
$env:GITHUB_TOKEN = "ghp_NEW_TOKEN_HERE"
git remote add origin https://github.com/YOUR-USER/ai-engineer-portfolio.git
git push https://x-access-token:$env:GITHUB_TOKEN@github.com/YOUR-USER/ai-engineer-portfolio.git main
```

The env var disappears when you close the shell.

### Option C: SSH (most secure, recommended for daily use)

```bash
# Generate key
ssh-keygen -t ed25519 -C "your_email@example.com"
# (press enter 3 times)

# Copy public key
cat ~/.ssh/id_ed25519.pub
```

Then:
1. Go to https://github.com/settings/keys
2. Click "New SSH key"
3. Paste the key, save

```bash
cd "C:\Users\aborb\.minimax-agent\projects\ai-engineer-portfolio"
git remote add origin git@github.com:YOUR-USER/ai-engineer-portfolio.git
git push -u origin main
```

## 4. After pushing

- Go to your repo on GitHub
- Check that README renders correctly (the badges might not show in local preview)
- Add a description and topics (e.g., `ai-agents`, `ollama`, `rag`, `fine-tuning`, `lora`)
- Enable Issues if you want feedback
- Optional: enable GitHub Pages for a public landing

## 5. Recommended next steps

- Add a GitHub Actions workflow to run the 89 tests on every push
- Set up branch protection on `main` (require tests to pass before merge)
- Add a `requirements-dev.txt` for test-only deps (pytest, pytest-asyncio, slowapi, markitdown)
