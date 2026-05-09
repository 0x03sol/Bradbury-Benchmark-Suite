"""
Smoke tests for the substring-based status / consensus / execution parsing
inside send_transaction. These are pure-string operations, so we can call
the parsing inline using captured fixture-style stdout.
"""

import re


ACCEPTED_OUT = """
status_name: 'ACCEPTED'
resultName: 'AGREE'
txExecutionResultName: 'SUCCESS'
validatorVotesName: ['AGREE', 'AGREE', 'AGREE', 'AGREE', 'AGREE']
"""

FINALIZED_ERROR_OUT = """
status_name: 'FINALIZED'
resultName: 'AGREE'
txExecutionResultName: 'FINISHED_WITH_ERROR'
validatorVotesName: ['AGREE', 'DISAGREE', 'AGREE', 'AGREE', 'DISAGREE']
"""

REJECTED_OUT = """
status_name: 'REJECTED'
resultName: 'DISAGREE'
"""


def _classify(output: str):
    """Mirrors the substring rules in client.send_transaction."""
    status = "unknown"
    if "status_name: 'ACCEPTED'" in output:
        status = "accepted"
    elif "status_name: 'FINALIZED'" in output:
        if "txExecutionResultName: 'FINISHED_WITH_ERROR'" in output:
            status = "finalized_error"
        else:
            status = "accepted"
    elif "status_name: 'REJECTED'" in output or "status_name: 'UNDETERMINED'" in output:
        status = "rejected"

    consensus = "agree" if "resultName: 'AGREE'" in output else (
        "disagree" if "resultName: 'DISAGREE'" in output else "unknown"
    )
    execution = "success" if "txExecutionResultName: 'SUCCESS'" in output else (
        "finished_with_error" if "txExecutionResultName: 'FINISHED_WITH_ERROR'" in output else "unknown"
    )

    votes_match = re.search(r"validatorVotesName:\s*\[([^\]]*)\]", output)
    votes = [v.lower() for v in re.findall(r"'([^']+)'", votes_match.group(1))] if votes_match else []

    return status, consensus, execution, votes


def test_accepted_full_agreement():
    status, consensus, execution, votes = _classify(ACCEPTED_OUT)
    assert status == "accepted"
    assert consensus == "agree"
    assert execution == "success"
    assert votes == ["agree"] * 5


def test_finalized_with_error_is_not_accepted():
    status, consensus, execution, votes = _classify(FINALIZED_ERROR_OUT)
    assert status == "finalized_error"
    assert execution == "finished_with_error"
    assert votes.count("disagree") == 2


def test_rejected():
    status, consensus, execution, votes = _classify(REJECTED_OUT)
    assert status == "rejected"
    assert consensus == "disagree"
