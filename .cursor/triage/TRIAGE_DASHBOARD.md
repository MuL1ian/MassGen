# Triage Dashboard

## Triage Progress (Live)

| Metric | Baseline | Current | Delta |
| :-- | --: | --: | --: |
| Total | 622 | 622 | 0 |
| Passed | 518 | 522 | +4 |
| Failed | 56 | 52 | -4 |
| Skipped | 48 | 48 | 0 |

### Progress Log (Snapshots after each completed cluster)

| Cluster | Status | Owner | Total | Passed | Failed | Skipped |
| :-- | :-- | :-- | --: | --: | --: | --: |
| bb85095009 | [x] Resolved | GitHub Copilot | 622 | 519 | 55 | 48 |
| 917dbd053a | [x] Resolved | GitHub Copilot | 622 | 522 | 52 | 48 |

## Clusters

- **Active Clusters**: 47
- **Last Updated**: 2025-12-23

| ID | Count | Exception | Message | Status | Owner | Resolution |
| :--- | :---: | :--- | :--- | :--- | :--- | :--- |
| [3214aa51a1](clusters/cluster_3214aa51a1.md) | 4 | `<unknown>` | `failed on setup with "TypeError: Can't instantiate abstract class MockClaudeCodeAgent without an imp` | [-] Deferred | GitHub Copilot | 4 Fail -> 5 XFail. Refactored fixtures to use temp workspace; deferred due to missing orchestrator features. |
| [917dbd053a](clusters/cluster_917dbd053a.md) | 3 | `<unknown>` | `AssertionError: assert False  +  where False = <AsyncMock name='mock.retrieve' id='<n>'>.called  +  ` | [x] Resolved | GitHub Copilot | 3 Fail -> 3 Pass. Enabled persistent memory retrieval by default. |
| [925e5d67cf](clusters/cluster_925e5d67cf.md) | 3 | `<unknown>` | `assert 0 == 1  +  where 0 = len([])` | [ ] Open | |
| [9cac85ecd5](clusters/cluster_9cac85ecd5.md) | 2 | `<unknown>` | `ValueError: Claude Code backend requires 'cwd' configuration for workspace management` | [ ] Open | |
| [2a747ad546](clusters/cluster_2a747ad546.md) | 1 | `<unknown>` | `AssertionError: Error during fallback test: object Mock can't be used in 'await' expression assert F` | [ ] Open | |
| [10e40617fc](clusters/cluster_10e40617fc.md) | 1 | `<unknown>` | `AssertionError: Error during no stored answer test: object Mock can't be used in 'await' expression ` | [ ] Open | |
| [a6331c8a4f](clusters/cluster_a6331c8a4f.md) | 1 | `<unknown>` | `AssertionError: Error during normal content test: object Mock can't be used in 'await' expression as` | [ ] Open | |
| [ddb4cca0e8](clusters/cluster_ddb4cca0e8.md) | 1 | `<unknown>` | `AssertionError: Read should be blocked from reading .m4v files assert not True` | [ ] Open | |
| [e1b979b82b](clusters/cluster_e1b979b82b.md) | 1 | `<unknown>` | `AssertionError: Read should be blocked from reading .o files assert not True` | [ ] Open | |
| [2265711670](clusters/cluster_2265711670.md) | 1 | `<unknown>` | `AssertionError: Read should be blocked from reading .wma files assert not True` | [ ] Open | |
| [addd89f9c7](clusters/cluster_addd89f9c7.md) | 1 | `<unknown>` | `AssertionError: Regex pattern did not match.   Expected regex: 'Azure OpenAI endpoint URL is require` | [ ] Open | |
| [403c7f4eb0](clusters/cluster_403c7f4eb0.md) | 1 | `<unknown>` | `AssertionError: Regex pattern did not match.   Expected regex: 'Both llm_backend and embedding_backe` | [ ] Open | |
| [e93ca5b364](clusters/cluster_e93ca5b364.md) | 1 | `<unknown>` | `AssertionError: assert 'Invalid output format' in 'VHS is not installed. Please install it from http` | [ ] Open | |
| [5574b4d202](clusters/cluster_5574b4d202.md) | 1 | `<unknown>` | `AssertionError: assert 'Sleep 10s' in '# VHS tape for MassGen terminal recording\n# Auto-generated b` | [ ] Open | |
| [903d89c512](clusters/cluster_903d89c512.md) | 1 | `<unknown>` | `AssertionError: assert 'ag2_lesson_planner' in set()  +  where set() = <massgen.backend.response.Res` | [ ] Open | |
| [f60ae3a821](clusters/cluster_f60ae3a821.md) | 1 | `<unknown>` | `AssertionError: assert 'calculate_sum' in set()  +  where set() = <massgen.backend.response.Response` | [ ] Open | |
| [179e903383](clusters/cluster_179e903383.md) | 1 | `<unknown>` | `AssertionError: assert 'calculate_sum' in {'custom_tool__calculate_sum': RegisteredToolEntry(tool_na` | [ ] Open | |
| [0417872da1](clusters/cluster_0417872da1.md) | 1 | `<unknown>` | `AssertionError: assert 'custom_function' in {'custom_tool__custom_function': RegisteredToolEntry(too` | [ ] Open | |
| [810ae1adca](clusters/cluster_810ae1adca.md) | 1 | `<unknown>` | `AssertionError: assert 'faulty_tool' in set()  +  where set() = <massgen.backend.response.ResponseBa` | [ ] Open | |
| [95e42d89f4](clusters/cluster_95e42d89f4.md) | 1 | `<unknown>` | `AssertionError: assert 'filesystem' not in ['filesystem', 'command_line']` | [ ] Open | |
| [a582835a54](clusters/cluster_a582835a54.md) | 1 | `<unknown>` | `AssertionError: assert 'filesystem' not in ['filesystem', 'workspace_tools', 'command_line']` | [ ] Open | |
| [3cf8378975](clusters/cluster_3cf8378975.md) | 1 | `<unknown>` | `AssertionError: assert 'gemini-3-flash-preview' == 'gemini-<num>-flash'      #x1B[0m#x1B[91m- gemini` | [ ] Open | |
| [bb85095009](clusters/cluster_bb85095009.md) | 1 | `<unknown>` | `AssertionError: assert 'gpt-<num>-codex' == 'gpt-5'      #x1B[0m#x1B[91m- gpt-5#x1B[39;49;00m#x1B[90` | [x] Resolved | GitHub Copilot | 1 Fail -> 1 Pass. Updated build_config tests to expect default gpt-5.1-codex and use context_paths parameter. |
| [08427b80fc](clusters/cluster_08427b80fc.md) | 1 | `<unknown>` | `AssertionError: assert 'langgraph_lesson_planner' in set()  +  where set() = <massgen.backend.respon` | [ ] Open | |
| [d59fb7887b](clusters/cluster_d59fb7887b.md) | 1 | `<unknown>` | `AssertionError: assert 'read_file_content' in {'custom_tool__read_file_content': RegisteredToolEntry` | [ ] Open | |
| [286ae5317d](clusters/cluster_286ae5317d.md) | 1 | `<unknown>` | `AssertionError: assert 'too large' in 'openai api key not found. please set openai_api_key in .env f` | [ ] Open | |
| [a3e3b9a674](clusters/cluster_a3e3b9a674.md) | 1 | `<unknown>` | `AssertionError: assert 0 >= 1  +  where 0 = <AsyncMock name='mock.retrieve' id='<n>'>.call_count  + ` | [ ] Open | |
| [b096158234](clusters/cluster_b096158234.md) | 1 | `<unknown>` | `AssertionError: assert False  +  where False = <function iscoroutinefunction at <hex>>(ag2_lesson_pl` | [ ] Open | |
| [692aca3f58](clusters/cluster_692aca3f58.md) | 1 | `<unknown>` | `AssertionError: assert False  +  where False = <function iscoroutinefunction at <hex>>(langgraph_les` | [ ] Open | |
| [5641729ef8](clusters/cluster_5641729ef8.md) | 1 | `<unknown>` | `AttributeError: 'ChatCompletionsBackend' object has no attribute 'convert_tools_to_chat_completions_` | [ ] Open | |
| [c93cc0fdf9](clusters/cluster_c93cc0fdf9.md) | 1 | `<unknown>` | `AttributeError: 'ClaudeBackend' object has no attribute 'convert_messages_to_claude_format'` | [ ] Open | |
| [e6fef0cb73](clusters/cluster_e6fef0cb73.md) | 1 | `<unknown>` | `AttributeError: <massgen.backend.azure_openai.AzureOpenAIBackend object at <hex>> does not have the ` | [ ] Open | |
| [5be1f2bcf3](clusters/cluster_5be1f2bcf3.md) | 1 | `<unknown>` | `Failed: DID NOT RAISE <class 'ValueError'>` | [ ] Open | |
| [c150c256c0](clusters/cluster_c150c256c0.md) | 1 | `<unknown>` | `ModuleNotFoundError: No module named 'massgen.backend.base_with_mcp'` | [ ] Open | |
| [db017ade3b](clusters/cluster_db017ade3b.md) | 1 | `<unknown>` | `TypeError: Can't instantiate abstract class MockClaudeCodeAgent without an implementation for abstra` | [ ] Open | |
| [5cb1ec0361](clusters/cluster_5cb1ec0361.md) | 1 | `<unknown>` | `TypeError: build_config() got an unexpected keyword argument 'context_path'. Did you mean 'context_p` | [ ] Open | |
| [bc5cf4d958](clusters/cluster_bc5cf4d958.md) | 1 | `<unknown>` | `TypeError: langgraph_lesson_planner() got an unexpected keyword argument 'topic'` | [ ] Open | |
| [4ed328e9fd](clusters/cluster_4ed328e9fd.md) | 1 | `<unknown>` | `TypeError: object async_generator can't be used in 'await' expression` | [ ] Open | |
| [038a7d54eb](clusters/cluster_038a7d54eb.md) | 1 | `<unknown>` | `assert 'The sum of 5 and 3 is 8' in "ToolNotFound: No tool named 'calculate_sum' exists"  +  where "` | [ ] Open | |
| [c66ac77e71](clusters/cluster_c66ac77e71.md) | 1 | `<unknown>` | `assert 'Weather in Tokyo: Rainy, 22°C' in "ToolNotFound: No tool named 'async_weather_fetcher' exist` | [ ] Open | |
| [c6823ff23f](clusters/cluster_c6823ff23f.md) | 1 | `<unknown>` | `assert 'asyncio.get_event_loop()' in '"""\nMCP Client for Tool Execution\n\nThis module handles MCP ` | [ ] Open | |
| [91401191b2](clusters/cluster_91401191b2.md) | 1 | `<unknown>` | `assert (0 == 1)  +  where 0 = len([])` | [ ] Open | |
| [716272239d](clusters/cluster_716272239d.md) | 1 | `<unknown>` | `assert 0 == 2  +  where 0 = len([])` | [ ] Open | |
| [5d454f7b61](clusters/cluster_5d454f7b61.md) | 1 | `<unknown>` | `assert 0 == 2  +  where 0 = len(set())  +    where set() = <massgen.backend.response.ResponseBackend` | [ ] Open | |
| [be6ae6c1bb](clusters/cluster_be6ae6c1bb.md) | 1 | `<unknown>` | `assert 1 == 0` | [ ] Open | |
| [13f1efd663](clusters/cluster_13f1efd663.md) | 1 | `<unknown>` | `assert False` | [ ] Open | |
| [cbd26168c5](clusters/cluster_cbd26168c5.md) | 1 | `<unknown>` | `failed on setup with "file massgen/tests/memory/test_context_window_management.py, line <line>   asy` | [ ] Open | |
| [639cdc40d2](clusters/cluster_639cdc40d2.md) | 1 | `<unknown>` | `failed on setup with "file massgen/tests/memory/test_context_window_management.py, line <line>   asy` | [ ] Open | |
