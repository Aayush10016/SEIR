"""Graph building and impact analysis, mostly against samples/shop."""

import pytest

from seir_analysis import AmbiguousComponentError, ComponentNotFoundError, analyze_sources

P = "com.shop."


def test_sample_repository_is_fully_parsed(shop):
    assert shop.files_with_syntax_errors == []
    assert len(shop.graph) == 19                      # test sources excluded by default
    assert P + "payment.PaymentServiceTest" not in shop.graph


def test_direct_and_indirect_dependents(shop):
    report = shop.impact("LegacyPaymentService")
    assert report.component == P + "payment.LegacyPaymentService"
    assert report.direct_dependents == [P + "jobs.ReconciliationJob", P + "payment.PaymentService"]
    assert report.dependents_by_depth[2] == [P + "api.PaymentController", P + "order.OrderService"]
    assert report.dependents_by_depth[3] == [P + "api.OrderController", P + "notify.NotificationService"]
    assert report.max_dependency_depth == 3
    assert len(report.affected_components) == 6


def test_impact_paths_explain_propagation(shop):
    report = shop.impact("LegacyPaymentService")
    assert report.impact_paths[P + "api.OrderController"] == [
        P + "api.OrderController", P + "order.OrderService",
        P + "payment.PaymentService", P + "payment.LegacyPaymentService",
    ]


def test_call_site_evidence_and_used_members(shop):
    report = shop.impact("LegacyPaymentService")
    sites = {(c["caller"], c["caller_member"], c["target_member"], c["line"]) for c in report.call_sites}
    assert (P + "jobs.ReconciliationJob", "run", "reconcileAll", 9) in sites
    assert (P + "payment.PaymentService", "pay", "charge", 28) in sites
    assert report.used_members == {"reconcileAll": 1, "charge": 1}
    assert report.metrics["is_deprecated"] == 1


def test_polymorphic_dependents_via_interface(shop):
    # AuditJob only knows PaymentGateway, which both gateways implement; StripeGateway is a
    # sibling implementation, not a consumer, so it must not be listed.
    report = shop.impact("StripeGateway")
    assert report.affected_components == []
    assert report.polymorphic_dependents == [P + "jobs.AuditJob", P + "payment.PaymentService"]


def test_types_nested_in_supertype_are_not_polymorphic_dependents():
    analysis = analyze_sources({
        "p/Gw.java": "package p; public interface Gw { class Cfg {} }",
        "p/Impl.java": "package p; public class Impl implements Gw {}",
        "p/User.java": "package p; public class User { Gw g; }",
    })
    assert analysis.impact("Impl").polymorphic_dependents == ["p.User"]


def test_max_depth_limits_propagation(shop):
    report = shop.impact("LegacyPaymentService", max_depth=1)
    assert report.indirect_dependents == []
    assert report.max_dependency_depth == 1


def test_cycles_are_traversed_once_and_reported(shop):
    report = shop.impact("OrderService")
    assert report.cycle_members == [P + "notify.NotificationService", P + "order.OrderService"]
    assert report.direct_dependents == [P + "api.OrderController", P + "notify.NotificationService"]
    assert P + "order.OrderService" not in report.affected_components
    # nested types used by their outer type are not reported as cycles
    assert shop.graph.cycles() == [[P + "notify.NotificationService", P + "order.OrderService"]]


def test_leaf_component_has_no_impact(shop):
    report = shop.impact("com.shop.api.OrderController")
    assert report.affected_components == []
    assert report.metrics["impact_size"] == 0


def test_component_lookup_by_file_path(shop):
    assert shop.graph.resolve("src/main/java/com/shop/order/OrderService.java") == P + "order.OrderService"
    assert shop.graph.resolve("OrderService.java") == P + "order.OrderService"
    absolute = shop.root / "src" / "main" / "java" / "com" / "shop" / "order" / "OrderService.java"
    assert shop.graph.resolve(str(absolute)) == P + "order.OrderService"
    assert shop.graph.resolve("Order.Status") == P + "model.Order.Status"


def test_unknown_and_ambiguous_components():
    analysis = analyze_sources({
        "a/Thing.java": "package a; public class Thing {}",
        "b/Thing.java": "package b; public class Thing {}",
    })
    with pytest.raises(AmbiguousComponentError) as amb:
        analysis.graph.resolve("Thing")
    assert amb.value.candidates == ["a.Thing", "b.Thing"]
    with pytest.raises(ComponentNotFoundError) as missing:
        analysis.graph.resolve("Thingy")
    assert "a.Thing" in missing.value.suggestions


def test_report_json_contract(shop):
    data = shop.impact("PaymentService").to_dict()
    for key in ("component", "direct_dependents", "indirect_dependents", "impact_size",
                "max_dependency_depth", "external_references", "metrics", "subgraph", "call_sites"):
        assert key in data
    assert data["impact_size"] == len(data["direct_dependents"]) + len(data["indirect_dependents"])
    assert set(data["external_references"]) == {
        "org.slf4j.Logger", "org.slf4j.LoggerFactory",
        "org.springframework.beans.factory.annotation.Autowired", "org.springframework.stereotype.Service",
    }
    node_ids = {n["id"] for n in data["subgraph"]["nodes"]}
    assert node_ids == {data["component"], *data["direct_dependents"], *data["indirect_dependents"]}
    assert all(e["source"] in node_ids and e["target"] in node_ids for e in data["subgraph"]["edges"])
    assert all(isinstance(v, (int, float)) for v in data["metrics"].values())
