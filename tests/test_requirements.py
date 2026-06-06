from local_llm_router.requirements import UsageProfile, list_usage_profiles, usage_requirements


def test_list_usage_profiles_includes_core():
    profiles = list_usage_profiles()
    assert UsageProfile.CORE in profiles


def test_core_requirements_without_check():
    report = usage_requirements(UsageProfile.CORE, check=False)
    assert report.profile == UsageProfile.CORE
    assert report.ready is True
    assert any(item.id == "python" for item in report.prerequisites)


def test_core_requirements_with_check():
    report = usage_requirements(UsageProfile.CORE, check=True)
    python_item = next(item for item in report.prerequisites if item.id == "python")
    assert python_item.satisfied is True


def test_local_assistant_lists_ollama_requirements():
    report = usage_requirements(UsageProfile.LOCAL_ASSISTANT, check=False)
    ids = {item.id for item in report.prerequisites}
    assert "ollama" in ids
    assert "requests" in ids
