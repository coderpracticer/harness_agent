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


def test_parser_accepts_optimize_command():
    parser = build_parser()
    args = parser.parse_args(
        [
            "optimize",
            "--file-processing-dir",
            "file_processing",
            "--template-type",
            "meeting",
            "--initial-template",
            "母模板.md",
            "--scene-mapping-file",
            "file_processing/场景映射.yaml",
            "--default-scene",
            "专项讨论会",
            "--enable-multimodal-docx",
        ]
    )

    assert args.command == "optimize"
    assert args.initial_template == "母模板.md"
    assert args.templates_dir == "templates"
    assert args.scene_mapping_file == "file_processing/场景映射.yaml"
    assert args.default_scene == "专项讨论会"
    assert args.enable_multimodal_docx is True


def test_parser_accepts_evaluate_command():
    parser = build_parser()
    args = parser.parse_args(
        [
            "evaluate",
            "--file-processing-dir",
            "file_processing",
            "--template-type",
            "interview",
        ]
    )

    assert args.command == "evaluate"
    assert args.file_processing_dir == "file_processing"


def test_parser_accepts_evaluate_multimodal_flag():
    parser = build_parser()
    args = parser.parse_args(
        [
            "evaluate",
            "--file-processing-dir",
            "file_processing",
            "--template-type",
            "meeting",
            "--enable-multimodal-docx",
        ]
    )

    assert args.enable_multimodal_docx is True
