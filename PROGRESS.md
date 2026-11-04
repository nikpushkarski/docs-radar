Current task: T21 — Pre-publication housekeeping complete.
Completed tasks: Added local credential ignore rules; moved the demo question into README quick start; added an MIT licence for original project code/documentation with third-party source material and trademarks excluded. Prior T19 model picker and T21 manifest-layout fixes remain unchanged.
Acceptance evidence / tests: git diff --check passed. git check-ignore confirms .env, .env.local, and .streamlit/secrets.toml are ignored; .env.example remains available to track. Application tests not rerun for documentation/ignore-only changes; previous recorded Windows validation was 289 passing tests and a passing full model-free gate. No native macOS validation or full secret/history audit performed.
Implemented by: Codex
Active mode: tutor
Run mode: extractive default
Key decision or blocker: User authorized these housekeeping changes, commit, and push to existing origin/main; repository visibility is unchanged. MIT covers original work only, not third-party source excerpts or trademarks. Human citation-support review remains pending.
Next smallest action: Confirm the pushed housekeeping commit on GitHub before changing repository visibility.
