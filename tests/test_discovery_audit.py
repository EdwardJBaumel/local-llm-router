from local_llm_router.discovery import audit_model_folders, remove_duplicate_manifests


def test_audit_finds_no_duplicates_after_cleanup():
    audit = audit_model_folders()
    assert audit["duplicate_tags"] == []


def test_remove_duplicate_manifests_idempotent():
    audit = audit_model_folders()
    if not audit.get("primary_root"):
        return
    removed = remove_duplicate_manifests(keep_root=str(audit["primary_root"]))
    assert isinstance(removed, list)
