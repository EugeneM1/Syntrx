"""Full four-stage pipeline test."""

from app.services.pipeline import run_pipeline


def test_pipeline_produces_findings_and_trace(sample_files):
    payload = sample_files["warfarin_sensitive_pgx_storm"].read_bytes()
    rep = run_pipeline(payload, filename="x.txt", use_llm=False)
    assert rep.parse.matched_variants > 50
    assert any(f.gene == "CYP2C9" for f in rep.findings)
    # Four agents, four trace entries
    names = [s.name for s in rep.trace]
    assert names == ["parser", "lookup", "synthesis", "safety"]
    # Safety agent should have appended a physician disclaimer somewhere
    assert any("Syntrx is a literacy tool" in a
               for f in rep.findings for a in f.actions)


def test_pipeline_with_mock_llm(sample_files):
    payload = sample_files["cyp2d6_poor_metabolizer"].read_bytes()
    rep = run_pipeline(payload, filename="x.txt", use_llm=True)
    cyp2d6 = next(f for f in rep.findings if f.gene == "CYP2D6")
    assert cyp2d6.id in rep.narratives
    # Mock narrator echoes the user prompt — should mention codeine
    assert "codeine" in rep.narratives[cyp2d6.id].lower()


def test_no_diagnostic_phrases_after_safety(sample_files):
    payload = sample_files["apoe_e4_carrier_with_iron"].read_bytes()
    rep = run_pipeline(payload, filename="x.txt", use_llm=True)
    for narration in rep.narratives.values():
        assert "I diagnose" not in narration
