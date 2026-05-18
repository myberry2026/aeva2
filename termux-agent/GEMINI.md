# Phone Vision Memory - Project Structure

## Folder Organization

- **humanoid_agent.py**: Core agent logic.
- **`benchmarks/`**: Benchmarking scripts and datasets (e.g., `benchmark_100.json`, `benchmark_runner_100.py`).
- **`data/`**: Static data files and artifacts.
  - **`xml/`**: Historical UI XML dumps.
  - **`screenshots/`**: Historical screenshots.
  - **`inventory/`**: Extracted UI inventory text files.
- **`demos/`**: HUD and overlay demonstrations.
- **`logs/`**: Runtime logs and step-by-step run directories (created automatically).
- **`profiling/`**: Performance and latency profiling scripts.
- **`scripts/`**: Miscellaneous utility and experimental scripts.
- **`tasks/`**: App-specific or task-specific logic (e.g., `tasks/zhihu/`).
- **`tests/`**: Unit and integration tests for models and components.
- **`vendor/`**: Third-party binaries and assets (e.g., `ADBKeyboard.apk`).

## Usage Guidelines

- Always run scripts from the **project root** directory.
- **System Health Check**: Run `python scripts/health_check.py` to verify ADB, Langfuse, and LLM connectivity.
- **Run Agent**: Use `./run.sh "your goal"` or `python agents/humanoid_agent.py`.
- For benchmarking, use `python benchmarks/benchmark_runner_100.py`.
- Common scratch files like `test.png` and `dump.xml` are maintained in the root for quick iteration.
