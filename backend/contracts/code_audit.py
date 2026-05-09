# { "Depends": "py-genlayer:15qfivjvy80800rh998pcxmd2m8va1wq2qzqhz850n8ggcr4i9q0" }
from genlayer import *


def _norm_vuln(s: str) -> str:
    s = s.strip().upper()
    if "YES" in s or "VULN" in s or "TRUE" in s:
        return "VULNERABLE"
    return "SAFE"


class CodeAuditBenchmark(gl.Contract):
    """
    Benchmark: AI Code Audit
    Tests validator agreement on identifying vulnerabilities
    in small code snippets with varying severity.
    """
    snippets: DynArray[str]

    def __init__(self):
        self.snippets = [
            "function withdraw() {{ public {{ msg.sender.transfer(balances[msg.sender]); balances[msg.sender] = 0; }}",
            "function mint(address to, uint256 amount) public {{ totalSupply += amount; balances[to] += amount; }}",
            "function transfer(address to, uint256 value) public returns (bool) {{ balances[msg.sender] -= value; balances[to] += value; return true; }}",
            "function setOwner(address newOwner) public {{ owner = newOwner; }}",
            "function buy() public payable {{ tokens[msg.sender] = msg.value / price; }}",
            "function execute(address target, bytes memory data) public {{ target.call(data); }}",
            "function selfDestruct(address payable recipient) public {{ selfdestruct(recipient); }}",
            "function batchTransfer(address[] memory recipients, uint256[] memory amounts) public {{ for (uint i=0; i<recipients.length; i++) {{ transfer(recipients[i], amounts[i]); }} }}",
            "function delegate(address to) public {{ delegates[msg.sender] = to; }}",
            "function random() public view returns (uint256) {{ return block.timestamp % 100; }}",
        ]

    @gl.public.write
    def benchmark_strict(self) -> str:
        """
        strict_eq on vulnerability verdict: expected low convergence
        due to LLM variance on borderline snippets.
        """
        def _audit():
            result = gl.nondet.exec_prompt(
                f"Is this Solidity code vulnerable? Reply with YES or NO only.\n{self.snippets[0]}"
            )
            return _norm_vuln(result)
        return gl.eq_principle.strict_eq(_audit)

    @gl.public.write
    def benchmark_prompt_comparative(self) -> str:
        """
        prompt_comparative: vulnerability verdicts across three snippets.
        """
        def _audit():
            verdicts = []
            for code in self.snippets[:3]:
                result = gl.nondet.exec_prompt(
                    f"Is this Solidity code vulnerable? Reply with YES or NO only.\n{code}"
                )
                verdicts.append(_norm_vuln(result))
            return " | ".join(verdicts)
        return gl.eq_principle.prompt_comparative(
            _audit,
            principle="The vulnerability verdict (VULNERABLE/SAFE) for each code snippet must match."
        )

    @gl.public.write
    def benchmark_custom(self) -> str:
        """
        custom: audits match if vulnerability verdicts agree for each snippet.
        Uses gl.advanced.run_nondet with custom validator.
        """
        def _audit():
            verdicts = []
            for code in self.snippets[:3]:
                result = gl.nondet.exec_prompt(
                    f"Is this Solidity code vulnerable? Reply with YES or NO only.\n{code}"
                )
                verdicts.append(_norm_vuln(result))
            return " | ".join(verdicts)

        def _validator(leaders):
            my_res, leaders_res = gl.advanced.validator_handle_rollbacks_and_errors_default(_audit, leaders)
            return str(my_res).strip() == str(leaders_res).strip()

        return gl.advanced.run_nondet(_audit, _validator)

    @gl.public.view
    def get_snippets(self) -> DynArray[str]:
        return self.snippets
