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
            "--max-tokens",
            "1024",
        ]
    )

    assert args.llm_backend == "openai"
    assert args.base_url == "http://127.0.0.1:8000/v1"
    assert args.model == "/models/qwen"
    assert args.timeout_seconds == 120
    assert args.max_tokens == 1024


def test_parser_accepts_optimize_command_with_type_mapping():
    parser = build_parser()
    args = parser.parse_args(
        [
            "optimize",
            "--file-processing-dir",
            "file_processing",
            "--optimization-data-file",
            "file_processing/150data.xlsx",
            "--initial-template",
            "母模板.md",
            "--type-mapping-file",
            "file_processing/类型映射.yaml",
            "--enable-multimodal-docx",
        ]
    )

    assert args.command == "optimize"
    assert args.optimization_data_file == "file_processing/150data.xlsx"
    assert args.initial_template == "母模板.md"
    assert args.templates_dir == "templates"
    assert args.type_mapping_file == "file_processing/类型映射.yaml"
    assert args.template_type == "meeting"
    assert args.enable_multimodal_docx is True


def test_parser_accepts_optimize_scope_and_context_truncation():
    parser = build_parser()
    args = parser.parse_args(
        [
            "optimize",
            "--file-processing-dir",
            "file_processing",
            "--initial-template",
            "母模板.md",
            "--optimization-scope",
            "scene",
            "--max-context-chars",
            "12000",
        ]
    )

    assert args.optimization_scope == "scene"
    assert args.max_context_chars == 12000


def test_parser_defaults_to_scene_and_sub_scene_optimization_scope():
    parser = build_parser()
    args = parser.parse_args(
        [
            "optimize",
            "--file-processing-dir",
            "file_processing",
            "--initial-template",
            "母模板.md",
        ]
    )

    assert args.optimization_scope == "scene_and_sub_scene"


def test_parser_accepts_evaluate_command_with_type_mapping():
    parser = build_parser()
    args = parser.parse_args(
        [
            "evaluate",
            "--file-processing-dir",
            "file_processing",
            "--type-mapping-file",
            "file_processing/类型映射.yaml",
        ]
    )

    assert args.command == "evaluate"
    assert args.file_processing_dir == "file_processing"
    assert args.type_mapping_file == "file_processing/类型映射.yaml"


def test_parser_accepts_evaluate_multimodal_flag():
    parser = build_parser()
    args = parser.parse_args(
        [
            "evaluate",
            "--file-processing-dir",
            "file_processing",
            "--enable-multimodal-docx",
        ]
    )

    assert args.enable_multimodal_docx is True
