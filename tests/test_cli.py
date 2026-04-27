from harness.cli import build_parser


def test_run_parser_accepts_local_llm_options():
    parser = build_parser()
    args = parser.parse_args(
        [
            "run",
            "--prompt-file",
            "tests/fixtures/meeting_input.md",
            "--template-type",
            "meeting",
            "--llm-backend",
            "openai",
            "--base-url",
            "http://127.0.0.1:8000/v1",
            "--model",
            "/models/qwen",
            "--timeout-seconds",
            "120",
        ]
    )

    assert args.llm_backend == "openai"
    assert args.base_url == "http://127.0.0.1:8000/v1"
    assert args.model == "/models/qwen"
    assert args.timeout_seconds == 120
