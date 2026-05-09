# { "Depends": "py-genlayer:15qfivjvy80800rh998pcxmd2m8va1wq2qzqhz850n8ggcr4i9q0" }
from genlayer import *


def _parse_price(s: str) -> float:
    try:
        return float(s.strip().replace(",", "").replace("$", ""))
    except Exception:
        return 0.0


class PriceBenchmark(gl.Contract):
    """
    Benchmark: Price Oracle
    Tests strict_eq vs custom equivalence with ±1% tolerance
    across multiple ETH price sources.
    """
    sources: DynArray[str]

    def __init__(self):
        self.sources = [
            "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
            "https://min-api.cryptocompare.com/data/price?fsym=ETH&tsyms=USD",
            "https://api.coinpaprika.com/v1/tickers/eth-ethereum",
        ]

    @gl.public.write
    def benchmark_strict(self) -> str:
        """
        strict_eq: expects exact character-level match.
        Expected to fail frequently due to real-time price drift.
        """
        def _fetch():
            data = gl.nondet.web.render(self.sources[0], mode="text")
            price = gl.nondet.exec_prompt(
                f"Extract ONLY the ETH/USD price as a plain number (digits and decimal point only, no other text). Data: {data}"
            )
            return price.strip()
        return gl.eq_principle.strict_eq(_fetch)

    @gl.public.write
    def benchmark_prompt_comparative(self) -> str:
        """
        prompt_comparative: validators compare via LLM judge.
        """
        def _fetch():
            prices = []
            for url in self.sources:
                data = gl.nondet.web.render(url, mode="text")
                price = gl.nondet.exec_prompt(
                    f"Extract the ETH/USD price as a plain number only (digits and decimal point, no other text). Data: {data[:3000]}"
                )
                prices.append(price.strip())
            return " | ".join(prices)
        return gl.eq_principle.prompt_comparative(
            _fetch,
            principle="The ETH/USD prices from each source must be within 2% of each other."
        )

    @gl.public.write
    def benchmark_prompt_non_comparative(self) -> str:
        """
        prompt_non_comparative: validators check the leader's output against criteria.
        """
        def _fetch():
            prices = []
            for url in self.sources:
                data = gl.nondet.web.render(url, mode="text")
                price = gl.nondet.exec_prompt(
                    f"Extract the ETH/USD price as a plain number only (digits and decimal point, no other text). Data: {data[:3000]}"
                )
                prices.append(price.strip())
            return " | ".join(prices)
        return gl.eq_principle.prompt_non_comparative(
            _fetch,
            task="Extract the current ETH/USD price from each data source.",
            criteria="The output must contain numeric ETH/USD prices separated by ' | '. Each price should be a positive number plausibly representing the current ETH price."
        )

    @gl.public.write
    def benchmark_custom(self) -> str:
        """
        custom: prices within ±2% are considered equivalent.
        Uses gl.advanced.run_nondet with custom tolerance comparison.
        """
        def _fetch():
            prices = []
            for url in self.sources:
                data = gl.nondet.web.render(url, mode="text")
                price_str = gl.nondet.exec_prompt(
                    f"Extract the ETH/USD price as a plain number only (digits and decimal point, no other text). Data: {data[:3000]}"
                )
                prices.append(str(_parse_price(price_str)))
            return " | ".join(prices)

        def _validator(leaders):
            my_res, leaders_res = gl.advanced.validator_handle_rollbacks_and_errors_default(_fetch, leaders)
            try:
                l_vals = [_parse_price(x) for x in str(leaders_res).split("|")]
                v_vals = [_parse_price(x) for x in str(my_res).split("|")]
                if len(l_vals) != len(v_vals):
                    return False
                for l, v in zip(l_vals, v_vals):
                    if l == 0.0 and v == 0.0:
                        continue
                    if l == 0.0 or v == 0.0:
                        return False
                    if abs(l - v) / l > 0.02:
                        return False
                return True
            except Exception:
                return False

        return gl.advanced.run_nondet(_fetch, _validator)

    @gl.public.view
    def get_sources(self) -> DynArray[str]:
        return self.sources
