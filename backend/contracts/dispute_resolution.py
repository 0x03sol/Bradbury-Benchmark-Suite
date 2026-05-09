# { "Depends": "py-genlayer:15qfivjvy80800rh998pcxmd2m8va1wq2qzqhz850n8ggcr4i9q0" }
from genlayer import *


def _norm_action(s: str) -> str:
    s = s.strip().upper()
    for w in ("REFUND", "RELEASE", "APPEAL", "INVESTIGATE"):
        if w in s:
            return w
    return "INVESTIGATE"



class DisputeBenchmark(gl.Contract):
    """
    Benchmark: Dispute Resolution & Appeals
    Measures appeal frequency and success rate by deliberately
    introducing ambiguous scenarios that may trigger disagreements.
    """
    scenarios: DynArray[str]

    def __init__(self):
        self.scenarios = [
            "User claims they sent 100 GEN but recipient says they received 99.",
            "Two validators return different prices for ETH/USD at the same timestamp.",
            "A contract execution ran out of gas mid-calculation.",
            "One validator says an image contains a cat, another says it contains a dog.",
            "A URL returned 403 to one validator and 200 to another.",
            "A sentiment was classified as POSITIVE by one validator and NEUTRAL by another.",
            "A prompt injection was flagged by one validator but not another.",
            "A code audit found a bug that another validator marked safe.",
        ]

    @gl.public.write
    def benchmark_custom(self) -> str:
        """
        custom: disputes are equivalent if resolution action matches.
        Uses gl.advanced.run_nondet with custom comparator.
        """
        def _resolve():
            actions = []
            for scenario in self.scenarios[:3]:
                result = gl.nondet.exec_prompt(
                    f"You are a dispute resolver. What action should be taken? "
                    f"Reply with ONE WORD — REFUND, RELEASE, APPEAL, or INVESTIGATE.\nScenario: {scenario}"
                )
                actions.append(_norm_action(result))
            return " | ".join(actions)

        def _validator(leaders):
            my_res, leaders_res = gl.advanced.validator_handle_rollbacks_and_errors_default(_resolve, leaders)
            return str(my_res).strip() == str(leaders_res).strip()

        return gl.advanced.run_nondet(_resolve, _validator)

    @gl.public.write
    def benchmark_prompt_comparative(self) -> str:
        """
        prompt_comparative: resolution action comparison for disputes.
        """
        def _resolve():
            actions = []
            for scenario in self.scenarios[:3]:
                result = gl.nondet.exec_prompt(
                    f"You are a dispute resolver. What action should be taken? "
                    f"Reply with ONE WORD — REFUND, RELEASE, APPEAL, or INVESTIGATE.\nScenario: {scenario}"
                )
                actions.append(_norm_action(result))
            return " | ".join(actions)
        return gl.eq_principle.prompt_comparative(
            _resolve,
            principle="The dispute resolution action (REFUND/RELEASE/APPEAL/INVESTIGATE) for each scenario must match."
        )

    @gl.public.view
    def get_scenarios(self) -> DynArray[str]:
        return self.scenarios
