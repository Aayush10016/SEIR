import json

from seir_analysis.cli import main

from .conftest import SAMPLE_REPO


def test_impact_json(capsys):
    assert main(["impact", str(SAMPLE_REPO), "PaymentService", "--no-subgraph"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["component"] == "com.shop.payment.PaymentService"
    assert "subgraph" not in data


def test_impact_mermaid(capsys):
    assert main(["impact", str(SAMPLE_REPO), "PaymentService", "--format", "mermaid"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("graph LR") and "PaymentController" in out and "style" in out


def test_unknown_component_exits_with_error(capsys):
    assert main(["impact", str(SAMPLE_REPO), "PaymentServise"]) == 2
    assert "Did you mean" in capsys.readouterr().err


def test_include_tests_flag(capsys):
    assert main(["scan", str(SAMPLE_REPO), "--include-tests"]) == 0
    assert json.loads(capsys.readouterr().out)["components"] == 20


def test_graph_export_to_file(tmp_path):
    out = tmp_path / "graph.json"
    assert main(["graph", str(SAMPLE_REPO), "-o", str(out)]) == 0
    graph = json.loads(out.read_text(encoding="utf-8"))
    assert len(graph["nodes"]) == 19 and graph["edges"]


def test_list_and_bad_repo(capsys, tmp_path):
    assert main(["list", str(SAMPLE_REPO)]) == 0
    assert "com.shop.model.Money" in capsys.readouterr().out
    assert main(["scan", str(tmp_path / "missing")]) == 2
