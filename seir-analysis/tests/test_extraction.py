"""AST analysis + dependency extraction: one test per relationship kind / resolution rule."""


def test_inheritance_and_interfaces(edges):
    result, _ = edges({
        "a/Base.java": "package a; public abstract class Base {}",
        "a/Api.java": "package a; public interface Api {}",
        "a/SubApi.java": "package a; public interface SubApi extends Api {}",
        "a/Impl.java": "package a; public class Impl extends Base implements SubApi {}",
    })
    assert result[("a.Impl", "a.Base")] == {"extends"}
    assert result[("a.Impl", "a.SubApi")] == {"implements"}
    assert result[("a.SubApi", "a.Api")] == {"extends"}


def test_fields_parameters_returns_locals_and_instantiation(edges):
    result, _ = edges({
        "p/Dep.java": "package p; public class Dep { public void go() {} }",
        "p/F.java": "package p; public class F {}",
        "p/P.java": "package p; public class P {}",
        "p/R.java": "package p; public class R {}",
        "p/L.java": "package p; public class L {}",
        "p/User.java": """
            package p;
            public class User {
                private F f;
                public R work(P p) {
                    L local = null;
                    Dep d = new Dep();
                    d.go();
                    return null;
                }
            }""",
    })
    assert result[("p.User", "p.F")] == {"field"}
    assert result[("p.User", "p.P")] == {"parameter"}
    assert result[("p.User", "p.R")] == {"return_type"}
    assert result[("p.User", "p.L")] == {"local_variable"}
    assert result[("p.User", "p.Dep")] == {"local_variable", "instantiation", "method_call"}


def test_method_calls_resolve_receivers(edges):
    _, analysis = edges({
        "s/Svc.java": "package s; public class Svc { public void a() {} public static void s() {} }",
        "s/Caller.java": """
            package s;
            public class Caller {
                private final Svc field = new Svc();
                void run(Svc param) {
                    field.a();
                    this.field.a();
                    param.a();
                    var inferred = new Svc();
                    inferred.a();
                    ((Svc) null).a();
                    new Svc().a();
                    Svc.s();
                }
            }""",
    })
    calls = [(r.kind, r.detail, r.line) for r in analysis.extraction.relationships
             if r.source == "s.Caller" and r.kind in ("method_call", "static_call")]
    assert ("static_call", "s", 13) in calls
    assert sum(1 for kind, detail, _ in calls if kind == "method_call" and detail == "a") == 6
    assert all(r.member == "run" for r in analysis.extraction.relationships
               if r.source == "s.Caller" and r.kind == "method_call")


def test_import_resolution_rules(edges):
    result, analysis = edges({
        "x/Target.java": "package x; public class Target { public static class Nested {} }",
        "y/Target.java": "package y; public class Target {}",
        "z/ViaSingle.java": "package z; import x.Target; class ViaSingle { Target t; }",
        "z/ViaWildcard.java": "package z; import y.*; class ViaWildcard { Target t; }",
        "z/ViaFqn.java": "package z; class ViaFqn { x.Target t; }",
        "z/ViaNested.java": "package z; import x.Target; class ViaNested { Target.Nested n; }",
        "z/External.java": "package z; import java.util.List; import com.vendor.Lib; class External { List<String> l; Lib lib; String s; }",
    })
    assert ("z.ViaSingle", "x.Target") in result and ("z.ViaSingle", "y.Target") not in result
    assert ("z.ViaWildcard", "y.Target") in result
    assert result[("z.ViaFqn", "x.Target")] == {"field"}
    assert ("z.ViaNested", "x.Target.Nested") in result
    assert analysis.extraction.external_references["z.External"] == {"java.util.List", "com.vendor.Lib"}
    assert not any(src == "z.External" for src, _ in result)


def test_single_import_beats_same_package(edges):
    result, _ = edges({
        "a/Thing.java": "package a; public class Thing {}",
        "b/Thing.java": "package b; public class Thing {}",
        "b/User.java": "package b; import a.Thing; class User { Thing t; }",
    })
    assert ("b.User", "a.Thing") in result
    assert ("b.User", "b.Thing") not in result


def test_nested_types_generics_annotations_and_misc(edges):
    result, analysis = edges({
        "n/Outer.java": """
            package n;
            public class Outer {
                Inner inner;
                static class Inner {}
            }""",
        "n/Marker.java": "package n; public @interface Marker {}",
        "n/Boom.java": "package n; public class Boom extends RuntimeException {}",
        "n/Item.java": "package n; public class Item { public static final int MAX = 1; static Item of(String s) { return null; } }",
        "n/Uses.java": """
            package n;
            import java.util.List;
            import java.util.function.Function;
            @Marker
            class Uses {
                List<Item> items;
                void f(Object o) throws Boom {
                    try { } catch (Boom e) { }
                    if (o instanceof Item i) { }
                    int max = Item.MAX;
                    Function<String, Item> fn = Item::of;
                    Class<?> c = Outer.class;
                }
            }""",
    })
    assert result[("n.Outer", "n.Outer.Inner")] == {"field"}
    assert result[("n.Outer.Inner", "n.Outer")] == {"enclosed_by"}
    assert result[("n.Uses", "n.Marker")] == {"annotation"}
    assert result[("n.Uses", "n.Boom")] == {"type_reference"}
    assert {"field", "type_reference", "static_reference", "local_variable"} <= result[("n.Uses", "n.Item")]
    assert ("n.Uses", "n.Outer") in result
    assert "Marker" in analysis.extraction.types["n.Uses"].annotations


def test_static_imports_create_dependencies(edges):
    result, _ = edges({
        "u/Util.java": "package u; public class Util { public static int helper() { return 1; } }",
        "v/A.java": "package v; import static u.Util.helper; class A { int x = helper(); }",
        "v/B.java": "package v; import static u.Util.*; class B {}",
    })
    assert result[("v.A", "u.Util")] == {"import"}
    assert result[("v.B", "u.Util")] == {"import"}


def test_modern_java_records_enums_and_lambdas(edges):
    result, analysis = edges({
        "m/Money.java": "package m; public record Money(long cents) {}",
        "m/Price.java": "package m; public record Price(Money money, String label) implements Comparable<Price> { public int compareTo(Price o) { return 0; } }",
        "m/Kind.java": "package m; public enum Kind { A, B; Money zero() { return new Money(0); } }",
        "m/Lam.java": "package m; import java.util.List; class Lam { void f(List<Money> l) { l.forEach((Money x) -> x.cents()); } }",
    })
    assert result[("m.Price", "m.Money")] == {"field"}
    assert ("m.Kind", "m.Money") in result
    assert "method_call" in result[("m.Lam", "m.Money")]
    assert analysis.extraction.types["m.Price"].kind == "record"
    assert analysis.extraction.types["m.Kind"].kind == "enum"


def test_no_self_dependencies_and_anonymous_classes(edges):
    result, analysis = edges({
        "q/Listener.java": "package q; public interface Listener { void on(); }",
        "q/Self.java": """
            package q;
            class Self {
                Self next;
                Listener l = new Listener() { public void on() { Self s = new Self(); } };
            }""",
    })
    assert ("q.Self", "q.Self") not in result
    assert "instantiation" in result[("q.Self", "q.Listener")]
    assert [mth.name for mth in analysis.extraction.types["q.Self"].methods] == []


def test_enum_methods_are_registered(edges):
    _, analysis = edges({"e/E.java": "package e; enum E { A, B; void f() {} static E g() { return A; } }"})
    assert [mth.name for mth in analysis.extraction.types["e.E"].methods] == ["f", "g"]


def test_deeply_nested_expressions_do_not_crash(edges):
    concat = " + ".join(f'"s{i}"' for i in range(3000))
    result, analysis = edges({
        "d/Dep.java": "package d; class Dep {}",
        "d/Big.java": f"package d; class Big {{ Dep dep; String s = {concat}; }}",
    })
    assert ("d.Big", "d.Dep") in result
    assert analysis.files_with_syntax_errors == []


def test_package_named_like_build_dir_is_analysed(tmp_path):
    from seir_analysis import analyze_repository
    (tmp_path / "pom.xml").write_text("<project/>")
    (tmp_path / "target" / "classes").mkdir(parents=True)
    (tmp_path / "target" / "Gen.java").write_text("package gen; class Gen {}")
    pkg = tmp_path / "src" / "main" / "java" / "com" / "x" / "build"
    pkg.mkdir(parents=True)
    (pkg / "Builder.java").write_text("package com.x.build; public class Builder {}")
    assert list(analyze_repository(tmp_path).graph.g.nodes) == ["com.x.build.Builder"]


def test_syntax_errors_are_tolerated(edges):
    result, analysis = edges({
        "e/Dep.java": "package e; public class Dep {}",
        "e/Broken.java": "package e; public class Broken { Dep d; void f( { int x = ; } }",
    })
    assert analysis.files_with_syntax_errors == ["e/Broken.java"]
    assert ("e.Broken", "e.Dep") in result
