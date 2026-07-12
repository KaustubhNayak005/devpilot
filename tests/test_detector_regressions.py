"""Regression tests for the stack detector's shared-state and merge behavior."""

from __future__ import annotations

from devpilot.inspector.detector import DETECTION_RULES, detect_stack


class TestDetectorStateIsolation:
    def test_repeated_calls_return_equal_results(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("[package]", encoding="utf-8")
        first = detect_stack(str(tmp_path))
        second = detect_stack(str(tmp_path))
        assert [(r.name, r.confidence, r.tools) for r in first] == [
            (r.name, r.confidence, r.tools) for r in second
        ]

    def test_results_are_fresh_instances(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("[package]", encoding="utf-8")
        first = detect_stack(str(tmp_path))
        second = detect_stack(str(tmp_path))
        assert first[0] is not second[0]

    def test_mutating_a_result_does_not_leak_into_next_call(self, tmp_path):
        (tmp_path / "go.mod").write_text("module x", encoding="utf-8")
        first = detect_stack(str(tmp_path))
        first[0].confidence = "mutated"
        first[0].tools.append("bogus-tool")
        second = detect_stack(str(tmp_path))
        assert second[0].confidence == "definite"
        assert "bogus-tool" not in second[0].tools

    def test_likely_match_does_not_downgrade_later_scans(self, tmp_path_factory):
        # A *.cmake file alone gives "likely" confidence.
        likely_dir = tmp_path_factory.mktemp("likely")
        (likely_dir / "helpers.cmake").write_text("# cmake", encoding="utf-8")
        result = detect_stack(str(likely_dir))
        assert result[0].confidence == "likely"

        # A CMakeLists.txt in a different project must still be "definite".
        definite_dir = tmp_path_factory.mktemp("definite")
        (definite_dir / "CMakeLists.txt").write_text("project(x)", encoding="utf-8")
        result = detect_stack(str(definite_dir))
        assert result[0].confidence == "definite"

    def test_rules_are_immutable(self):
        import dataclasses

        import pytest

        with pytest.raises(dataclasses.FrozenInstanceError):
            DETECTION_RULES[0].pattern = "hacked"  # type: ignore[misc]


class TestDetectorMerging:
    def test_primary_and_secondary_merge_to_one_definite_result(self, tmp_path):
        (tmp_path / "CMakeLists.txt").write_text("project(x)", encoding="utf-8")
        (tmp_path / "helpers.cmake").write_text("# cmake", encoding="utf-8")
        results = detect_stack(str(tmp_path))
        cmake_results = [r for r in results if r.name == "C++ / CMake"]
        assert len(cmake_results) == 1
        assert cmake_results[0].confidence == "definite"

    def test_empty_directory_detects_nothing(self, tmp_path):
        assert detect_stack(str(tmp_path)) == []
