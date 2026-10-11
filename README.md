# trueforge-skills

Skills for a local [TrueForge](https://github.com/truefoundry/trueforge) agent harness. They're written for a small local model (Qwen3 8B): each step is one exact tool call, and scripts do the data handling so the model never retypes numbers.

| Skill | What it does |
|---|---|
| `skills/model-leaderboard-dashboard` | Fetches public open-model leaderboards with Exa, extracts every table into JSON, and builds a self-contained interactive `dashboard.html` |

Register a skill in TrueForge (Settings → Skills) as a Git skill with URL `https://github.com/Adamsa58/trueforge-skills`, ref `main`, path `skills/<name>`.

Scripts use the Python 3 standard library only.
