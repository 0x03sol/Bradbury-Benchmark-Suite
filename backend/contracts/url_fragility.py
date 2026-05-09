# { "Depends": "py-genlayer:15qfivjvy80800rh998pcxmd2m8va1wq2qzqhz850n8ggcr4i9q0" }
from genlayer import *
import json
import hashlib


def _norm_access(s: str) -> str:
    s = s.strip().upper()
    if "BLOCK" in s or "PAYWALL" in s or "403" in s or "WAF" in s:
        return "BLOCKED"
    return "ACCESSIBLE"


class URLFragilityBenchmark(gl.Contract):
    """
    Benchmark: URL Fragility
    Hits whitelisted domains repeatedly and tracks:
    - HTTP 200 rate
    - Cloudflare block rate
    - Content change rate
    - Paywall detection
    """
    targets: DynArray[str]

    def __init__(self):
        self.targets = [
            "https://example.com",
            "https://httpbin.org/get",
            "https://www.wikipedia.org/wiki/Blockchain",
            "https://news.ycombinator.com",
            "https://github.com/genlayerlabs",
            "https://docs.genlayer.com",
            "https://sdk.genlayer.com",
            "https://skills.genlayer.com",
            "https://studio.genlayer.com",
            "https://testnet-faucet.genlayer.foundation",
            "https://zksync-os-testnet-genlayer.explorer.zksync.dev",
            "https://explorer-bradbury.genlayer.com",
            "https://coinmarketcap.com",
            "https://coingecko.com",
            "https://etherscan.io",
            "https://www.reddit.com/r/ethereum",
            "https://medium.com",
            "https://twitter.com",
            "https://www.theguardian.com/technology",
            "https://arxiv.org/abs/2301.00001",
        ]

    @gl.public.write
    def benchmark_strict(self) -> str:
        """
        strict_eq on raw HTML: expected to fail due to dynamic content,
        cookies, timestamps, and ads.
        """
        def _probe():
            html = gl.nondet.web.render(self.targets[0], mode="html")
            return json.dumps({"url": self.targets[0], "len": len(html), "hash": hashlib.sha256(html.encode("utf-8", errors="replace")).hexdigest()})
        return gl.eq_principle.strict_eq(_probe)

    @gl.public.write
    def benchmark_custom(self) -> str:
        """
        custom: equivalence if accessibility verdict matches for each URL.
        Uses gl.advanced.run_nondet with custom comparator.
        """
        def _probe():
            verdicts = []
            for url in self.targets[:3]:
                text = gl.nondet.web.render(url, mode="text")
                result = gl.nondet.exec_prompt(
                    f"Is this URL accessible or blocked/paywalled? URL: {url}. "
                    f"Content preview: {text[:1000]}. Reply with ACCESSIBLE or BLOCKED only."
                )
                verdicts.append(_norm_access(result))
            return " | ".join(verdicts)

        def _validator(leaders):
            my_res, leaders_res = gl.advanced.validator_handle_rollbacks_and_errors_default(_probe, leaders)
            return str(my_res).strip() == str(leaders_res).strip()

        return gl.advanced.run_nondet(_probe, _validator)

    @gl.public.write
    def benchmark_prompt_comparative(self) -> str:
        """
        prompt_comparative: semantic equivalence of accessibility verdicts.
        """
        def _probe():
            verdicts = []
            for url in self.targets[:3]:
                text = gl.nondet.web.render(url, mode="text")
                result = gl.nondet.exec_prompt(
                    f"Is this URL accessible or blocked/paywalled? URL: {url}. "
                    f"Content preview: {text[:1000]}. Reply with ACCESSIBLE or BLOCKED only."
                )
                verdicts.append(_norm_access(result))
            return " | ".join(verdicts)
        return gl.eq_principle.prompt_comparative(
            _probe,
            principle="The accessibility verdict (ACCESSIBLE/BLOCKED) for each URL must match."
        )

    @gl.public.view
    def get_targets(self) -> DynArray[str]:
        return self.targets
