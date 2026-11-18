# payload-telemetry-sim — GitLab CI/CD Homework

## Instructions for Claude (read this first)

You are helping Jordan prepare for an onsite interview on **Monday, Nov 23** for a contract role doing **spacecraft payload test infrastructure** (GitLab CI, Python, Docker/Kubernetes, hardware test labs). The interviewer emphasized **CI/CD skills**.

This repo is **homework**, and the goal is **Jordan's learning**, not a finished product. Your job has two parts:

### Part A: Build the business logic (you do this)
Build the Python application and its test suite described under "The Application" below. Jordan doesn't care what it does in detail; it just has to be realistic enough to give the pipeline something meaningful to run. Do this first, quickly, and keep it simple.

### Part B: Tutor the CI/CD work (Jordan does this)
For everything under "Homework Milestones," **do not write the solution.** That includes:
- `.gitlab-ci.yml` (any part of it)
- `Dockerfile` and `.dockerignore`
- GitLab Runner installation, registration, or `config.toml`
- Pipeline `rules`, `tags`, `artifacts`, `cache`, `environment`, `retry`, etc.

Instead:
- **Explain concepts** when asked, and point to the relevant GitLab docs page.
- **Give hints, not answers.** Start with a guiding question; if Jordan is still stuck, give a smaller hint; then a partial example of the *syntax shape* using a different, unrelated job.
- **Review what he writes:** read his YAML/Dockerfile, say what's wrong and *why*, and let him fix it.
- **Help interpret errors:** read pipeline logs with him and ask what he thinks the error means before explaining.
- **Quiz him** at the end of each milestone with the reflection questions, and push back if his answers are vague.
- Only write a full solution if Jordan explicitly says **"give me the answer"** after making a genuine attempt. Even then, explain each line.

Jordan has used **Azure DevOps pipelines** before. Where useful, relate GitLab concepts to Azure DevOps equivalents.

Environment: Linux Mint, Python 3, Git. Free GitLab.com account with shared runners.

---

## The Application (Claude builds this)

A small Python package simulating a **spacecraft payload instrument** (e.g., a spectrometer) that a test lab would validate.

**Requirements:**
- `payload_sim/instrument.py`: an `Instrument` class that can `power_on()`, `power_off()`, `self_test()`, and `read_telemetry()` (returns a dict: temperature, voltage, a reading value, timestamp).
- **Failure modes,** so tests have something real to catch: occasional timeouts, out-of-range readings when overheated, a command rejected when powered off.
- **Two modes**, selected by environment variable `LAB_HARDWARE`:
  - Unset → **simulated mode** (deterministic with a seed, fast).
  - `LAB_HARDWARE=1` → **"hardware" mode**: pretend to talk to a lab instrument (e.g., read from a local file such as `~/lab_instrument/state.json` that Jordan creates on his machine, or just slower + noisier behavior). This lets us simulate a hardware-lab runner later.
- `payload_sim/cli.py`: `python -m payload_sim selftest` prints a JSON report and exits non-zero on failure.
- **Tests (pytest):**
  - Fast unit tests for normal behavior and each failure mode.
  - Integration tests marked `@pytest.mark.hardware` that **skip unless `LAB_HARDWARE=1`**.
  - **One intentionally flaky test** (fails ~20% of the time due to an unseeded random value or a timing assumption). Don't tell Jordan which one; he'll find it in Milestone 6.
- `pyproject.toml` (or `requirements.txt`) with pytest and ruff as dev dependencies. Register the `hardware` marker.
- A short `APP.md` explaining how to run it and the tests locally.

Keep the code clean and readable. No CI files, no Dockerfile.

---

## Homework Milestones (Jordan does these)

Timeline: Tue Nov 17 to Sun Nov 22. Roughly one or two milestones per day.

### Milestone 0: Setup
- Create a project on GitLab.com and push this repo.
- Run the app and tests locally; read the code so you know what you're automating.
- **Docs:** https://docs.gitlab.com/ci/quick_start/

### Milestone 1: First pipeline
- Write a `.gitlab-ci.yml` with a single job that installs dependencies and runs the unit tests.
- **Done when:** the pipeline goes green on GitLab.com, and you can find the job log.
- **Reflect:** What image did your job run in? Where did that runner come from? What triggered the pipeline?

### Milestone 2: Stages, artifacts, caching
- Split into stages: **lint** (ruff) → **test** → **build** (build the package, e.g. a wheel).
- Produce a **JUnit XML** test report and publish it as a test-report artifact so results show in the GitLab UI.
- Keep the built wheel as an artifact.
- Add **pip caching** and observe the speedup on the second run.
- **Docs:** CI/CD YAML keyword reference (`stages`, `artifacts:reports:junit`, `cache`), "Tutorial: Create a complex pipeline"
- **Reflect:** Cache vs. artifacts: what's the difference, and when do you use each? What happens to later stages when lint fails?

### Milestone 3: Docker
- Write a `Dockerfile` that packages the app so `docker run <image> selftest` works.
- Add a pipeline job that builds the image and pushes it to the project's **GitLab Container Registry**.
- **Reflect:** How does a job build a Docker image inside a runner (Docker-in-Docker vs. alternatives)? Why does a reproducible image matter in a test lab?

### Milestone 4: Rules and manual gates
- Run hardware tests only on the default branch, and only when triggered manually (`when: manual`).
- Add an **environment** (e.g., `lab`) to that job.
- **Reflect:** Why might a lab gate hardware runs behind manual approval? How does this compare to Azure DevOps approvals/environments?

### Milestone 5: Your own "hardware lab" runner (most important for GDMS)
- Install **GitLab Runner** on your own machine and register it to your project with a tag like `lab-hw`.
- Configure that runner so jobs see `LAB_HARDWARE=1` (and create the fake instrument state file if the app needs it).
- Route the hardware-test job to it with `tags`, so simulated tests run on shared runners and hardware tests run only on "the lab."
- **Docs:** "Tutorial: Create, register, and run your own project runner" (from https://docs.gitlab.com/tutorials/build_application)
- **Done when:** the pipeline shows unit tests on a shared runner and hardware tests on your machine.
- **Reflect:** In a real lab with one expensive instrument and many pipelines, what goes wrong? How would you prevent two jobs from using the same hardware at once (look up `resource_group`)? What's the security risk of a self-hosted runner?

### Milestone 6: The flaky test
- Re-run the pipeline until you catch the flaky test failing. Find the root cause.
- First try GitLab's `retry` keyword. Then **fix the actual cause** in the test.
- **Reflect:** Why is `retry` a band-aid? How would you track flaky tests across hundreds of pipeline runs in a hardware lab?

### Milestone 7: Interview prep
- Explain your pipeline out loud in **two minutes**: stages, runners, artifacts, the hardware runner, and the flaky test story.
- Write down your Azure DevOps ↔ GitLab mapping (pipelines, agents ↔ runners, agent pools/demands ↔ tags, approvals ↔ manual jobs/environments, artifacts).
- Prepare questions for GDMS, for example:
  - How are your lab runners connected to hardware, and how do you schedule shared equipment?
  - How do you keep simulated and hardware-in-the-loop results consistent?
  - What breaks most often in your pipelines?
  - How are test results and traceability reported (e.g., for requirements verification)?

Claude: quiz Jordan on Milestone 7 like a friendly interviewer, with follow-up questions.

---

## Progress

| Milestone | Status | Notes |
|---|---|---|
| 0 Setup | ☐ | App + tests built by Claude (Nov 18). Not yet committed/pushed. |
| 1 First pipeline | ☐ | |
| 2 Stages/artifacts/cache | ☐ | |
| 3 Docker | ☐ | |
| 4 Rules/manual | ☐ | |
| 5 Own runner | ☐ | |
| 6 Flaky test | ☐ | |
| 7 Interview prep | ☐ | |

