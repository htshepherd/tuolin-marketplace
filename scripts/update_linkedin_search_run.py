from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.linkedin_search.browser_contract import (
    LinkedInAccountObservation,
    LinkedInPostSearchObservation,
    bind_linkedin_account,
    confirm_effective_limit,
    finish_current_keyword,
    record_first_posts_search,
    record_next_posts_search,
)
from tuolin_marketplace.linkedin_search.discovery import (
    CompanyContactObservation,
    IndividualCandidateObservation,
    LinkedInPostObservation,
    record_company_post_evaluation,
    record_individual_post_evaluation,
)
from tuolin_marketplace.linkedin_search.review import (
    authorize_dispatch_batch,
    confirm_candidate_batch,
    prepare_candidate_batch_review,
    prepare_dispatch_authorization,
    remove_candidates_from_batch,
)
from tuolin_marketplace.linkedin_search.dispatch import (
    InvitationDispatchObservation,
    authorize_interruption_recovery,
    dispatch_next_candidate,
    prepare_interruption_recovery,
    prepare_platform_restart_handoff,
    resolve_note_unavailable,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a deterministic state transition to a LinkedIn search run.")
    parser.add_argument("action", choices=[
        "bind-account", "confirm-effective-limit", "record-first-search", "record-next-search", "finish-keyword",
        "record-individual", "record-company", "prepare-review", "remove-candidates",
        "confirm-batch", "prepare-authorization", "authorize-batch",
        "dispatch-next", "resolve-note-unavailable", "prepare-recovery", "authorize-recovery",
        "prepare-platform-restart",
    ])
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--data-json", default="{}", help="Action payload as a JSON object.")
    args = parser.parse_args()
    data = json.loads(args.data_json)
    if not isinstance(data, dict):
        raise ValueError("--data-json 顶层必须是对象。")
    run_dir = Path(args.run_dir)

    if args.action == "bind-account":
        result = bind_linkedin_account(
            run_dir,
            LinkedInAccountObservation(**data["observation"]),
            browser_authorized=bool(data.get("browser_authorized")),
        )
    elif args.action == "confirm-effective-limit":
        result = confirm_effective_limit(run_dir, confirmed=bool(data.get("confirmed")))
    elif args.action in {"record-first-search", "record-next-search"}:
        observation = LinkedInPostSearchObservation(**data["observation"])
        result = record_first_posts_search(run_dir, observation) if args.action == "record-first-search" else record_next_posts_search(run_dir, observation)
    elif args.action == "finish-keyword":
        result = finish_current_keyword(run_dir, exhausted=bool(data.get("exhausted")))
    elif args.action == "record-individual":
        candidate_data = data.get("candidate")
        result = record_individual_post_evaluation(
            run_dir,
            LinkedInPostObservation(**data["post"]),
            decision=data["decision"],
            reason=data["reason"],
            candidate=IndividualCandidateObservation(**candidate_data) if candidate_data else None,
        )
    elif args.action == "record-company":
        result = record_company_post_evaluation(
            run_dir,
            LinkedInPostObservation(**data["post"]),
            decision=data["decision"],
            reason=data["reason"],
            contacts=[CompanyContactObservation(**item) for item in data.get("contacts", [])],
        )
    elif args.action == "prepare-review":
        result = prepare_candidate_batch_review(run_dir)
    elif args.action == "remove-candidates":
        result = remove_candidates_from_batch(run_dir, list(data.get("identifiers") or []))
    elif args.action == "confirm-batch":
        result = confirm_candidate_batch(run_dir)
    elif args.action == "prepare-authorization":
        result = prepare_dispatch_authorization(
            run_dir,
            note_text=data.get("note_text"),
            note_review_confirmed=bool(data.get("note_review_confirmed")),
        )
    elif args.action == "authorize-batch":
        result = authorize_dispatch_batch(
            run_dir,
            confirmed=bool(data.get("confirmed")),
            observed_member_name=str(data.get("observed_member_name") or ""),
            observed_profile_url=str(data.get("observed_profile_url") or ""),
        )
    elif args.action == "dispatch-next":
        result = dispatch_next_candidate(run_dir, InvitationDispatchObservation(**data["observation"]))
    elif args.action == "resolve-note-unavailable":
        result = resolve_note_unavailable(run_dir, send_without_note=bool(data.get("send_without_note")))
    elif args.action == "prepare-recovery":
        result = prepare_interruption_recovery(
            run_dir,
            observed_member_name=str(data.get("observed_member_name") or ""),
            observed_profile_url=str(data.get("observed_profile_url") or ""),
            last_candidate_live_state=str(data.get("last_candidate_live_state") or "ambiguous"),
        )
    elif args.action == "authorize-recovery":
        result = authorize_interruption_recovery(run_dir, confirmed=bool(data.get("confirmed")))
    else:
        result = prepare_platform_restart_handoff(run_dir)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
